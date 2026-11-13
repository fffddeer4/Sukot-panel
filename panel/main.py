# main.py — SUKOT Panel: FastAPI app + routes (Shiprr-ready, single port)
import os, io, json, time, base64, secrets, hashlib, hmac
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException, Form, WebSocket, Body, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, PlainTextResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from starlette.status import WS_1008_POLICY_VIOLATION

import core
from core import (APP_NAME, APP_VERSION, load_state, save_state, settings, SESSIONS, SESSION_COOKIE,
                  create_session, get_session, destroy_session, revoke_other_sessions,
                  verify_admin_credentials, hash_password, verify_password, admin_record,
                  login_lock_info, login_fail, login_ok, now_iso, parse_iso, human_bytes,
                  gb_to_bytes, log_activity, log_error, client_error, bump_daily,
                  client_ip_from_headers, split_xff, random_config_names, build_config_remark,
                  build_info_server_remark, PORT, VW_TLS, VW_FORCE_PORT)
import links as ln
from links import (links, get_link, get_link_info, is_link_allowed, make_link, remove_link_everywhere,
                   create_sub_group, subs, PROTOCOLS, LIVE_PROTOCOLS, vless_link_for_link,
                   config_lines_for, subscription_headers, sub_url_for, portal_url_for)
import relays, tcp_relay, speed_limit, outbound, keepalive, operators, nodes as nodes_mod, vps_serv
from ui import login as ui_login, dashboard as ui_dash, portal as ui_portal

# ---------------------------------------------------------------- app setup
app = FastAPI(title="SUKOT Panel", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1024)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_assets")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

START_TS = time.time()
TELEMETRY = {"cpu_h": deque(maxlen=40), "ram_h": deque(maxlen=40)}
BOT_OBJ = {"running": False}

def base_url() -> str:
    return core.public_url().rstrip("/")

# ---------------------------------------------------------------- auth helpers
def _tok(request: Request) -> Optional[str]:
    t = request.cookies.get(SESSION_COOKIE)
    if t and get_session(t):
        return t
    t = request.headers.get("x-sk-session")
    if t and get_session(t):
        return t
    return None

def require_auth(request: Request) -> dict:
    t = _tok(request)
    if not t:
        raise HTTPException(status_code=401, detail="unauthorized")
    rec = SESSIONS[t]
    adm = admin_record(rec.get("admin_id"))
    if not adm or not adm.get("active", True):
        raise HTTPException(status_code=401, detail="unauthorized")
    adm = dict(adm)
    adm["perm"] = set(rec.get("permissions") or adm.get("permissions") or [])
    if adm.get("role") == "owner":
        adm["perm"] = set(core.ALL_PERMISSIONS) | {"*"}
    return adm

def require_owner(request: Request) -> dict:
    adm = require_auth(request)
    if adm.get("role") != "owner":
        raise HTTPException(status_code=403, detail="فقط مالک پنل")
    return adm

def need(perm: str):
    def dep(request: Request) -> dict:
        adm = require_auth(request)
        if "*" not in adm["perm"] and perm not in adm["perm"]:
            raise HTTPException(status_code=403, detail="دسترسی نداری")
        return adm
    return dep

def _set_cookie(resp: RedirectResponse | JSONResponse, tok: str, remember: bool):
    max_age = (core.SESSION_TTL_REMEMBER if remember else core.SESSION_TTL_DEFAULT)
    resp.set_cookie(SESSION_COOKIE, tok, max_age=max_age, httponly=True, samesite="lax",
                    secure=request_secure)
request_secure = False

def is_https(request: Request) -> bool:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or ""
    return "https" in str(proto)

# ---------------------------------------------------------------- pages
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if _tok(request):
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    global request_secure
    request_secure = is_https(request)
    if _tok(request):
        return RedirectResponse("/dashboard", status_code=302)
    return HTMLResponse(ui_login.render())

@app.post("/login")
async def login_submit(request: Request, username: str = Form(""), password: str = Form(""),
                       remember: str = Form("")):
    global request_secure
    request_secure = is_https(request)
    ip = client_ip_from_headers(request.headers, request.client)
    lock = login_lock_info(ip)
    if lock:
        return _login_error(f"تعداد تلاش‌ها زیاد بود؛ {max(1, lock // 60)} دقیقه دیگر دوباره امتحان کن.", username)
    adm = verify_admin_credentials(username, password)
    if not adm:
        login_fail(ip)
        rem = max(0, 5 - len({}))
        try:
            rec = core._LOGIN_FAILS.get(ip)
            rem = max(0, 5 - (rec["count"] if rec else 0))
        except Exception:
            rem = 1
        return _login_error(f"رمز عبور اشتباه است. {rem} تلاش دیگر باقی مانده است.", username)
    login_ok(ip)
    tok = create_session(adm["admin_id"], adm["role"], adm.get("permissions"), remember=bool(remember))
    log_activity("ورود موفق به پنل", actor=adm["admin_id"])
    resp = RedirectResponse("/dashboard?login=1", status_code=303)
    max_age = (core.SESSION_TTL_REMEMBER if remember else core.SESSION_TTL_DEFAULT)
    resp.set_cookie(SESSION_COOKIE, tok, max_age=max_age, httponly=True, samesite="lax",
                    secure=is_https(request))
    return resp

def _login_error(msg: str, username: str):
    return HTMLResponse(ui_login.render(error=msg), status_code=401)

@app.post("/api/login")
async def api_login(request: Request, body: dict = Body(...)):
    ip = client_ip_from_headers(request.headers, request.client)
    lock = login_lock_info(ip)
    if lock:
        return JSONResponse({"ok": False, "error": "قفل موقت ورود"}, status_code=429)
    adm = verify_admin_credentials(str(body.get("username") or ""), str(body.get("password") or ""))
    if not adm:
        login_fail(ip)
        return JSONResponse({"ok": False, "error": "نام کاربری یا رمز اشتباه است"}, status_code=401)
    login_ok(ip)
    tok = create_session(adm["admin_id"], adm["role"], adm.get("permissions"),
                         remember=bool(body.get("remember")))
    resp = JSONResponse({"ok": True, "role": adm["role"]})
    resp.set_cookie(SESSION_COOKIE, tok, max_age=core.SESSION_TTL_DEFAULT, httponly=True,
                    samesite="lax", secure=is_https(request))
    return resp

@app.get("/logout")
async def logout(request: Request):
    t = request.cookies.get(SESSION_COOKIE)
    if t:
        destroy_session(t)
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(SESSION_COOKIE)
    return resp

@app.post("/api/logout")
async def api_logout(request: Request):
    t = _tok(request)
    if t:
        destroy_session(t)
    return {"ok": True}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    if not _tok(request):
        return RedirectResponse("/login", status_code=302)
    return HTMLResponse(ui_dash.render())

@app.get("/health")
@app.get("/ping")
@app.get("/healthz")
async def health():
    return {"ok": True, "app": APP_NAME, "version": APP_VERSION, "t": now_iso()}

@app.get("/manifest.webmanifest")
async def manifest():
    return JSONResponse({
        "name": "SUKOT Panel", "short_name": "SUKOT", "start_url": "/dashboard",
        "display": "standalone", "background_color": "#0a0709", "theme_color": "#ff3d54",
        "icons": [{"src": "/assets/logo.webp", "sizes": "512x512", "type": "image/webp"},
                  {"src": "/assets/favicon.png", "sizes": "64x64", "type": "image/png"}]})

# ---------------------------------------------------------------- me / telemetry
@app.get("/api/me")
async def api_me(request: Request):
    adm = require_auth(request)
    return {"username": adm["admin_id"], "role": adm["role"], "permissions": sorted(adm["perm"])}

NET_LAST = {"t": 0.0, "rx": 0, "tx": 0, "rate": 0.0}

@app.get("/api/telemetry")
async def telemetry(_=Depends(require_auth)):
    import psutil, platform
    vm = psutil.virtual_memory()
    du = psutil.disk_usage("/")
    nt = psutil.net_io_counters()
    now = time.time()
    dt = now - NET_LAST["t"]
    if dt >= 2 and NET_LAST["t"] > 0:
        rx = max(0, nt.bytes_recv - NET_LAST["rx"]) / dt
        tx = max(0, nt.bytes_sent - NET_LAST["tx"]) / dt
        NET_LAST["rate"] = rx + tx
    elif NET_LAST["t"] == 0:
        NET_LAST["rate"] = 0.0
    NET_LAST.update({"t": now, "rx": nt.bytes_recv, "tx": nt.bytes_sent})
    TELEMETRY["cpu_h"].append(psutil.cpu_percent())
    TELEMETRY["ram_h"].append(vm.percent)
    return {"cpu": psutil.cpu_percent(), "ram": vm.percent,
            "ram_used": vm.used, "ram_total": vm.total,
            "swap": getattr(psutil.swap_memory(), "percent", 0),
            "disk": du.percent, "disk_used": du.used, "disk_total": du.total,
            "net_rate_s": human_bytes(NET_LAST["rate"]) + "/s",
            "net_rate": min(100.0, NET_LAST["rate"] / (50 * 1024 * 1024) * 100),
            "cpu_h": list(TELEMETRY["cpu_h"]), "ram_h": list(TELEMETRY["ram_h"]),
            "uptime_s": time.time() - START_TS, "platform": f"{platform.system()} · {platform.release()}",
            "public_url": core.public_url()}

@app.get("/stats")
async def stats(_=Depends(require_auth)):
    st = links()
    return {"links_total": len(st),
            "links_active": sum(1 for c in st.values() if is_link_allowed(c)),
            "traffic_bytes": sum(c.get("used_bytes") or 0 for c in st.values()),
            "online": len(core.TUNNELS_NOW),
            "subs": len(subs()),
            "admins": 1 + len(core.admins()),
            "bot_running": bool(BOT_OBJ["running"])}

@app.get("/api/connections")
async def api_connections(_=Depends(need("live_connections"))):
    items = []
    for uid, n in core.TUNNELS_NOW.items():
        c = get_link(uid)
        if c:
            ips = list(core.CONNECTED_IPS.get(uid) or [])
            for ip in (ips or ["—"]):
                items.append({"uuid": uid, "label": c.get("label"), "ip": ip, "bytes": c.get("used_bytes") or 0})
    return {"total": len(core.TUNNELS_NOW),
            "ips": len({ip for ips in core.CONNECTED_IPS.values() for ip in ips}),
            "items": items[:40]}

@app.get("/api/activity")
async def api_activity(_=Depends(require_auth)):
    return {"items": list(core.ACTIVITY)}

@app.get("/api/errors")
async def api_errors(_=Depends(require_auth)):
    return {"items": list(core.ERRORS)}

@app.post("/api/errors/client")
async def api_errors_client(request: Request):
    try:
        b = await request.json()
        client_error(str(b.get("message") or ""), str(b.get("page") or ""))
    except Exception:
        pass
    return {"ok": True}

@app.post("/api/errors/clear")
async def api_errors_clear(_=Depends(need("messages"))):
    core.ERRORS.clear()
    return {"ok": True}

@app.get("/api/reports/summary")
async def reports_summary(request: Request, days: int = 7, _=Depends(need("reports"))):
    days = max(1, min(days, 90))
    ds = load_state().get("daily_stats") or {}
    import datetime as _dt
    out = []
    traffic = 0
    for i in range(days - 1, -1, -1):
        d = (_dt.date.today() - _dt.timedelta(days=i)).isoformat()
        rec = ds.get(d) or {}
        traffic += rec.get("traffic_bytes") or 0
        out.append({"day": d, "traffic_bytes": rec.get("traffic_bytes") or 0,
                    "new_links": rec.get("new_links") or 0})
    st = links()
    top = sorted(st.values(), key=lambda c: -(c.get("used_bytes") or 0))[:10]
    return {"total": len(st),
            "active": sum(1 for c in st.values() if is_link_allowed(c)),
            "subs": len(subs()), "traffic": traffic, "daily": out,
            "top": [{"label": c.get("label"), "used_bytes": c.get("used_bytes") or 0} for c in top]}

@app.get("/api/reports/export.csv")
async def reports_csv(days: int = 30, _=Depends(need("reports"))):
    import datetime as _dt
    ds = load_state().get("daily_stats") or {}
    rows = ["date,traffic_bytes,new_links,orders"]
    for i in range(days - 1, -1, -1):
        d = (_dt.date.today() - _dt.timedelta(days=i)).isoformat()
        rec = ds.get(d) or {}
        rows.append(f"{d},{rec.get('traffic_bytes', 0)},{rec.get('new_links', 0)},{rec.get('orders', 0)}")
    return PlainTextResponse("\n".join(rows), media_type="text/csv",
                             headers={"content-disposition": "attachment; filename=sukot-report.csv"})

# ---------------------------------------------------------------- protocols / operators / names
@app.get("/api/protocols")
async def api_protocols(_=Depends(require_auth)):
    return {"items": PROTOCOLS}

@app.get("/api/reality-keypair")
async def reality_keypair(_=Depends(require_auth)):
    import base64 as _b, subprocess, tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            pass
        priv = subprocess.run(["openssl", "genpkey", "-algorithm", "x25519"], capture_output=True, timeout=8).stdout
        open(f.name, "wb").write(priv)
        pubp = subprocess.run(["openssl", "pkey", "-in", f.name, "-pubout"], capture_output=True, timeout=8).stdout
        from cryptography.hazmat.primitives.serialization import load_pem_private_public_key
        pk = load_pem_private_public_key(priv, None)
        pub = load_pem_private_public_key(pubp, None)
        os.unlink(f.name)
        return {"private": _b.urlsafe_b64encode(pk.private_bytes_raw()).decode().rstrip("="),
                "public": _b.urlsafe_b64encode(pub.public_key().public_bytes_raw()).decode().rstrip("=")}
    except Exception as e:
        return {"error": str(e)[:120]}

@app.get("/api/name-suggestions")
async def name_suggestions(n: int = 6, _=Depends(require_auth)):
    return {"items": random_config_names(count=min(max(n, 1), 12))}

@app.get("/api/operators")
async def api_operators(_=Depends(require_auth)):
    return {"items": operators.get_operators()}

@app.post("/api/operators/{key}")
async def api_operators_set(key: str, body: dict = Body(...), _=Depends(require_owner)):
    r = operators.set_operator(key, body)
    if not r:
        raise HTTPException(404, "اپراتور پیدا نشد")
    return {"ok": True}

# ---------------------------------------------------------------- links CRUD
@app.get("/api/links")
async def api_links(request: Request, _=Depends(need("dashboard"))):
    adm = require_auth(request)
    items = []
    for c in links().values():
        if not ln.scope_allows_inbound(adm, c["uuid"]):
            continue
        if c.get("parent_inbound_id"):
            if not ln.client_visible(c, adm):
                continue
        info = get_link_info(c)
        info["speed_mbit"] = round((c.get("speed_limit_bytes") or 0) * 8 / 1_000_000, 1)
        items.append(info)
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return {"items": items}

@app.post("/api/links")
async def api_links_create(request: Request, body: dict = Body(...), _=Depends(need("inbound_create"))):
    adm = require_auth(request)
    preset = operators.preset_for(str(body.get("operator") or "all"))
    days = int(body.get("days") or 0)
    expires = None
    if body.get("expires_at"):
        expires = str(body.get("expires_at"))
    elif days > 0:
        expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    c = make_link(
        label=str(body.get("label") or ""),
        limit_bytes=gb_to_bytes(body.get("limit_gb") or body.get("limit_value") or 0),
        expires_at=expires,
        protocol=str(body.get("protocol") or "vless-ws"),
        fingerprint=body.get("fingerprint") or preset["fingerprint"],
        alpn=body.get("alpn") or preset["alpn"],
        port=int(body.get("port") or (VW_FORCE_PORT if VW_TLS else 443)),
        fragment=body.get("fragment") or preset["fragment"],
        ip_limit=int(body.get("ip_limit") or 0),
        connection_limit=int(body.get("connection_limit") or 0),
        speed_limit_bytes=int((float(body.get("speed_mbit") or 0)) * 1_000_000 / 8),
        category_id=str(body.get("category_id") or ""),
        note=str(body.get("note") or ""),
        clean_ips=body.get("clean_ips") or [],
        config_count=int(body.get("config_count") or 1),
        client_limit=int(body.get("client_limit") or 0),
        operator=str(body.get("operator") or ""),
        created_by=adm["admin_id"],
        manual=body.get("manual") if isinstance(body.get("manual"), dict) else None,
    )
    log_activity(f"اینباند «{c['label']}» ساخته شد", actor=adm["admin_id"])
    return {"ok": True, "uuid": c["uuid"], "sub_url": sub_url_for(c["uuid"])}

@app.get("/api/links/{uid}/info")
async def api_link_info(uid: str, _=Depends(need("dashboard"))):
    c = get_link(uid)
    if not c:
        raise HTTPException(404, "پیدا نشد")
    info = get_link_info(c)
    info["speed_mbit"] = round((c.get("speed_limit_bytes") or 0) * 8 / 1_000_000, 1)
    info["link_uri"] = vless_link_for_link(c)
    info["portal_url"] = portal_url_for(uid)
    return {"item": info}

@app.patch("/api/links/{uid}")
async def api_link_edit(uid: str, body: dict = Body(...), _=Depends(need("inbound_edit"))):
    c = get_link(uid)
    if not c:
        raise HTTPException(404, "پیدا نشد")
    if body.get("label"):
        c["label"] = core.sanitize_label(body["label"])
    if body.get("set_limit_gb") is not None:
        c["limit_bytes"] = gb_to_bytes(body["set_limit_gb"])
    if body.get("add_bytes"):
        c["limit_bytes"] = (c.get("limit_bytes") or 0) + int(body["add_bytes"])
    if body.get("extend_days"):
        base = parse_iso(c.get("expires_at")) or datetime.now(timezone.utc)
        if base < datetime.now(timezone.utc):
            base = datetime.now(timezone.utc)
        c["expires_at"] = (base + timedelta(days=int(body["extend_days"]))).isoformat()
    if body.get("expires_at"):
        c["expires_at"] = str(body["expires_at"])
    if body.get("ip_limit") is not None:
        c["ip_limit"] = int(body["ip_limit"] or 0)
    if body.get("speed_mbit") is not None:
        c["speed_limit_bytes"] = int((float(body["speed_mbit"] or 0)) * 1_000_000 / 8)
    if body.get("category_id") is not None:
        c["category_id"] = str(body["category_id"] or "")
    if body.get("note") is not None:
        c["note"] = str(body["note"])
    if body.get("operator") is not None:
        c["operator"] = str(body["operator"])
    if body.get("config_count") is not None:
        c["config_count"] = max(1, min(int(body["config_count"] or 1), 40))
    if body.get("reset_usage"):
        c["used_bytes"] = 0
        speed_limit.reset_bucket(uid)
    save_state()
    log_activity(f"اینباند «{c['label']}» ویرایش شد", actor="panel")
    return {"ok": True}

@app.post("/api/links/{uid}/regenerate")
async def api_link_regen(uid: str, _=Depends(need("inbound_edit"))):
    c = get_link(uid)
    if not c:
        raise HTTPException(404, "پیدا نشد")
    old = uid
    new = core.new_uuid4()
    c["uuid"] = new
    links()[new] = links().pop(old)
    for ch in links().values():
        if ch.get("parent_inbound_id") == old:
            ch["parent_inbound_id"] = new
    for s in subs().values():
        if old in s.get("link_ids", []):
            s["link_ids"][s["link_ids"].index(old)] = new
    save_state()
    log_activity(f"لینک «{c['label']}» تعویض شد", actor="panel")
    return {"ok": True, "uuid": new}

@app.post("/api/links/{uid}/action")
async def api_link_action(uid: str, body: dict = Body(...), _=Depends(need("inbound_edit"))):
    c = get_link(uid)
    if not c:
        raise HTTPException(404, "پیدا نشد")
    action = str(body.get("action") or "")
    if action == "reset":
        c["used_bytes"] = 0
        speed_limit.reset_bucket(uid)
    elif action == "enable":
        c["active"] = True
    elif action == "disable":
        c["active"] = False
    elif action == "toggle":
        c["active"] = not c.get("active", True)
    else:
        raise HTTPException(400, "عملیات نامعتبر")
    save_state()
    return {"ok": True, "active": c["active"]}

@app.delete("/api/links/{uid}")
async def api_link_delete(uid: str, _=Depends(need("inbound_delete"))):
    c = get_link(uid)
    if not c:
        raise HTTPException(404, "پیدا نشد")
    for ch in [x for x in links().values() if x.get("parent_inbound_id") == uid]:
        remove_link_everywhere(ch["uuid"])
        links().pop(ch["uuid"], None)
    remove_link_everywhere(uid)
    links().pop(uid, None)
    save_state()
    log_activity(f"کانفیگ «{c.get('label')}» حذف شد", actor="panel")
    return {"ok": True}

# ---------------------------------------------------------------- clients
@app.get("/api/links/{uid}/clients")
async def api_clients(request: Request, uid: str, _=Depends(need("dashboard"))):
    adm = require_auth(request)
    items = []
    for c in links().values():
        if c.get("parent_inbound_id") != uid or not ln.client_visible(c, adm):
            continue
        info = get_link_info(c)
        info["speed_mbit"] = round((c.get("speed_limit_bytes") or 0) * 8 / 1_000_000, 1)
        items.append(info)
    return {"items": items}

@app.post("/api/links/{uid}/clients")
async def api_client_add(request: Request, uid: str, body: dict = Body(...), _=Depends(need("client_create"))):
    parent = get_link(uid)
    if not parent:
        raise HTTPException(404, "اینباند پیدا نشد")
    children = sum(1 for c in links().values() if c.get("parent_inbound_id") == uid)
    lim = parent.get("client_limit") or 0
    if lim and children >= lim:
        raise HTTPException(400, "سقف کلاینت این اینباند پر است")
    adm = require_auth(request)
    days = int(body.get("days") or 0)
    expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat() if days else parent.get("expires_at")
    vol = gb_to_bytes(body.get("limit_gb") or 0) or parent.get("limit_bytes") or 0
    c = make_link(label=str(body.get("label") or f"client-{children+1}"),
                  limit_bytes=vol, expires_at=expires,
                  protocol=parent.get("protocol"), fingerprint=parent.get("fingerprint"),
                  alpn=parent.get("alpn"), port=parent.get("port"), fragment=parent.get("fragment"),
                  ip_limit=int(body.get("ip_limit") or parent.get("ip_limit") or 0),
                  connection_limit=parent.get("connection_limit"),
                  speed_limit_bytes=parent.get("speed_limit_bytes"),
                  parent_inbound_id=uid, created_by=adm["admin_id"])
    return {"ok": True, "item": get_link_info(c)}

@app.delete("/api/links/{uid}/clients/{cid}")
async def api_client_del(uid: str, cid: str, _=Depends(need("client_delete"))):
    c = get_link(cid)
    if not c or c.get("parent_inbound_id") != uid:
        raise HTTPException(404, "پیدا نشد")
    links().pop(cid, None)
    save_state()
    return {"ok": True}

# ---------------------------------------------------------------- categories
@app.get("/api/categories")
async def api_categories(_=Depends(need("categories"))):
    return {"items": [{"id": k, **v} for k, v in load_state().get("categories", {}).items()]}

@app.post("/api/categories")
async def api_categories_add(body: dict = Body(...), _=Depends(need("categories"))):
    cats = load_state().setdefault("categories", {})
    if len(cats) >= 10:
        raise HTTPException(400, "حداکثر ۱۰ دسته")
    cid = core.rand_key(8)
    cats[cid] = {"name": core.sanitize_label(body.get("name") or "بدون نام", 32),
                 "number": len(cats) + 1}
    save_state()
    return {"ok": True, "id": cid}

@app.delete("/api/categories/{cid}")
async def api_categories_del(cid: str, _=Depends(need("categories"))):
    cats = load_state().setdefault("categories", {})
    if cid in cats:
        cats.pop(cid)
        save_state()
    return {"ok": True}

# ---------------------------------------------------------------- sub groups
@app.get("/api/subs")
async def api_subs(_=Depends(need("subgroups"))):
    b = base_url()
    items = []
    for s in subs().values():
        items.append({"id": s["id"], "name": s["name"], "count": len(s.get("link_ids") or []),
                      "has_password": bool(s.get("password_hash")),
                      "public_url": f"{b}/sub-group/{s['uuid_key']}"})
    return {"items": items}

@app.post("/api/subs")
async def api_subs_create(body: dict = Body(...), _=Depends(need("subgroups"))):
    ids = [str(x) for x in (body.get("link_ids") or []) if get_link(str(x))]
    if len(ids) < 2:
        raise HTTPException(400, "حداقل دو کانفیگ انتخاب کن")
    s = create_sub_group(str(body.get("name") or ""), ids, password=str(body.get("password") or ""))
    b = base_url()
    return {"ok": True, "item": {"id": s["id"], "name": s["name"],
            "public_url": f"{b}/sub-group/{s['uuid_key']}"}}

@app.delete("/api/subs/{sid}")
async def api_subs_del(sid: str, _=Depends(need("subgroups"))):
    subs().pop(sid, None)
    save_state()
    return {"ok": True}

# ---------------------------------------------------------------- settings / security
@app.get("/api/settings")
async def api_settings(_=Depends(require_owner)):
    s = dict(settings())
    s["password_hash"] = None
    return {"settings": s}

@app.post("/api/settings")
async def api_settings_save(request: Request, body: dict = Body(...), _=Depends(require_owner)):
    s = settings()
    for k in ("public_base_url", "tcp_public_host", "tcp_public_port", "bot_token", "bot_admin_ids",
              "support_username", "channel_username", "sub_remark_name", "sub_remark_volume",
              "sub_remark_id", "sub_remark_inbound", "sub_info_line_name", "sub_info_line_volume",
              "sub_info_line_id", "sub_info_line_inbound", "name_style_enabled", "info_server_name"):
        if k in body:
            s[k] = body[k]
    save_state()
    import sukot_bot
    if "bot_token" in body or "bot_admin_ids" in body:
        sukot_bot.configure(str(body.get("bot_token") or ""), str(body.get("bot_admin_ids") or ""))
    if body.get("bot_auto_start") or body.get("bot_token"):
        try:
            BOT_OBJ["running"] = bool(await sukot_bot.start_bot())
        except Exception as e:
            log_error("bot start: " + str(e), "bot")
    return {"ok": True}

@app.post("/api/change-username")
async def change_username(body: dict = Body(...), _=Depends(require_owner)):
    u = core.sanitize_label(str(body.get("username") or ""), 40).replace(" ", "_")
    if not u:
        raise HTTPException(400, "نام کاربری نامعتبر")
    load_state()["username"] = u
    save_state()
    return {"ok": True, "username": u}

@app.post("/api/change-password")
async def change_password(body: dict = Body(...), _=Depends(require_owner)):
    st = load_state()
    if not verify_password(str(body.get("old_password") or ""), st.get("password_hash") or ""):
        raise HTTPException(400, "رمز فعلی اشتباه است")
    new = str(body.get("new_password") or "")
    if len(new) < 6:
        raise HTTPException(400, "رمز جدید کوتاه است (حداقل ۶ کاراکتر)")
    st["password_hash"] = hash_password(new)
    save_state()
    log_activity("رمز عبور مالک تغییر کرد", actor="owner")
    return {"ok": True}

@app.post("/api/security/revoke-other-sessions")
async def revoke_sessions(request: Request, _=Depends(require_auth)):
    t = _tok(request)
    rec = SESSIONS.get(t) if t else None
    n = revoke_other_sessions(rec.get("admin_id") if rec else "", t)
    return {"ok": True, "revoked": n}

# ---------------------------------------------------------------- bot control
@app.get("/api/bot/status")
async def bot_status(_=Depends(require_auth)):
    import sukot_bot
    return {"running": bool(sukot_bot.running())}

@app.post("/api/bot/start")
async def bot_start(_=Depends(require_owner)):
    import sukot_bot
    ok = await sukot_bot.start_bot()
    BOT_OBJ["running"] = bool(ok)
    if not ok and not sukot_bot.TOKEN:
        raise HTTPException(400, "توکن ربات تنظیم نشده")
    return {"ok": ok}

@app.post("/api/bot/stop")
async def bot_stop(_=Depends(require_owner)):
    import sukot_bot
    await sukot_bot.stop_bot()
    BOT_OBJ["running"] = False
    return {"ok": True}

# ---------------------------------------------------------------- admin accounts
@app.get("/api/admins")
async def api_admins(_=Depends(require_owner)):
    items = [{"admin_id": load_state().get("username") or core.ADMIN_USERNAME, "role": "owner",
              "active": True, "permissions": core.ALL_PERMISSIONS}]
    for aid, a in core.admins().items():
        items.append({"admin_id": aid, "role": a.get("role", "admin"), "active": a.get("active", True),
                      "permissions": a.get("permissions") or [], "allowed_inbounds": a.get("allowed_inbounds") or []})
    return {"items": items}

@app.post("/api/admins")
async def api_admins_add(body: dict = Body(...), _=Depends(require_owner)):
    aid = core.sanitize_label(str(body.get("admin_id") or ""), 40).replace(" ", "_")
    if not aid or aid.lower() in ("owner",):
        raise HTTPException(400, "نام کاربری نامعتبر")
    a = core.admins()
    if aid in a:
        raise HTTPException(400, "این نام قبلاً وجود دارد")
    a[aid] = {"role": "admin", "password_hash": hash_password(str(body.get("password") or "")),
              "permissions": [p for p in (body.get("permissions") or []) if p in core.ALL_PERMISSIONS],
              "allowed_inbounds": body.get("allowed_inbounds") or [], "active": True,
              "created": now_iso()}
    save_state()
    log_activity(f"ادمین «{aid}» ساخته شد", actor="owner")
    return {"ok": True}

@app.patch("/api/admins/{aid}")
async def api_admins_edit(aid: str, body: dict = Body(...), _=Depends(require_owner)):
    a = core.admins().get(aid)
    if not a:
        raise HTTPException(404, "پیدا نشد")
    if body.get("permissions") is not None:
        a["permissions"] = [p for p in body["permissions"] if p in core.ALL_PERMISSIONS]
    if body.get("password"):
        a["password_hash"] = hash_password(str(body["password"]))
    if body.get("active") is not None:
        a["active"] = bool(body["active"])
    save_state()
    return {"ok": True}

@app.delete("/api/admins/{aid}")
async def api_admins_del(aid: str, _=Depends(require_owner)):
    if aid in core.admins():
        core.admins().pop(aid)
        save_state()
    return {"ok": True}

@app.post("/api/admin-requests")
async def admin_request_submit(request: Request, body: dict = Body(...)):
    ip = client_ip_from_headers(request.headers, request.client)
    # simple 60s cooldown per ip
    key = "req:" + ip
    last = getattr(app.state, "req_times", {})
    if time.time() - last.get(key, 0) < 60:
        raise HTTPException(429, "کمی صبر کن و دوباره بفرست")
    last[key] = time.time()
    app.state.req_times = last
    st = load_state()
    reqs = st.setdefault("admin_requests", [])
    reqs.append({"id": core.rand_key(10), "name": core.sanitize_label(body.get("name") or "", 60),
                 "tg": str(body.get("tg") or "")[:40], "note": str(body.get("note") or "")[:300],
                 "t": now_iso()})
    save_state()
    log_activity("درخواست همکاری ادمینی ثبت شد", actor=body.get("tg") or "anonymous")
    return {"ok": True}

@app.get("/api/admin-requests")
async def admin_request_list(_=Depends(require_owner)):
    return {"items": load_state().get("admin_requests", [])}

@app.post("/api/admin-requests/{rid}/{action}")
async def admin_request_act(rid: str, action: str, _=Depends(require_owner)):
    reqs = load_state().get("admin_requests", [])
    rec = next((r for r in reqs if r.get("id") == rid), None)
    if not rec:
        raise HTTPException(404, "پیدا نشد")
    reqs.remove(rec)
    if action == "approve":
        base = "admin" + rid[:4]
        aid = base
        n = 1
        while aid in core.admins():
            aid = f"{base}{n}"; n += 1
        core.admins()[aid] = {"role": "admin", "password_hash": hash_password(secrets.token_urlsafe(9)),
                              "permissions": core.DEFAULT_ADMIN_PERMS, "allowed_inbounds": [],
                              "active": True, "created": now_iso(), "tg": rec.get("tg")}
        log_activity(f"ادمین «{aid}» از درخواست ساخته شد", actor="owner")
    save_state()
    return {"ok": True}

# ---------------------------------------------------------------- nodes
@app.get("/api/node/token")
async def node_token(_=Depends(require_owner)):
    return {"token": nodes_mod.node_token()}

@app.get("/api/node/info")
async def node_info(request: Request):
    auth = request.headers.get("authorization") or ""
    if not (auth.startswith("Bearer ") and nodes_mod.authorize_node(auth[7:].strip())):
        raise HTTPException(401, "node token required")
    return nodes_mod.node_info_self()

@app.get("/api/nodes")
async def api_nodes(_=Depends(need("nodes"))):
    return {"items": nodes_mod.list_nodes()}

@app.post("/api/nodes")
async def api_nodes_add(body: dict = Body(...), _=Depends(need("nodes"))):
    n = nodes_mod.upsert_node(str(body.get("name") or "node"), str(body.get("url") or ""),
                              str(body.get("token") or ""))
    asyncio.create_task(nodes_mod.probe_node({**n, "id": list(nodes_mod.NODES.keys())[-1]}))
    return {"ok": True, "id": list(nodes_mod.NODES.keys())[-1]}

@app.delete("/api/nodes/{nid}")
async def api_nodes_del(nid: str, _=Depends(need("nodes"))):
    return {"ok": nodes_mod.remove_node(nid)}

@app.post("/api/nodes/{nid}/check")
async def api_nodes_check(nid: str, _=Depends(need("nodes"))):
    n = nodes_mod.NODES.get(nid)
    if not n:
        raise HTTPException(404)
    st = await nodes_mod.probe_node({**n, "id": nid})
    return {"status": st.get("status"), "error": st.get("error"), "latency_ms": st.get("latency_ms")}

import asyncio
@app.post("/api/nodes/check-all")
async def api_nodes_check_all(_=Depends(need("nodes"))):
    await nodes_mod.check_all()
    return {"ok": True}

# ---------------------------------------------------------------- vps
@app.get("/api/vps")
async def api_vps(_=Depends(need("vps"))):
    return {"items": vps_serv.list_servers()}

@app.post("/api/vps")
async def api_vps_add(body: dict = Body(...), _=Depends(need("vps"))):
    s = vps_serv.add_server(str(body.get("name") or "server"), str(body.get("host") or ""),
                            str(body.get("mode") or "single"), body.get("ports") or {},
                            str(body.get("sni") or "www.speedtest.net"))
    return {"ok": True, "item": s}

@app.get("/api/vps/{sid}")
async def api_vps_get(sid: str, _=Depends(need("vps"))):
    s = vps_serv._servers().get(sid)
    if not s:
        raise HTTPException(404)
    b = base_url()
    return {"item": {k: v for k, v in s.items() if not k.endswith("private")},
            "install_url": f"{b}/xs/{s['token']}/install.sh",
            "xray_url": f"{b}/xs/{s['token']}/xray.json",
            "wg_url": f"{b}/xs/{s['token']}/wg.conf"}

@app.put("/api/vps/{sid}")
async def api_vps_edit(sid: str, body: dict = Body(...), _=Depends(need("vps"))):
    s = vps_serv.update_server(sid, body)
    if not s:
        raise HTTPException(404)
    return {"ok": True}

@app.delete("/api/vps/{sid}")
async def api_vps_del(sid: str, _=Depends(need("vps"))):
    return {"ok": vps_serv.remove_server(sid)}

@app.post("/api/vps/{sid}/check")
async def api_vps_check(sid: str, _=Depends(need("vps"))):
    s = vps_serv._servers().get(sid)
    if not s:
        raise HTTPException(404)
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection(s.get("host"), 443), 5)
        w.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}

@app.post("/api/vps/scan")
async def api_vps_scan(body: dict = Body(...), _=Depends(need("vps"))):
    sid = body.get("sid")
    s = vps_serv._servers().get(str(sid)) if sid else None
    host = s.get("host") if s else str(body.get("host") or "")
    ports = body.get("ports") or ([443, 8443, 2053, 2083, 2087, 2096, 8080, 51820, 6543, 22] if not s else
                                  [int(p) for p in (s.get("ports") or {}).values()] + [22, 80])
    ports = sorted(set(int(p) for p in ports if p))
    return await vps_serv.scan_ports(host, ports)

@app.post("/api/vps/sni-scan")
async def api_vps_sni(body: dict = Body(...), _=Depends(need("vps"))):
    sid = body.get("sid")
    s = vps_serv._servers().get(str(sid)) if sid else None
    host = s.get("host") if s else str(body.get("host") or "") or None
    return await vps_serv.sni_scan(host, body.get("candidates"))

# xray/wg/install file serving (token-authed)
@app.get("/xs/{token}/xray.json")
async def xs_xray(token: str):
    s = vps_serv.get_by_token(token)
    if not s:
        raise HTTPException(404)
    return PlainTextResponse(vps_serv.xray_json(s), media_type="application/json")

@app.get("/xs/{token}/wg.conf")
async def xs_wg(token: str):
    s = vps_serv.get_by_token(token)
    if not s:
        raise HTTPException(404)
    return PlainTextResponse(vps_serv.wg_conf(s) or "# wireguard disabled", media_type="text/plain")

@app.get("/xs/{token}/install.sh")
async def xs_install(token: str, request: Request):
    s = vps_serv.get_by_token(token)
    if not s:
        raise HTTPException(404)
    b = base_url() or f"https://{request.headers.get('host', '')}"
    return PlainTextResponse(vps_serv.install_script(s, b), media_type="text/x-shellscript")

# ---------------------------------------------------------------- subscription feeds
def _browser_request(request: Request, force: str | None) -> bool:
    if force == "raw":
        return False
    if force == "web":
        return True
    sfm = request.headers.get("sec-fetch-mode") or ""
    accept = request.headers.get("accept") or ""
    if sfm == "navigate":
        return True
    if "text/html" in accept and "Mozilla" in (request.headers.get("user-agent") or ""):
        return True
    return False

@app.get("/sub/{uid}")
async def sub_feed(request: Request, uid: str, web: str | None = None, raw: str | None = None):
    c = get_link(uid)
    if not c:
        raise HTTPException(404, "not found")
    if _browser_request(request, web or raw):
        return RedirectResponse(portal_url_for(uid), status_code=307)
    group_id = c.get("sub_id")
    if group_id and group_id in subs():
        members = [get_link(x) for x in subs()[group_id].get("link_ids", []) if get_link(x)]
    else:
        members = [c]
    lines = []
    info = build_info_server_remark(c)
    if info:
        lines.append(info)
    for m in members:
        lines.extend(config_lines_for(m))
    payload = base64.b64encode("\n".join([x for x in lines if x]).encode()).decode()
    return PlainTextResponse(payload, media_type="text/plain", headers=subscription_headers(c))

@app.get("/api/subscription/{uid}")
async def api_subscription(uid: str):
    c = get_link(uid)
    if not c:
        raise HTTPException(404)
    ips = list(core.CONNECTED_IPS.get(uid) or [])
    exp = core.expires_in_seconds(c)
    info = get_link_info(c)
    return {"ok": True, "name": c.get("label"), "protocol": c.get("protocol"),
            "active": is_link_allowed(c), "used_bytes": c.get("used_bytes") or 0,
            "limit_bytes": c.get("limit_bytes") or 0,
            "expires_at": c.get("expires_at"),
            "expires_in": exp, "online": info.get("online", 0),
            "ips": ips, "ip_limit": c.get("ip_limit") or 0,
            "ip_cur": len(ips),
            "usage_history": (c.get("usage_history") or [])[-24:]}

@app.get("/subscription/{uid}", response_class=HTMLResponse)
async def subscription_page(uid: str):
    c = get_link(uid)
    if not c:
        return HTMLResponse("<h3 style='font-family:sans-serif'>این اشتراک پیدا نشد.</h3>", status_code=404)
    b = base_url()
    info = get_link_info(c)
    host = ln._public_host() or (c.get("address") if c.get("protocol") == "manual" else None) or "—"
    port = c.get("port") or (core.VW_FORCE_PORT if core.VW_TLS else 443)
    data = {
        "uid": uid,
        "name": c.get("label") or "config",
        "protocol": str(c.get("protocol")),
        "active": is_link_allowed(c),
        "used": c.get("used_bytes") or 0,
        "limit": c.get("limit_bytes") or 0,
        "expires_at": c.get("expires_at"),
        "sub_url": sub_url_for(uid),
        "info_url": f"{b}/info/{uid}",
        "online": info.get("online", 0),
        "ip_cur": info.get("ips_online", 0),
        "ip_max": c.get("ip_limit") or 0,
        "speed_mbit": round((c.get("speed_limit_bytes") or 0) * 8 / 1_000_000, 1),
        "clients_count": info.get("clients_count", 0),
        "config_count": c.get("config_count") or 1,
        "usage_hist": c.get("usage_history") or [],
        "link_uri": ln.vless_link_for_link(c),
        "host": host, "port": port,
        "security": "TLS" if core.VW_TLS else "none",
        "sni": host if host != "—" else "—",
        "network": "ws" if (c.get("protocol") or "").endswith("ws") else ("xhttp" if (c.get("protocol") or "").startswith("xhttp") else "tcp"),
        "path": f"/ws/{uid}" if (c.get("protocol") or "").endswith("ws") else (f"/xhttp-siz10/{(c.get('protocol') or '').replace('xhttp-','')}/{uid}" if (c.get("protocol") or "").startswith("xhttp") else "—"),
        "fingerprint": c.get("fingerprint") or "chrome",
        "alpn": {"http1": "http/1.1", "h2h1": "h2, http/1.1", "h2": "h2"}.get(c.get("alpn") or "http1", "http/1.1"),
        "operator": c.get("operator") or "",
        "note": c.get("note") or "",
        "created_at": (c.get("created_at") or "")[:10],
    }
    return HTMLResponse(ui_portal.subscription(data, core.support_url()))

@app.get("/sub-all")
async def sub_all(_=Depends(require_auth)):
    out = []
    for c in links().values():
        if is_link_allowed(c):
            out.extend(config_lines_for(c))
    return PlainTextResponse(base64.b64encode("\n".join(out).encode()).decode(), media_type="text/plain")

@app.get("/info/{uid}", response_class=HTMLResponse)
async def info_page(uid: str):
    c = get_link(uid)
    if not c:
        return HTMLResponse("<h3 style='font-family:sans-serif'>پیدا نشد.</h3>", status_code=404)
    b = base_url()
    return HTMLResponse(ui_portal.info(
        uid, c.get("label") or "config", str(c.get("protocol")), is_link_allowed(c),
        c.get("used_bytes") or 0, c.get("limit_bytes") or 0, c.get("expires_at"),
        len(core.CONNECTED_IPS.get(uid) or []), c.get("ip_limit") or 0,
        int(core.TUNNELS_NOW.get(uid, 0) or 0), c.get("fingerprint"),
        core.support_url(), b))

# ---------------------------------------------------------------- group portals
def _group_items(sub: dict) -> list:
    items = []
    b = base_url()
    for lid in sub.get("link_ids", []):
        c = get_link(lid)
        if not c:
            continue
        items.append({"key": c["uuid"][:8], "label": c.get("label"), "protocol": c.get("protocol"),
                      "active": is_link_allowed(c), "operator": c.get("operator"),
                      "used_bytes": c.get("used_bytes") or 0, "limit_bytes": c.get("limit_bytes") or 0,
                      "link": vless_link_for_link(c), "sub": f"{b}/sub/{c['uuid']}"})
    return items

@app.get("/sub-group/{key}")
async def sub_group_page(request: Request, key: str, pw: str | None = None):
    sub = next((s for s in subs().values() if s.get("uuid_key") == key), None)
    if not sub:
        return HTMLResponse("<h3 style='font-family:sans-serif'>این گروه پیدا نشد.</h3>", status_code=404)
    has_pw = bool(sub.get("password_hash"))
    if has_pw:
        if not pw:
            return HTMLResponse(ui_portal.group(key, sub.get("name"), [], True, core.support_url()))
        if not hmac.compare_digest(ln.hash(pw), sub.get("password_hash") or ""):
            return JSONResponse({"ok": False, "error": "رمز اشتباه است"})
        return HTMLResponse(ui_portal.group(key, sub.get("name"), _group_items(sub), False, core.support_url()))
    return HTMLResponse(ui_portal.group(key, sub.get("name"), _group_items(sub), False, core.support_url()))

@app.get("/p/{key}", response_class=HTMLResponse)
async def p_alias(request: Request, key: str, pw: str | None = None):
    return await sub_group_page(request, key, pw)

@app.get("/api/public/sub/{key}")
async def api_public_sub(request: Request, key: str, pw: str | None = None):
    sub = next((s for s in subs().values() if s.get("uuid_key") == key), None)
    if not sub:
        raise HTTPException(404)
    if sub.get("password_hash"):
        if not pw or not hmac.compare_digest(ln.hash(pw), sub.get("password_hash")):
            return JSONResponse({"ok": False, "error": "locked"}, status_code=401)
    items = _group_items(sub)
    used = sum(i["used_bytes"] for i in items)
    total = sum(i["limit_bytes"] for i in items)
    exps = [parse_iso(get_link(i).get("expires_at")) for i in sub.get("link_ids", []) if get_link(i)]
    exps = [e for e in exps if e]
    exp = min(exps).isoformat() if exps else None
    return {"ok": True, "name": sub.get("name"), "items": items,
            "used_bytes": used, "limit_bytes": total, "expires_at": exp}

# ---------------------------------------------------------------- mini app (TMA)
@app.get("/app", response_class=HTMLResponse)
@app.get("/miniapp", response_class=HTMLResponse)
async def tma_page():
    return HTMLResponse(ui_portal.miniapp())

def _tma_valid(request: Request, init: str) -> dict | None:
    import sukot_bot
    tok = settings().get("bot_token") or sukot_bot.TOKEN
    if not tok or not init:
        return None
    try:
        pairs = sorted(p for p in init.split("&") if not p.startswith("hash="))
        check = "\n".join(pairs)
        secret = hmac.new(b"WebAppData", tok.encode(), hashlib.sha256).digest()
        h = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        got = ""
        for p in init.split("&"):
            if p.startswith("hash="):
                got = p[5:]
        if not hmac.compare_digest(h, got):
            return None
        auth_date = 0
        user = {}
        for p in pairs:
            k, _, v = p.partition("=")
            if k == "auth_date":
                auth_date = int(v)
            if k == "user":
                user = json.loads(v)
        if auth_date and time.time() - auth_date > 86400:
            return None
        ids = str(settings().get("bot_admin_ids") or "")
        if str(user.get("id")) not in [x.strip() for x in ids.split(",") if x.strip()]:
            return None
        return user
    except Exception:
        return None

@app.post("/api/tma/session")
async def tma_session(request: Request, body: dict = Body(default={})):
    user = _tma_valid(request, str((body or {}).get("init") or ""))
    if not user:
        raise HTTPException(401, "فقط ادمین‌های ربات")
    tok = create_session("tma:" + str(user.get("id")), "admin", core.DEFAULT_ADMIN_PERMS, extra={"tma": True})
    resp = JSONResponse({"ok": True, "username": user.get("first_name") or "ادمین"})
    resp.set_cookie(SESSION_COOKIE, tok, max_age=86400, httponly=True, samesite="lax", secure=is_https(request))
    return resp

@app.post("/api/tma/state")
async def tma_state(request: Request):
    adm = require_auth(request)
    st = links()
    b = base_url()
    items = []
    for c in sorted(st.values(), key=lambda x: x.get("created_at") or "", reverse=True)[:30]:
        if c.get("parent_inbound_id") and not ln.client_visible(c, adm):
            continue
        items.append({"uuid": c["uuid"], "label": c.get("label"), "active": c.get("active", True),
                      "used_h": human_bytes(c.get("used_bytes") or 0),
                      "limit_h": human_bytes(c.get("limit_bytes") or 0) or "∞",
                      "sub_url": f"{b}/sub/{c['uuid']}"})
    return {"ok": True, "total": len(st),
            "active": sum(1 for c in st.values() if is_link_allowed(c)),
            "traffic_h": human_bytes(sum(c.get("used_bytes") or 0 for c in st.values())),
            "items": items}

@app.post("/api/tma/create")
async def tma_create(request: Request, body: dict = Body(...)):
    adm = require_auth(request)
    if "client_create" not in adm.get("perm", set()) and "*" not in adm.get("perm", set()):
        raise HTTPException(403)
    c = make_link(label=random_config_names(count=1)[0], limit_bytes=gb_to_bytes(body.get("gb") or 0),
                  protocol="vless-ws", created_by="tma", admin_id=adm["admin_id"])
    if int(body.get("days") or 0):
        c["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=int(body["days"]))).isoformat()
        save_state()
    return {"ok": True, "uuid": c["uuid"]}

@app.post("/api/tma/edit")
async def tma_edit(request: Request, body: dict = Body(...)):
    adm = require_auth(request)
    c = get_link(str(body.get("uuid") or ""))
    if not c:
        raise HTTPException(404)
    if "client_edit" not in adm.get("perm", set()) and "*" not in adm.get("perm", set()):
        raise HTTPException(403)
    if body.get("active") is not None:
        c["active"] = bool(body["active"])
    save_state()
    return {"ok": True}

# ---------------------------------------------------------------- data plane
@app.websocket("/ws/{uid}")
async def ws_relay(ws: WebSocket, uid: str):
    await relays.websocket_tunnel(ws, uid)

relays.register_xhttp(app)

# ---------------------------------------------------------------- tg proxy + misc
from fastapi import Depends as _D
tg_api_registered = False
def register_extras():
    global tg_api_registered
    if not tg_api_registered:
        tg_proxy_mod.register(app, require_auth, core.DATA_DIR)
        tg_api_registered = True

import tg_proxy as tg_proxy_mod

@app.get("/test-ws")
async def test_ws():
    return {"ok": True, "hint": "WS relay at /ws/{uuid}"}

# ---------------------------------------------------------------- startup
@app.on_event("startup")
async def startup():
    load_state()
    # restore from Postgres BEFORE state file use
    try:
        import persist_db
        persist_db.restore_sync()
        persist_db.start_background()
        PERSIST["on"] = True
    except Exception as e:
        print("persist skip:", e)
    # usage-history sampler
    async def usage_loop():
        while True:
            await asyncio.sleep(300)
            try:
                for c in links().values():
                    h = c.setdefault("usage_history", [])
                    h.append(c.get("used_bytes") or 0)
                    if len(h) > 48:
                        del h[:-48]
                save_state()
            except Exception:
                pass
    asyncio.create_task(usage_loop())
    # node monitor
    async def node_loop():
        while True:
            await asyncio.sleep(30)
            try:
                await nodes_mod.check_all()
            except Exception:
                pass
    asyncio.create_task(node_loop())
    # session reaper
    asyncio.create_task(relays.reap_sessions())
    keepalive.start()
    try:
        tcp_relay_loop = asyncio.get_event_loop()
        tcp_relay_loop.create_task(tcp_relay.start_server())
    except Exception:
        pass
    import sukot_bot
    tok = settings().get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    ids = str(settings().get("bot_admin_ids") or os.environ.get("TELEGRAM_ADMIN_IDS", ""))
    if tok:
        sukot_bot.configure(tok, ids)
        try:
            BOT_OBJ["running"] = bool(await sukot_bot.start_bot())
        except Exception as e:
            print("bot start failed:", e)
    log_activity("پنل SUKOT بالا آمد", kind="act")
    print(f"SUKOT Panel v{APP_VERSION} ready on :{PORT}")

PERSIST = {"on": False}

@app.on_event("shutdown")
async def shutdown():
    save_state()
    try:
        import persist_db
        persist_db.push_once()
    except Exception:
        pass

register_extras()
