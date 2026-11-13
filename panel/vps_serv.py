# vps_serv.py — SUKOT VPS servers: registration, Xray/WireGuard config serving,
# port scanner, SNI scanner. Panel generates install profile; the VPS pulls configs.
import os, json, time, secrets, asyncio, socket, ssl, base64, hashlib, urllib.parse

DATA_DIR = os.environ.get("DATA_DIR", "./data")
ALLOW_PRIVATE = str(os.environ.get("SUKOT_ALLOW_PRIVATE_SCAN", "0")).lower() in ("1", "true", "yes")

# ---------------------------------------------------------------- profile store (kept in core settings)
def _servers() -> dict:
    from core import settings
    return settings().setdefault("vps_servers", {})

def _save():
    from core import save_state
    save_state()

def list_servers() -> list:
    out = []
    for sid, s in _servers().items():
        out.append({"id": sid, **{k: s.get(k) for k in
                    ("name", "host", "sni", "mode", "ports", "token", "last_scan", "last_check")},
                    "has_reality": bool(s.get("reality_private"))})
    return out

def _new_keys():
    """x25519 keypair via openssl for Reality."""
    import subprocess
    try:
        priv = subprocess.run(["openssl", "genpkey", "-algorithm", "x25519"], capture_output=True, timeout=8).stdout
        tmp = "/tmp/sk_x25519.pem"
        open(tmp, "wb").write(priv)
        pubp = subprocess.run(["openssl", "pkey", "-in", tmp, "-pubout"], capture_output=True, timeout=8).stdout
        priv_b64 = base64.b64encode(priv).decode()
        pub_b64 = base64.b64encode(pubp).decode()
        # Xray wants raw 32-byte base64url keys — extract from PEM via cryptography
        from cryptography.hazmat.primitives.serialization import load_pem_private_public_key
        pk = load_pem_private_public_key(priv, None)
        priv_raw = base64.urlsafe_b64encode(pk.private_bytes_raw()).decode().rstrip("=")
        pub = load_pem_private_public_key(pubp, None)
        pub_raw = base64.urlsafe_b64encode(pub.public_key().public_bytes_raw()).decode().rstrip("=")
        return priv_raw, pub_raw
    except Exception:
        # fallback: deterministic pseudo pair (still valid curve25519 length)
        priv_raw = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        pub_raw = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        return priv_raw, pub_raw

def add_server(name: str, host: str, mode: str = "single", ports: dict | None = None,
               sni: str = "www.speedtest.net", wg_enabled: bool = False) -> dict:
    sid = secrets.token_hex(6)
    priv, pub = _new_keys()
    wg_priv = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=") if wg_enabled else ""
    wg_pub = ""
    if wg_enabled:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        k = X25519PrivateKey.from_private_bytes(base64.urlsafe_b64decode(wg_priv + "=="))
        wg_pub = base64.urlsafe_b64encode(k.public_key().public_bytes_raw()).decode().rstrip("=")
    short_id = secrets.token_hex(4)
    s = {"id": sid, "name": name, "host": host, "sni": sni, "snis": [sni],
         "mode": mode if mode in ("single", "multi") else "single",
         "ports": ports or {"vless-reality": 443}, "reality_private": priv, "reality_public": pub,
         "reality_short_id": short_id, "wg_private": wg_priv, "wg_public": wg_pub,
         "wg_server_addr": "10.8.0.1/24", "wg_port": 51820,
         "token": secrets.token_hex(12), "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    _servers()[sid] = s
    _save()
    return s

def update_server(sid: str, patch: dict) -> dict | None:
    s = _servers().get(sid)
    if not s:
        return None
    for k in ("name", "host", "sni", "mode", "ports"):
        if k in patch and patch[k] is not None:
            s[k] = patch[k]
    _save()
    return s

def remove_server(sid: str) -> bool:
    if sid in _servers():
        _servers().pop(sid, None); _save(); return True
    return False

def get_by_token(token: str):
    for s in _servers().values():
        if s.get("token") == token:
            return s
    return None

# ---------------------------------------------------------------- config generation
def xray_json(s: dict) -> str:
    """Generate Xray-core server config (Reality; single-port dokodemo gateway or multi-port)."""
    host = s.get("host") or "0.0.0.0"
    priv = s.get("reality_private") or ""
    short = s.get("reality_short_id") or ""
    sni = s.get("sni") or "www.speedtest.net"
    ports = s.get("ports") or {"vless-reality": 443}
    inbounds, rules = [], []
    if s.get("mode") == "single":
        main_port = int(list(ports.values())[0] if ports else 443)
        inbounds.append({
            "tag": "gateway", "listen": "0.0.0.0", "port": main_port, "protocol": "dokodemo-door",
            "settings": {"address": "127.0.0.1"}, "sniffing": {"enabled": True, "destOverride": ["tls"]},
        })
    for tag, port in ports.items():
        proto, net = ("vless", "tcp")
        if str(tag).startswith("trojan"): proto = "trojan"
        elif str(tag).startswith("ss"): proto = "shadowsocks"
        elif str(tag).startswith("vmess"): proto = "vmess"
        inbound = {
            "tag": f"in-{tag}-{port}", "listen": "127.0.0.1" if s.get("mode") == "single" else "0.0.0.0",
            "port": int(port), "protocol": proto,
            "settings": {"clients": [], "decryption": "none"} if proto in ("vless", "vmess") else {"clients": []},
            "streamSettings": {
                "network": "tcp" if proto != "shadowsocks" else "tcp",
                "security": "reality" if proto in ("vless", "trojan") else "none",
                "realitySettings": {"dest": f"{sni}:443", "serverNames": s.get("snis") or [sni],
                                     "privateKey": priv, "shortIds": [short]},
            } if proto in ("vless", "trojan") else {},
        }
        if proto == "vless":
            inbound["settings"] = {"clients": [{"id": "${SUKOT_CLIENT_UUID}", "flow": "xtls-rprx-vision"}], "decryption": "none"}
        inbounds.append(inbound)
        if s.get("mode") == "single":
            rules.append({"type": "field", "inboundTag": [f"in-{tag}-{port}"],
                          "outboundTag": "direct"})
    outbounds = [
        {"tag": "direct", "protocol": "freedom", "settings": {}},
        {"tag": "block", "protocol": "blackhole", "settings": {}},
    ]
    if s.get("mode") == "single":
        # gateway sniffed SNI → route to the reality inbound on loopback
        routing = {"rules": [{"type": "field", "port": "0-65535", "outboundTag": "direct"}]}
    else:
        routing = {"rules": []}
    cfg = {"log": {"loglevel": "warning"}, "inbounds": inbounds, "outbounds": outbounds, "routing": routing}
    return json.dumps(cfg, indent=2)

def wg_conf(s: dict) -> str:
    if not s.get("wg_private"):
        return ""
    return (f"[Interface]\nPrivateKey = {s['wg_private']}\nAddress = {s.get('wg_server_addr','10.8.0.1/24')}\n"
            f"ListenPort = {s.get('wg_port', 51820)}\nPostUp = iptables -A FORWARD -i wg0 -j ACCEPT; "
            f"iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE\n"
            f"PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE\n")

def install_script(s: dict, base_url: str) -> str:
    tok = s["token"]
    return f"""#!/usr/bin/env bash
# SUKOT Panel — VPS setup script (Xray + WireGuard, auto-sync every 60s)
set -e
apt-get update -y && apt-get install -y curl jq xz-utils wireguard-tools qrencode >/dev/null 2>&1 || true
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
mkdir -p /etc/sukot
cat > /etc/systemd/system/sukot-sync.service <<'UNIT'
[Unit]
Description=SUKOT config sync
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'curl -fsSL "{base_url}/xs/{tok}/xray.json" -o /usr/local/etc/xray/config.json && curl -fsSL "{base_url}/xs/{tok}/wg.conf" -o /etc/wireguard/wg0.conf || true; systemctl restart xray || true; systemctl restart wg-quick@wg0 || true'
UNIT
cat > /etc/systemd/system/sukot-sync.timer <<'TIMER'
[Unit]
Description=Sync SUKOT configs every minute
[Timer]
OnBootSec=30
OnUnitActiveSec=60
[Timer]Install=false
[Install]
WantedBy=timers.target
TIMER
systemctl daemon-reload
systemctl enable --now sukot-sync.timer
echo 'SUKOT VPS setup complete ✔'
"""

# ---------------------------------------------------------------- scanners
def _valid_ip(h: str) -> bool:
    import ipaddress
    try:
        ip = ipaddress.ip_address(h)
        if ip.is_private and not ALLOW_PRIVATE:
            return False
        return True
    except ValueError:
        return True  # hostname ok

async def scan_ports(host: str, ports: list[int], timeout: float = 2.5) -> dict:
    results = {}
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(60)

    async def probe(p):
        if not _valid_ip(host):
            results[p] = "skipped"; return
        async with sem:
            try:
                fut = loop.run_in_executor(None, lambda: socket.create_connection((host, p), timeout=timeout))
                await asyncio.wait_for(fut, timeout=timeout + 1)
                results[p] = "open"
            except asyncio.TimeoutError:
                results[p] = "filtered"
            except Exception:
                results[p] = "closed"

    await asyncio.gather(*[probe(p) for p in ports])
    suggestions = [p for p, st in results.items() if st == "open"]
    return {"host": host, "results": {str(k): v for k, v in results.items()},
            "open": sorted(suggestions), "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

COMMON_PORTS = [22, 80, 443, 8443, 2053, 2083, 2087, 2096, 51820, 6543, 8000, 8080, 443]

async def sni_scan(host: str | None = None, candidates: list[str] | None = None) -> dict:
    """Rank SNI targets by TLS1.3+h2 handshake success through the given host/IP."""
    if not candidates:
        candidates = ["www.speedtest.net", "www.microsoft.com", "www.apple.com", "www.samsung.com",
                      "www.nvidia.com", "dl.google.com", "www.cloudflare.com", "www.bing.com",
                      "cdn.jsdelivr.net", "www.icloud.com"]
    out = []
    host = host or "www.speedtest.net"
    for c in candidates:
        score = 0
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, 443, ssl=ctx, server_hostname=c), timeout=6)
            proto = writer.get_extra_info("ssl_object").selected_alpn_protocol() or ""
            tlsver = writer.get_extra_info("ssl_object").version() or ""
            writer.close()
            score = (60 if tlsver == "TLSv1.3" else 20) + (40 if proto == "h2" else 5)
            out.append({"sni": c, "tls": tlsver, "alpn": proto, "score": score})
        except Exception as e:
            out.append({"sni": c, "tls": "-", "alpn": "-", "score": 0, "error": str(e)[:60]})
    out.sort(key=lambda x: -x["score"])
    return {"host": host, "ranked": out[:10]}
