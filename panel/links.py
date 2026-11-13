# links.py — SUKOT link/config engine (inbounds, clients, URIs, quota)
import base64, secrets, json, urllib.parse
from datetime import datetime, timedelta, timezone
from core import (STATE, STATE_LOCK, load_state, save_state, settings, now_iso, parse_iso,
                  human_bytes, gb_to_bytes, sanitize_label, new_uuid4, rand_key,
                  build_config_remark, build_info_server_remark, random_config_names,
                  VW_TLS, VW_FORCE_PORT, APP_NAME)

PROTOCOLS = {
    "vless-ws":         {"label": "VLESS + WebSocket",     "live": True},
    "vless-tcp":        {"label": "VLESS + TCP (خام)",     "live": True},
    "xhttp-packet-up":  {"label": "XHTTP (packet-up)",     "live": True},
    "xhttp-stream-up":  {"label": "XHTTP (stream-up)",     "live": True},
    "xhttp-stream-one": {"label": "XHTTP (stream-one)",    "live": False},
    "vmess-ws":         {"label": "VMess + WebSocket",     "live": False},
    "trojan-ws":        {"label": "Trojan + WebSocket",    "live": False},
    "manual":           {"label": "لینک دستی ( همه پروتکل‌ها )", "live": True},
}
LIVE_PROTOCOLS = {k for k, v in PROTOCOLS.items() if v["live"]}

MANUAL_LIVE_COMBOS = {
    ("vless", "tcp", "reality"), ("vless", "grpc", "reality"), ("vless", "xhttp", "reality"),
    ("trojan", "tcp", "reality"), ("shadowsocks", "tcp", "none"), ("wireguard", "udp", "none"),
}

FINGERPRINTS = ["chrome", "firefox", "safari", "ios", "android", "edge", "360", "qq", "random", "randomized"]
ALPN_MAP = {"http1": "http/1.1", "h2h1": "h2,http/1.1", "h2": "h2"}

# ----------------------------------------------------------------- access
def links() -> dict:
    return load_state().setdefault("links", {})

def get_link(uid: str):
    return links().get(uid)

def is_link_allowed(link) -> bool:
    if not link:
        return False
    if not link.get("active", True):
        return False
    exp = None
    try:
        from core import expires_in_seconds
        exp = expires_in_seconds(link)
    except Exception:
        exp = None
    if exp is not None and exp <= 0:
        return False
    lim = link.get("limit_bytes") or 0
    if lim and (link.get("used_bytes") or 0) >= lim:
        return False
    return True

def check_and_use(uuid: str, n: int):
    """Quota accounting under lock. Returns True when within quota."""
    with STATE_LOCK:
        lk = get_link(uuid)
        if not lk:
            return False
        lk["used_bytes"] = (lk.get("used_bytes") or 0) + n
        lim = lk.get("limit_bytes") or 0
        if lim and lk["used_bytes"] > lim:
            save_state()
            return False
        return True

def client_visible(link, admin) -> bool:
    """Admins only see clients they created; owner sees all."""
    if not admin or admin.get("role") == "owner":
        return True
    return (link.get("created_by") or "") == (admin.get("admin_id") or "")

def scope_allows_inbound(admin, uid: str) -> bool:
    if not admin or admin.get("role") == "owner":
        return True
    allowed = admin.get("allowed_inbounds") or []
    return (not allowed) or (uid in allowed)

# ----------------------------------------------------------------- creation
def make_link(*, label="", limit_bytes=0, expires_at=None, protocol="vless-ws",
              fingerprint="chrome", alpn="http1", port=443, fragment="", ip_limit=0,
              connection_limit=0, speed_limit_bytes=0, sub_id="", parent_inbound_id="",
              category_id="", note="", clean_ips=None, config_count=1, client_limit=0,
              outbound_proxy_id="", operator="", created_by="", admin_id="",
              manual=None, uuid=None, active=True) -> dict:
    uid = uuid or new_uuid4()
    lk = {
        "uuid": uid,
        "label": sanitize_label(label) if label else random_config_names(count=1)[0].split("|")[-1],
        "limit_bytes": int(limit_bytes or 0),
        "used_bytes": 0,
        "expires_at": expires_at or None,
        "active": bool(active),
        "protocol": protocol if protocol in PROTOCOLS else "vless-ws",
        "fingerprint": fingerprint or "chrome",
        "alpn": alpn or "http1",
        "port": int(port or (VW_FORCE_PORT if VW_TLS else 443)),
        "fragment": fragment or "",
        "ip_limit": int(ip_limit or 0),
        "connection_limit": int(connection_limit or 0),
        "speed_limit_bytes": int(speed_limit_bytes or 0),
        "sub_id": sub_id or "",
        "parent_inbound_id": parent_inbound_id or "",
        "category_id": category_id or "",
        "note": note or "",
        "clean_ips": [c for c in (clean_ips or []) if str(c).strip()][:8],
        "config_count": max(1, min(int(config_count or 1), 40)),
        "client_limit": int(client_limit or 0),
        "usage_history": [],
        "outbound_proxy_id": outbound_proxy_id or "",
        "operator": operator or "",
        "created_by": created_by or admin_id or "",
        "created_at": now_iso(),
        "combo_group_id": "",
    }
    if lk["protocol"] == "manual" and isinstance(manual, dict):
        for k in ("base_protocol", "network", "security", "address", "path", "host_header",
                  "sni", "flow", "grpc_service_name", "grpc_mode", "xhttp_mode", "header_type",
                  "allow_insecure", "reality_public_key", "reality_short_id", "spider_x",
                  "ss_method", "ss_password", "wg_private_key", "wg_public_key", "wg_address",
                  "wg_mtu", "wg_reserved", "xs", "xs_server"):
            if manual.get(k) is not None:
                lk[k] = manual[k]
    links()[uid] = lk
    from core import bump_daily, log_activity
    bump_daily(new_links=1 if not parent_inbound_id else 0)
    log_activity(f"کانفیگ «{lk['label']}» ساخته شد", actor=created_by or admin_id or "system")
    save_state()
    return lk

def get_link_info(link) -> dict:
    from core import expires_in_seconds, TUNNELS_NOW, CONNECTED_IPS
    uid = link["uuid"]
    children = [c for c in links().values() if c.get("parent_inbound_id") == uid]
    live = link.get("protocol") in LIVE_PROTOCOLS
    if link.get("protocol") == "manual":
        bp = (link.get("base_protocol") or "vless").lower()
        live = (bp, (link.get("network") or "tcp").lower(), (link.get("security") or "none").lower()) in MANUAL_LIVE_COMBOS
    d = dict(link)
    d.pop("password_hash", None)
    d["live"] = bool(live)
    d["status"] = "active" if is_link_allowed(link) else ("expired" if (expires_in_seconds(link) or 1) <= 0 else "disabled" if not link.get("active", True) else "exhausted")
    d["clients_count"] = len(children)
    # ---- live connected users: own tunnels + tunnels of all child clients ----
    own_n = TUNNELS_NOW.get(uid, 0) or 0
    ch_n = sum(TUNNELS_NOW.get(ch["uuid"], 0) or 0 for ch in children)
    d["online"] = int(own_n + ch_n)
    ips = set(CONNECTED_IPS.get(uid) or ())
    for ch in children:
        ips |= set(CONNECTED_IPS.get(ch["uuid"]) or ())
    d["ips_online"] = len(ips)
    d["sub_url"] = (sub_url_for(uid))
    d["portal_url"] = (portal_url_for(uid))
    return d

# ----------------------------------------------------------------- URI builders
def _public_host() -> str:
    from core import public_url
    u = public_url()
    if u:
        return urllib.parse.urlparse(u).netloc or u
    return ""

def _remark_full(link) -> str:
    info = build_info_server_remark(link)
    tail = build_config_remark(link)
    return (info + " | " + tail) if info else tail

def generate_vless_link(link) -> str:
    uid = link["uuid"]
    proto = link.get("protocol")
    host = _public_host() or "127.0.0.1"
    fp = link.get("fingerprint") or "chrome"
    alpn = ALPN_MAP.get(link.get("alpn") or "http1", "http/1.1")
    remark = urllib.parse.quote(_remark_full(link))
    if proto == "vless-ws":
        port = VW_FORCE_PORT if VW_TLS else (link.get("port") or 443)
        q = (f"encryption=none&security={'tls' if VW_TLS else 'none'}&type=ws&host={host}"
             f"&path=%2Fws%2F{uid}&sni={host}&fp={fp}&alpn={urllib.parse.quote(alpn)}")
        return f"vless://{uid}@{host}:{port}?{q}#{remark}"
    if proto == "vless-tcp":
        from core import settings
        s = settings()
        host = s.get("tcp_public_host") or host
        port = s.get("tcp_public_port") or link.get("port") or 443
        q = f"encryption=none&security=none&type=tcp&fp={fp}"
        return f"vless://{uid}@{host}:{port}?{q}#{remark}"
    if proto and proto.startswith("xhttp"):
        mode = proto.replace("xhttp-", "") or "packet-up"
        port = VW_FORCE_PORT if VW_TLS else (link.get("port") or 443)
        q = (f"encryption=none&security={'tls' if VW_TLS else 'none'}&type=xhttp&host={host}"
             f"&path=%2Fxhttp-siz10%2F{mode}%2F{uid}&sni={host}&fp={fp}&mode={mode}")
        return f"vless://{uid}@{host}:{port}?{q}#{remark}"
    return ""

def generate_vmess_link(link) -> str:
    uid = link["uuid"]
    host = _public_host() or "127.0.0.1"
    port = VW_FORCE_PORT if VW_TLS else (link.get("port") or 443)
    obj = {"v": "2", "ps": _remark_full(link), "add": host, "port": str(port), "id": uid,
           "aid": "0", "scy": "auto", "net": "ws", "type": "none",
           "host": host, "path": f"/ws/{uid}", "tls": "tls" if VW_TLS else "", "fp": link.get("fingerprint") or "chrome"}
    return "vmess://" + base64.b64encode(json.dumps(obj, ensure_ascii=False).encode()).decode()

def generate_trojan_link(link) -> str:
    uid = link["uuid"]
    host = _public_host() or "127.0.0.1"
    port = VW_FORCE_PORT if VW_TLS else (link.get("port") or 443)
    q = (f"security={'tls' if VW_TLS else 'none'}&type=ws&host={host}&path=%2Fws%2F{uid}"
         f"&sni={host}&fp={link.get('fingerprint') or 'chrome'}")
    return f"trojan://{uid}@{host}:{port}?{q}#{urllib.parse.quote(_remark_full(link))}"

def build_manual_uri(link) -> str:
    """3x-ui style manual builder (vless/vmess/trojan/ss/wireguard)."""
    m = link
    bp = (m.get("base_protocol") or "vless").lower()
    host = m.get("address") or _public_host() or "127.0.0.1"
    port = m.get("port") or 443
    uid = link["uuid"]
    remark = urllib.parse.quote(_remark_full(link))
    sec = (m.get("security") or "none").lower()
    net = (m.get("network") or "tcp").lower()
    q = []
    if bp in ("vless",):
        q.append("encryption=none")
        if m.get("flow"):
            q.append("flow=" + m["flow"])
    if sec == "tls":
        q.append("security=tls")
        if m.get("sni"): q.append("sni=" + m["sni"])
        if m.get("fp"): q.append("fp=" + m["fp"])
        if m.get("alpn"): q.append("alpn=" + m["alpn"])
        if str(m.get("allow_insecure") or "").lower() in ("1", "true"): q.append("allowInsecure=1")
    elif sec == "reality":
        q.append("security=reality")
        q.append("pbk=" + (m.get("reality_public_key") or ""))
        q.append("sid=" + (m.get("reality_short_id") or ""))
        if m.get("sni"): q.append("sni=" + m["sni"])
        if m.get("fp"): q.append("fp=" + m["fp"])
        if m.get("spider_x"): q.append("spx=" + urllib.parse.quote(m["spider_x"]))
    else:
        q.append("security=none")
    if net == "ws":
        q.append("type=ws")
        if m.get("path"): q.append("path=" + urllib.parse.quote(m["path"]))
        if m.get("host_header"): q.append("host=" + m["host_header"])
    elif net == "grpc":
        q.append("type=grpc")
        if m.get("grpc_service_name"): q.append("serviceName=" + m["grpc_service_name"])
        q.append("mode=" + (m.get("grpc_mode") or "gun"))
    elif net == "xhttp":
        q.append("type=xhttp")
        if m.get("path"): q.append("path=" + urllib.parse.quote(m["path"]))
        if m.get("host_header"): q.append("host=" + m["host_header"])
        q.append("mode=" + (m.get("xhttp_mode") or "auto"))
    else:
        q.append("type=tcp")
        if m.get("header_type"): q.append("headerType=" + m["header_type"])
    if bp == "vless":
        return f"vless://{uid}@{host}:{port}?" + "&".join(q) + f"#{remark}"
    if bp == "trojan":
        return f"trojan://{uid}@{host}:{port}?" + "&".join(q) + f"#{remark}"
    if bp == "vmess":
        obj = {"v": "2", "ps": _remark_full(link), "add": host, "port": str(port), "id": uid,
               "aid": "0", "scy": "auto", "net": net, "type": (m.get("header_type") or "none"),
               "host": m.get("host_header") or "", "path": m.get("path") or "",
               "tls": "tls" if sec in ("tls", "reality") else "", "sni": m.get("sni") or "", "fp": m.get("fp") or ""}
        return "vmess://" + base64.b64encode(json.dumps(obj, ensure_ascii=False).encode()).decode()
    if bp == "shadowsocks":
        userinfo = base64.b64encode(f"{m.get('ss_method') or 'chacha20-ietf-poly1305'}:{m.get('ss_password') or uid}".encode()).decode()
        return f"ss://{userinfo}@{host}:{port}#{remark}"
    if bp == "wireguard":
        return (f"wireguard://{m.get('wg_private_key') or uid}@{host}:{port}?"
                f"publicKey={m.get('wg_public_key') or ''}&address={m.get('wg_address') or '172.16.0.2/32'}"
                f"&mtu={m.get('wg_mtu') or 1420}#{remark}")
    return ""

def vless_link_for_link(link) -> str:
    p = link.get("protocol")
    if p == "vmess-ws":
        return generate_vmess_link(link)
    if p == "trojan-ws":
        return generate_trojan_link(link)
    if p == "manual":
        return build_manual_uri(link)
    return generate_vless_link(link)

def config_lines_for(link, count: int | None = None) -> list:
    """One or more client app lines for this config."""
    n = count if count is not None else int(link.get("config_count") or 1)
    base = vless_link_for_link(link)
    if not base:
        return []
    if n <= 1:
        return [base]
    names = random_config_names(count=n)
    out = []
    from urllib.parse import quote
    for nm in names:
        # swap remark fragment
        frag = quote(nm, safe="")
        try:
            head, _, _ = base.partition("#")
            out.append(head + "#" + frag)
        except Exception:
            out.append(base)
    # per clean-ip variants if present
    cis = link.get("clean_ips") or []
    if cis and len(out) == 1:
        extra = []
        for cip in cis[:6]:
            try:
                import re as _re2
                variant = _re2.sub(r"@[^\?:]+", "@" + str(cip).strip(), base)
                extra.append(variant)
            except Exception:
                pass
        out = [base] + extra
    return out

# ----------------------------------------------------------------- subscription urls
def base_url() -> str:
    from core import public_url
    return public_url().rstrip("/")

def sub_url_for(uid) -> str:
    return f"{base_url()}/sub/{uid}"

def portal_url_for(uid) -> str:
    return f"{base_url()}/subscription/{uid}"

def subscription_headers(link) -> dict:
    lim = link.get("limit_bytes") or 0
    used = link.get("used_bytes") or 0
    exp = 0
    d = parse_iso(link.get("expires_at"))
    if d:
        exp = int(d.timestamp())
    from core import support_url
    h = {
        "subscription-userinfo": f"upload=0; download={used}; total={lim}; expire={exp}",
        "profile-update-interval": "12",
        "content-disposition": f'attachment; filename="{APP_NAME}-{link["uuid"][:8]}"',
        "support-url": support_url(),
    }
    return h

# ----------------------------------------------------------------- sub groups
def subs() -> dict:
    return load_state().setdefault("subs", {})

def create_sub_group(name: str, link_ids=None, desc="", password="", remote_links=None) -> dict:
    sid = rand_key(10)
    sub = {
        "id": sid,
        "name": sanitize_label(name) or ("گروه " + sid[:4]),
        "desc": desc or "",
        "password_hash": (hash(password) if password else ""),
        "uuid_key": new_uuid4() + new_uuid4()[:12],
        "created_at": now_iso(),
        "link_ids": list(link_ids or []),
        "remote_links": list(remote_links or []),
    }
    subs()[sid] = sub
    for lid in sub["link_ids"]:
        lk = get_link(lid)
        if lk:
            lk["sub_id"] = sid
    from core import log_activity
    log_activity(f"گروه ساب «{sub['name']}» ساخته شد")
    save_state()
    return sub

def hash(s: str) -> str:
    import hashlib
    return hashlib.sha256(("sub:" + (s or "")).encode()).hexdigest()

def remove_link_everywhere(uid: str):
    for sub in subs().values():
        if uid in sub.get("link_ids", []):
            sub["link_ids"].remove(uid)
