# nodes.py — SUKOT panel-to-panel nodes (multi-server federation, Marzban-style)
import json, os, secrets, time, asyncio, httpx

DATA_DIR = os.environ.get("DATA_DIR", "./data")
NODES_FILE = os.path.join(DATA_DIR, "sukot_nodes.json")
TOKEN_FILE = os.path.join(DATA_DIR, "sukot_node_token.json")

NODES: dict = {}
NODE_TOKEN = ""
STATUS: dict = {}

NODE_ALLOWED_PREFIXES = (
    "/api/links", "/api/categories", "/api/subs", "/api/protocols", "/api/telemetry",
    "/stats", "/api/subscription", "/api/node/info", "/api/vps", "/api/operators",
)

def load():
    global NODES, NODE_TOKEN
    if NODES or NODE_TOKEN:
        return
    try:
        if os.path.exists(NODES_FILE):
            NODES = json.load(open(NODES_FILE, encoding="utf-8")) or {}
    except Exception:
        NODES = {}
    try:
        if os.path.exists(TOKEN_FILE):
            NODE_TOKEN = json.load(open(TOKEN_FILE, encoding="utf-8")) or ""
    except Exception:
        NODE_TOKEN = ""
    if not NODE_TOKEN:
        NODE_TOKEN = "skn_" + secrets.token_urlsafe(32)
        save_token()

def save_nodes():
    try:
        tmp = NODES_FILE + ".tmp"
        json.dump(NODES, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tmp, NODES_FILE)
    except Exception as e:
        print("nodes save:", e)

def save_token():
    try:
        json.dump(NODE_TOKEN, open(TOKEN_FILE, "w"))
    except Exception:
        pass

def authorize_node(token: str) -> bool:
    load()
    return bool(token) and token == NODE_TOKEN

def node_token() -> str:
    load()
    return NODE_TOKEN

def list_nodes() -> list:
    load()
    out = []
    for nid, n in NODES.items():
        out.append({"id": nid, **{k: n.get(k) for k in ("name", "url", "enabled", "created_at")},
                    "status": STATUS.get(nid, {}).get("status", "unknown"),
                    "latency_ms": STATUS.get(nid, {}).get("latency_ms"),
                    "last_check": STATUS.get(nid, {}).get("last")})
    return out

def upsert_node(name: str, url: str, token: str, enabled: bool = True, nid: str | None = None) -> dict:
    load()
    nid = nid or secrets.token_hex(6)
    NODES[nid] = {"name": name, "url": (url or "").rstrip("/"), "token": token or "",
                  "enabled": bool(enabled), "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    save_nodes()
    return NODES[nid]

def remove_node(nid: str) -> bool:
    load()
    if nid in NODES:
        NODES.pop(nid, None); save_nodes(); return True
    return False

def call_node_json(node, method: str, path: str, *, headers=None, body=None, timeout=10):
    load()
    h = {"Authorization": f"Bearer {node.get('token') or ''}"}
    if headers:
        h.update(headers)
    with httpx.Client(timeout=timeout, verify=False) as cli:
        r = cli.request(method, node["url"].rstrip("/") + path, headers=h, json=body if method != "GET" else None)
        r.raise_for_status()
        return r.json() if "json" in (r.headers.get("content-type") or "") else {"text": r.text}

async def probe_node(node) -> dict:
    t0 = time.monotonic()
    try:
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, lambda: call_node_json(node, "GET", "/api/node/info", timeout=8))
        ms = int((time.monotonic() - t0) * 1000)
        STATUS[node["id"]] = {"status": "online", "latency_ms": ms, "last": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **(res if isinstance(res, dict) else {})}
        return STATUS[node["id"]]
    except Exception as e:
        STATUS[node["id"]] = {"status": "offline", "error": str(e)[:120],
                              "last": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        return STATUS[node["id"]]

async def check_all():
    load()
    for n in NODES.values():
        if n.get("enabled", True):
            await probe_node(n)
    return STATUS

def node_info_self() -> dict:
    import core, links as ln, platform as pf, psutil
    st = ln.links()
    return {
        "app": core.APP_NAME, "version": core.APP_VERSION, "ok": True,
        "uptime_s": int(time.time() - START_TS),
        "inbounds": len(st),
        "clients": sum(1 for l in st.values() if l.get("parent_inbound_id")),
        "connections": len(core.TUNNELS_NOW),
        "online_ips": len({ip for ips in core.CONNECTED_IPS.values() for ip in ips}),
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "platform": pf.system(),
    }

START_TS = time.time()

# ------------------------------------------------- forwarding (whitelisted paths)
def allowed_path(path: str) -> bool:
    return any(path.startswith(p) for p in NODE_ALLOWED_PREFIXES)
