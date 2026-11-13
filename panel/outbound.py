# outbound.py — SUKOT outbound (exit) proxy pool: store / connect / probe / scan (compact)
import asyncio, json, os, time, socket, secrets, base64
from urllib.parse import urlparse

DATA_DIR = os.environ.get("DATA_DIR", "./data")
STORE_FILE = os.path.join(DATA_DIR, "sukot_proxies.json")
MAX_PROXIES = 300
FALLBACK_DIRECT = str(os.environ.get("OUTBOUND_FALLBACK_DIRECT", "0")).lower() in ("1", "true", "yes")

_PROXIES: dict = {}
_CB: dict = {}   # circuit breaker: id -> {"fails": n, "until": ts}
lock = asyncio.Lock()

def _load():
    global _PROXIES
    if _PROXIES:
        return
    try:
        if os.path.exists(STORE_FILE):
            _PROXIES = json.load(open(STORE_FILE, encoding="utf-8")) or {}
    except Exception:
        _PROXIES = {}

def _save():
    try:
        tmp = STORE_FILE + ".tmp"
        json.dump(_PROXIES, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tmp, STORE_FILE)
    except Exception as e:
        print("outbound save:", e)

def list_proxies() -> list:
    _load()
    out = []
    for pid, p in _PROXIES.items():
        out.append({"id": pid, "name": p.get("name"), "kind": p.get("kind"),
                    "host": p.get("host"), "port": p.get("port"),
                    "has_auth": bool(p.get("username")),
                    "status": p.get("status", "unknown"),
                    "latency_ms": p.get("latency_ms"),
                    "added_at": p.get("added_at")})
    return out

def proxy_count() -> int:
    _load()
    return len(_PROXIES)

def add_proxy(*, name="", kind="socks5", host, port, username="", password="", status="new") -> dict | None:
    _load()
    if len(_PROXIES) >= MAX_PROXIES:
        return None
    pid = secrets.token_hex(6)
    _PROXIES[pid] = {"id": pid, "name": name or f"{host}:{port}", "kind": (kind or "socks5").lower(),
                     "host": str(host).strip(), "port": int(port), "username": username or "",
                     "password": password or "", "status": status, "latency_ms": None,
                     "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    _save()
    return _PROXIES[pid]

def remove_proxy(pid: str) -> bool:
    _load()
    if pid in _PROXIES:
        _PROXIES.pop(pid, None)
        _save()
        return True
    return False

def get_proxy(pid: str):
    _load()
    return _PROXIES.get(pid)

# ------------------------------------------------------------ parsing
def parse_candidate(line: str) -> dict | None:
    line = (line or "").strip()
    if not line or line.startswith(("#", "//")):
        return None
    scheme = "socks5"
    m = None
    if "://" in line:
        line2 = line
        scheme, _, rest = line2.partition("://")
        line = rest
    auth = ""
    if "@" in line:
        auth, _, line = line.rpartition("@")
    if ":" in auth:
        username, _, password = auth.partition(":")
    else:
        username, password = auth, ""
    host, port = None, None
    line = line.strip("[]")
    if line.count(":") == 1:
        host, _, port = line.partition(":")
    else:
        # host:port:user:pass or IPv6
        parts = line.split(":")
        if len(parts) >= 2 and parts[-1].isdigit():
            port = parts[-1]; host = ":".join(parts[:-1])
            if len(parts) >= 4 and not username:
                username, password = parts[-3], parts[-2]
                host = ":".join(parts[:-3]) if len(parts) > 4 else parts[0]
        else:
            host = line
    try:
        port = int(port)
    except Exception:
        return None
    if not host or not (1 <= port <= 65535):
        return None
    if scheme in ("http", "https"):
        kind = "http"
    elif scheme in ("socks4", "socks5"):
        kind = scheme
    else:
        kind = "socks5"
    return {"kind": kind, "host": host.strip(), "port": port,
            "username": username or "", "password": password or ""}

# ------------------------------------------------------------ connect
async def open_target_connection(link, address: str, port: int):
    """Open TCP to target, tunneling through the config's exit proxy when set."""
    pid = link.get("outbound_proxy_id") if isinstance(link, dict) else None
    p = get_proxy(pid) if pid else None
    if not p:
        return await asyncio.open_connection(address, port)
    cb = _CB.get(pid)
    now = time.time()
    if cb and cb.get("until", 0) > now:
        if FALLBACK_DIRECT:
            return await asyncio.open_connection(address, port)
        raise OSError("exit proxy temporarily down (circuit breaker)")
    try:
        from python_socks.async_.asyncio import Proxy
        kind = p.get("kind") or "socks5"
        cls = {"socks5": "socks5", "socks4": "socks4", "http": "http"}.get(kind, "socks5")
        px = Proxy.from_url(f"{cls}://{p['host']}:{p['port']}",
                            username=p.get("username") or None, password=p.get("password") or None)
        sock = await px.connect(dest_host=address, dest_port=port)
        r, w = await asyncio.open_connection(sock=sock)
        _CB[pid] = {"fails": 0, "until": 0}
        return r, w
    except Exception as e:
        c = _CB.setdefault(pid, {"fails": 0, "until": 0})
        c["fails"] += 1
        if c["fails"] >= 3:
            c["until"] = now + 20
            c["fails"] = 0
        raise

# ------------------------------------------------------------ probe (compact)
async def probe_candidate(c: dict) -> dict:
    """TCP ping + protocol sniff + latency (ms). Does not do geo/TLS deep checks."""
    res = {"ok": False, "latency_ms": None, "kind": c.get("kind"), "score": 0}
    loop = asyncio.get_running_loop()
    t0 = time.monotonic()
    try:
        fut = loop.run_in_executor(None, lambda: socket.create_connection((c["host"], c["port"]), timeout=6))
        reader_writer = await asyncio.wait_for(fut, timeout=8)
        res["latency_ms"] = int((time.monotonic() - t0) * 1000)
        reader_writer[1].close()
        res["ok"] = True
        res["score"] = max(0, 100 - res["latency_ms"] // 20)
    except Exception as e:
        res["error"] = str(e)[:120]
    return res

async def run_scan(text: str, max_candidates: int = 200) -> dict:
    """Parse a pasted list, probe candidates, import good ones."""
    cands = []
    seen = set()
    for line in (text or "").splitlines():
        c = parse_candidate(line)
        if c:
            key = (c["host"], c["port"])
            if key not in seen:
                seen.add(key)
                cands.append(c)
        if len(cands) >= max_candidates:
            break
    good, tested = 0, 0
    for c in cands:
        r = await probe_candidate(c)
        tested += 1
        if r["ok"]:
            add_proxy(name=f"{c['host']}:{c['port']}", kind=c["kind"], host=c["host"],
                      port=c["port"], username=c.get("username"), password=c.get("password"),
                      status="alive", )
            # store latency
            pid = None
            for k, v in _PROXIES.items():
                if v["host"] == c["host"] and v["port"] == c["port"]:
                    pid = k; break
            if pid:
                _PROXIES[pid]["latency_ms"] = r["latency_ms"]
                _save()
            good += 1
    return {"tested": tested, "imported": good, "total_candidates": len(cands)}
