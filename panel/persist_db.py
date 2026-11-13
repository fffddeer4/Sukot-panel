# persist_db.py — SUKOT Postgres mirror (PaaS disks are ephemeral)
# Every runtime JSON file in DATA_DIR is mirrored as a blob row; restored on boot.
import os, json, time, hashlib, threading, base64

DATABASE_URL_RAW = (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
                    or os.environ.get("POSTGRESQL_URL") or "").strip()
# only postgres DSNs are mirrorable; anything else (sqlite/file/etc.) is ignored
DATABASE_URL = DATABASE_URL_RAW if DATABASE_URL_RAW.lower().startswith(
    ("postgres://", "postgresql://")) else ""
PERSIST_INTERVAL = int(os.environ.get("PERSIST_INTERVAL", "15") or 15)
SSL_VERIFY = str(os.environ.get("PERSIST_SSL_VERIFY", "0")).lower() not in ("0", "false", "no")

api = None  # module-level handle: None when disabled/unavailable
_conn = None

def _connect():
    import pg8000.native as pg
    global _conn
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    from urllib.parse import urlparse, unquote
    u = urlparse(url)
    kw = {}
    if "sslmode=" not in url:
        kw["ssl_context"] = None if not SSL_VERIFY else True
    _conn = pg.Connection(user=unquote(u.username or ""), password=unquote(u.password or ""),
                          host=u.hostname or "localhost", port=u.port or 5432,
                          database=(u.path or "/postgres").lstrip("/"), **kw)
    _conn.run("CREATE TABLE IF NOT EXISTS sk_files (name TEXT PRIMARY KEY, data BYTEA NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now())")

def _q(sql, args=()):
    return _conn.run(sql, stream=False, args=args) if False else _conn.run(sql, args=args)

def start_background():
    """Called from main startup. Returns True when persistence is active."""
    global api
    if not DATABASE_URL:
        print("persist: no DATABASE_URL — state stays on local disk only")
        return False
    try:
        _connect()
        api = _Api()
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        print("persist: Postgres mirror ACTIVE")
        return True
    except Exception as e:
        print("persist: DATABASE NOT REACHABLE —", str(e)[:160])
        api = None
        return False

def restore_sync():
    """Download every mirrored file into DATA_DIR before modules read it."""
    if not DATABASE_URL:
        return False
    for attempt in range(5):
        try:
            _connect()
            rows = _conn.run("SELECT name, data FROM sk_files")
            for name, blob in rows:
                try:
                    path = os.path.join(DATA_DIR, os.path.basename(str(name)))
                    with open(path, "wb") as f:
                        f.write(bytes(blob))
                except Exception:
                    pass
            print(f"persist: restored {len(rows)} file(s) from database")
            return True
        except Exception as e:
            print(f"persist: restore attempt {attempt+1}/5 failed — {str(e)[:120]}")
            time.sleep(2)
    print("persist: DATABASE NOT REACHABLE — panel will run WITHOUT durable storage")
    return False

class _Api:
    @staticmethod
    def save_file(name: str, data: bytes):
        try:
            _conn.run("INSERT INTO sk_files (name, data, updated_at) VALUES (:n, :d, now()) "
                      "ON CONFLICT (name) DO UPDATE SET data = :d, updated_at = now()",
                      args={"n": os.path.basename(name), "d": data})
        except Exception:
            _reconnect_quiet()

    @staticmethod
    def load_file(name: str):
        try:
            rows = _conn.run("SELECT data FROM sk_files WHERE name = :n", args={"n": os.path.basename(name)})
            return bytes(rows[0][0]) if rows else None
        except Exception:
            _reconnect_quiet()
            return None

def _reconnect_quiet():
    try:
        _connect()
    except Exception:
        pass

_HASHES: dict = {}

def push_once():
    """Upload changed DATA_DIR files (skip big/temp files)."""
    if _conn is None:
        return
    for fn in os.listdir(DATA_DIR):
        if fn.endswith((".tmp", ".lock", ".swp", ".part")):
            continue
        path = os.path.join(DATA_DIR, fn)
        try:
            if not os.path.isfile(path) or os.path.getsize(path) > 8 * 1024 * 1024:
                continue
            data = open(path, "rb").read()
            h = hashlib.sha256(data).hexdigest()
            if _HASHES.get(fn) == h:
                continue
            _HASHES[fn] = h
            _Api.save_file(fn, data)
        except Exception:
            pass

def _loop():
    while True:
        time.sleep(PERSIST_INTERVAL)
        try:
            push_once()
        except Exception:
            _reconnect_quiet()
