# core.py — SUKOT Panel core: config, state, auth, helpers
# Fresh implementation for the SUKOT control panel (Shiprr-ready).
import os, io, json, time, secrets, hashlib, hmac, shutil, threading, asyncio, \
       unicodedata, re as _re
from collections import deque
from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------- branding
APP_NAME    = "SUKOT"
APP_VERSION = "3.0.0"
BRAND_TAG   = "SUKOT · CONTROL CENTER"

# ----------------------------------------------------------------- paths / env
PORT = int(os.environ.get("PORT") or os.environ.get("SERVER_PORT") or 8000)
DATA_DIR = os.environ.get("DATA_DIR") or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or "./data"
os.makedirs(DATA_DIR, exist_ok=True)

VW_TLS         = 1 if str(os.environ.get("SUKOT_TLS", os.environ.get("VW_TLS", "1"))).lower() not in ("0", "false", "no") else 0
VW_FORCE_PORT  = int(os.environ.get("SUKOT_FORCE_PORT", os.environ.get("VW_FORCE_PORT", "443")) or 443)
STATE_FILE     = os.path.join(DATA_DIR, "sukot_state.json")
SESSIONS_FILE  = os.path.join(DATA_DIR, "sukot_sessions.json")

RAW_SECRET = os.environ.get("SECRET_KEY") or ""
if not RAW_SECRET:
    key_file = os.path.join(DATA_DIR, "sukot_secret.key")
    if os.path.exists(key_file):
        RAW_SECRET = open(key_file).read().strip()
    else:
        RAW_SECRET = secrets.token_urlsafe(48)
        try:
            open(key_file, "w").write(RAW_SECRET)
        except Exception:
            pass
SECRET_KEY = RAW_SECRET

# install salt for password hashing (stronger than raw sha256(secret+pw))
SALT_FILE = os.path.join(DATA_DIR, "sukot_salt.key")
if os.path.exists(SALT_FILE):
    PW_SALT = open(SALT_FILE).read().strip()
else:
    PW_SALT = secrets.token_hex(16)
    try: open(SALT_FILE, "w").write(PW_SALT)
    except Exception: pass

def _norm_base(u: str) -> str:
    u = (u or "").strip().rstrip("/")
    if u and not u.startswith("http"):
        u = "https://" + u
    return u

PUBLIC_BASE_URL = _norm_base(os.environ.get("PUBLIC_BASE_URL")
                             or os.environ.get("RAILWAY_PUBLIC_DOMAIN") and ("https://" + os.environ["RAILWAY_PUBLIC_DOMAIN"])
                             or "")
TCP_PUBLIC_HOST = os.environ.get("TCP_PUBLIC_HOST", "")
TCP_PUBLIC_PORT = int(os.environ.get("TCP_PUBLIC_PORT", "0") or 0)
TCP_LISTEN_PORT = int(os.environ.get("TCP_LISTEN_PORT", "6543") or 6543)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Sukot").strip() or "Sukot"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Sukot").strip() or "Sukot"
# true when credentials came explicitly from environment (skip default migration)
ENV_USER_SET = bool(os.environ.get("ADMIN_USERNAME"))
ENV_PASS_SET = bool(os.environ.get("ADMIN_PASSWORD"))
_PREV_DEFAULT_USER = "admin"
_PREV_DEFAULT_PASS = "sukot-admin"

# ----------------------------------------------------------------- settings
DEFAULT_SETTINGS = {
    "public_base_url": PUBLIC_BASE_URL,
    "tcp_public_host": TCP_PUBLIC_HOST,
    "tcp_public_port": TCP_PUBLIC_PORT,
    "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "bot_admin_ids": os.environ.get("TELEGRAM_ADMIN_IDS", ""),
    "bot_auto_start": True,
    "support_username": "@SUKOT1344",
    "channel_username": "SUKOT1344",
    "sub_remark_name": True, "sub_remark_volume": True,
    "sub_remark_id": False, "sub_remark_inbound": False,
    "sub_info_line_name": True, "sub_info_line_volume": True,
    "sub_info_line_id": True, "sub_info_line_inbound": False,
    "name_style_enabled": True,
    "info_server_name": "SUKOT-Panel",
    "xs_profile": {},
    "vps_servers": {},
}

PERSISTED_EXTRA_SETTINGS = {"xs_profile", "vps_servers"}

def settings() -> dict:
    return STATE.setdefault("settings", dict(DEFAULT_SETTINGS))

def set_setting(k, v):
    settings()[k] = v
    save_state()

def public_url() -> str:
    u = _norm_base(settings().get("public_base_url") or PUBLIC_BASE_URL)
    return u

def support_url() -> str:
    su = (settings().get("support_username") or "@SUKOT1344").lstrip("@")
    return "https://t.me/" + su

def channel_url() -> str:
    cu = (settings().get("channel_username") or "SUKOT1344").lstrip("@")
    return "https://t.me/" + cu

# ----------------------------------------------------------------- state
STATE: dict = {}
STATE_LOCK = threading.RLock()
STATE_LOADED = False

def load_state():
    global STATE, STATE_LOADED
    with STATE_LOCK:
        if STATE_LOADED:
            return STATE
        st = {}
        try:
            if os.path.exists(STATE_FILE):
                st = json.load(open(STATE_FILE, encoding="utf-8"))
        except Exception:
            st = {}
        st.setdefault("links", {})
        st.setdefault("subs", {})
        st.setdefault("categories", {})
        st.setdefault("admins", {})
        st.setdefault("admin_requests", [])
        st.setdefault("daily_stats", {})
        st.setdefault("bot_texts", {})
        st.setdefault("sessions", {})
        st.setdefault("settings", {})
        merged = dict(DEFAULT_SETTINGS)
        merged.update(st.get("settings") or {})
        st["settings"] = merged
        st.setdefault("username", ADMIN_USERNAME)
        # ---- one-time migration: old default credentials (admin / sukot-admin) → Sukot / Sukot
        if not ENV_USER_SET and (st.get("username") or "").lower() == _PREV_DEFAULT_USER.lower():
            st["username"] = ADMIN_USERNAME
        if not ENV_PASS_SET and st.get("password_hash") == hash_password(_PREV_DEFAULT_PASS):
            st["password_hash"] = hash_password(ADMIN_PASSWORD)
        if not st.get("password_hash"):
            st["password_hash"] = hash_password(ADMIN_PASSWORD)
        # ---- migrate old Telegram ids to the official channel (@SUKOT1344)
        _m = merged
        if str(_m.get("support_username") or "").lower().lstrip("@") in ("sukot134", "sukot1344"):
            _m["support_username"] = "@SUKOT1344"
        if str(_m.get("channel_username") or "").lower().lstrip("@") in ("sukot134", "sukot1344"):
            _m["channel_username"] = "SUKOT1344"
        STATE = st
        STATE_LOADED = True
        # restore persisted sessions
        try:
            _sess = st.get("sessions") or {}
            now = time.time()
            for tok, rec in list(_sess.items()):
                if rec.get("exp", 0) > now:
                    SESSIONS[tok] = rec
        except Exception:
            pass
        return STATE

SAVE_TIMER = None
def save_state():
    """Debounced atomic save."""
    global SAVE_TIMER
    def _do():
        try:
            with STATE_LOCK:
                STATE["saved_at"] = now_iso()
                tmp = STATE_FILE + ".tmp"
                json.dump(STATE, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
                os.replace(tmp, STATE_FILE)
                # persist sessions snapshot
                try:
                    sess_tmp = SESSIONS_FILE + ".tmp"
                    json.dump(SESSIONS, open(sess_tmp, "w"), ensure_ascii=False)
                    os.replace(sess_tmp, SESSIONS_FILE)
                except Exception:
                    pass
        except Exception as e:
            print("save_state error:", e)
    try:
        SAVE_TIMER.cancel()
    except Exception:
        pass
    SAVE_TIMER = threading.Timer(0.6, _do)
    SAVE_TIMER.daemon = True
    SAVE_TIMER.start()

# ----------------------------------------------------------------- crypto / passwords
def hash_password(pw: str) -> str:
    return hashlib.sha256((PW_SALT + ":" + (pw or "")).encode()).hexdigest()

def verify_password(pw: str, h: str) -> bool:
    return hmac.compare_digest(hash_password(pw), h or "")

# ----------------------------------------------------------------- sessions
SESSION_COOKIE = "sukot_session"
SESSIONS: dict = {}
SESSION_TTL_DEFAULT = 7 * 86400
SESSION_TTL_REMEMBER = 365 * 86400

def create_session(admin_id: str, role: str, permissions, remember: bool = False,
                   extra: dict | None = None) -> str:
    tok = secrets.token_urlsafe(48)
    ttl = SESSION_TTL_REMEMBER if remember else SESSION_TTL_DEFAULT
    SESSIONS[tok] = {
        "admin_id": admin_id, "role": role,
        "permissions": list(permissions or []),
        "exp": time.time() + ttl, "created": now_iso(),
        **(extra or {}),
    }
    save_state()
    return tok

def get_session(tok: str) -> dict | None:
    rec = SESSIONS.get(tok)
    if not rec:
        return None
    if rec.get("exp", 0) < time.time():
        SESSIONS.pop(tok, None)
        return None
    return rec

def destroy_session(tok: str):
    SESSIONS.pop(tok, None)
    save_state()

def revoke_other_sessions(admin_id: str, keep_token: str | None = None) -> int:
    n = 0
    for tok in list(SESSIONS.keys()):
        if SESSIONS[tok].get("admin_id") == admin_id and tok != keep_token:
            SESSIONS.pop(tok, None); n += 1
    save_state()
    return n

# ----------------------------------------------------------------- admins / permissions
ALL_PERMISSIONS = [
    "dashboard", "inbound_create", "inbound_edit", "inbound_delete",
    "client_create", "client_edit", "client_delete", "client_reset",
    "subscription", "categories", "subgroups", "reports", "nodes",
    "outbound_manage", "live_connections", "activity", "messages", "vps", "tgproxy",
]
DEFAULT_ADMIN_PERMS = [
    "dashboard", "inbound_create", "inbound_edit", "inbound_delete",
    "client_create", "client_edit", "client_delete", "client_reset",
    "subscription", "categories", "subgroups", "reports", "activity", "messages",
]

def admins() -> dict:
    return STATE.setdefault("admins", {})

def admin_record(admin_id: str) -> dict | None:
    st = load_state()
    aid = (admin_id or "").strip().lower()
    if aid == (st.get("username") or ADMIN_USERNAME).lower() or aid in ("owner", ""):
        return {"admin_id": st.get("username") or ADMIN_USERNAME, "role": "owner",
                "permissions": ALL_PERMISSIONS, "allowed_inbounds": [], "active": True}
    a = admins().get(admin_id) or admins().get(aid)
    if not a:
        return None
    return {"admin_id": admin_id, **a}

def verify_admin_credentials(username: str, password: str) -> dict | None:
    st = load_state()
    uname = (username or "").strip().lower()
    # owner: empty username or matching username
    if uname in ("", (st.get("username") or ADMIN_USERNAME).lower(), "owner"):
        if verify_password(password, st.get("password_hash") or ""):
            return admin_record(st.get("username") or ADMIN_USERNAME)
    for aid, a in (admins().items() if isinstance(admins(), dict) else []):
        if uname == aid.lower() and a.get("active", True) and verify_password(password, a.get("password_hash", "")):
            return admin_record(aid)
    return None

# login brute-force guard
_LOGIN_FAILS: dict = {}
LOGIN_MAX_FAILS = 5
LOGIN_LOCK_SECONDS = 900

def login_lock_info(ip: str) -> int | None:
    rec = _LOGIN_FAILS.get(ip)
    if not rec:
        return None
    if rec["count"] >= LOGIN_MAX_FAILS and time.time() - rec["first"] < LOGIN_LOCK_SECONDS:
        return int(LOGIN_LOCK_SECONDS - (time.time() - rec["first"]))
    if rec["count"] >= LOGIN_MAX_FAILS:
        _LOGIN_FAILS.pop(ip, None)
    return None

def login_fail(ip: str):
    rec = _LOGIN_FAILS.setdefault(ip, {"count": 0, "first": time.time()})
    if time.time() - rec["first"] > LOGIN_LOCK_SECONDS:
        rec["count"], rec["first"] = 0, time.time()
    rec["count"] += 1

def login_ok(ip: str):
    _LOGIN_FAILS.pop(ip, None)

# ----------------------------------------------------------------- logs (rings)
ACTIVITY: deque = deque(maxlen=250)
ERRORS: deque = deque(maxlen=100)

def log_activity(text: str, actor: str = "system", kind: str = "info"):
    ACTIVITY.appendleft({"t": now_iso(), "text": text, "actor": actor, "kind": kind})

def log_error(text: str, source: str = "server"):
    ERRORS.appendleft({"t": now_iso(), "text": str(text)[:500], "source": source})

def client_error(text: str, page: str = ""):
    ERRORS.appendleft({"t": now_iso(), "text": str(text)[:500], "source": "client:" + (page or "?")})

# ----------------------------------------------------------------- daily stats
def _today() -> str:
    return datetime.now(timezone(timedelta(hours=3, minutes=30))).strftime("%Y-%m-%d")  # Asia/Tehran

def bump_daily(traffic_bytes: int = 0, new_links: int = 0, orders: int = 0, stars: int = 0):
    ds = load_state().setdefault("daily_stats", {})
    day = ds.setdefault(_today(), {"traffic_bytes": 0, "new_links": 0, "orders": 0, "stars": 0})
    day["traffic_bytes"] += traffic_bytes
    day["new_links"] += new_links
    day["orders"] += orders
    day["stars"] += stars
    # prune to 180 days
    if len(ds) > 185:
        for k in sorted(ds.keys())[: len(ds) - 180]:
            ds.pop(k, None)

# ----------------------------------------------------------------- utils
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def parse_iso(s):
    if not s:
        return None
    try:
        s = str(s).replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        try:
            return datetime.fromtimestamp(float(s), tz=timezone.utc)
        except Exception:
            return None

def expires_in_seconds(link) -> float | None:
    d = parse_iso(link.get("expires_at"))
    if not d:
        return None
    return (d - datetime.now(timezone.utc)).total_seconds()

def human_bytes(n) -> str:
    try:
        n = float(n or 0)
    except Exception:
        n = 0
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024 or unit == "PB":
            return (f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}")
        n /= 1024
    return "0 B"

def gb_to_bytes(gb) -> int:
    try:
        return int(float(gb or 0) * 1024 ** 3)
    except Exception:
        return 0

FA_ILLEGAL = _re.compile(r"[\\/:*?\"<>|]|\x00")
def sanitize_label(s: str, maxlen: int = 64) -> str:
    s = unicodedata.normalize("NFKC", str(s or "")).strip()
    s = FA_ILLEGAL.sub("-", s)
    return s[:maxlen] or "config"

def new_uuid() -> str:
    return str(secrets.token_hex(8) + secrets.token_hex(8)[:8])  # 24 hex — actually use uuid4 below

import uuid as _uuid
def new_uuid4() -> str:
    return str(_uuid.uuid4())

def rand_key(n: int = 12) -> str:
    return secrets.token_urlsafe(n)[:n]

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
def fa_num(x) -> str:
    return str(x).translate(PERSIAN_DIGITS)

NAME_WORDS_A = ["توفان", "شبح", "اوج", "تیتان", "نوا", "شهاب", "آذرخش", "سایه", "بلتز", "نکسوس",
                "ونوم", "رونین", "کایزر", "فانتوم", "ولت", "اکتان", "پالس", "اوربیت", "کواکب", "زایلون"]
NAME_WORDS_B = ["🚀", "⚡", "🔥", "🌙", "💎", "🌪", "🛡", "👑", "🎯", "✨"]

def random_config_names(base: str = "", count: int = 1) -> list:
    import random
    out = []
    for _ in range(max(1, min(count, 40))):
        w = random.choice(NAME_WORDS_A)
        n = random.randint(2, 99)
        e = random.choice(NAME_WORDS_B)
        prefix = APP_NAME if settings().get("name_style_enabled", True) else ""
        out.append(f"{prefix}|{w}{n}{e}" if prefix else f"{w}{n}{e}")
    return out

def build_config_remark(link) -> str:
    """Remark tail per settings toggles: name / volume / id / inbound."""
    s = settings()
    parts = []
    if s.get("sub_remark_name", True):
        parts.append(link.get("label") or "config")
    if s.get("sub_remark_volume", True):
        lim = link.get("limit_bytes") or 0
        parts.append("∞" if not lim else human_bytes(lim))
    if s.get("sub_remark_id", False):
        parts.append((link.get("uuid") or "")[:8])
    if s.get("sub_remark_inbound", False):
        parts.append(str(link.get("port") or VW_FORCE_PORT))
    return " | ".join(p for p in parts if p) or "config"

def build_info_server_remark(link) -> str:
    """Decorative info line shown inside VPN apps (used/remaining + time left)."""
    s = settings()
    if not (s.get("sub_info_line_name", True) or s.get("sub_info_line_volume", True)
            or s.get("sub_info_line_id", True) or s.get("sub_info_line_inbound", False)):
        return ""
    seg = []
    if s.get("sub_info_line_name", True):
        seg.append("🌐 " + str(s.get("info_server_name") or APP_NAME + "-Panel"))
    if s.get("sub_info_line_volume", True):
        lim, used = link.get("limit_bytes") or 0, link.get("used_bytes") or 0
        if lim:
            seg.append(f"{human_bytes(used)} / {human_bytes(lim)}")
        else:
            seg.append(human_bytes(used) + " / ∞")
    if s.get("sub_info_line_id", True):
        seg.append("🆔 " + (link.get("uuid") or "")[:8])
    if s.get("sub_info_line_inbound", False):
        seg.append("📡 " + str(link.get("label") or ""))
    return " | ".join(seg)

# ----------------------------------------------------------------- ip-limit tracking
CONNECTED_IPS: dict = {}   # uuid -> set of client IPs (currently connected)
_IP_LOCK = asyncio.Lock()
TUNNELS_NOW: dict = {}     # uuid -> active tunnel count (for live display)

def tunnel_open(uuid: str):
    TUNNELS_NOW[uuid] = TUNNELS_NOW.get(uuid, 0) + 1

def tunnel_close(uuid: str):
    n = TUNNELS_NOW.get(uuid, 0) - 1
    if n <= 0:
        TUNNELS_NOW.pop(uuid, None)
    else:
        TUNNELS_NOW[uuid] = n

def split_xff(value: str) -> str:
    if not value:
        return ""
    return value.split(",")[0].strip()

def client_ip_from_headers(headers, peer=None) -> str:
    ip = split_xff(headers.get("x-forwarded-for") or "") or headers.get("x-real-ip") or ""
    if not ip and peer:
        ip = peer[0] if isinstance(peer, (tuple, list)) else str(peer)
    return (ip or "").split("%")[0]

async def is_ip_allowed(uuid: str, ip: str, ip_limit: int) -> tuple[bool, object]:
    """Concurrent-unique-IP cap; returns (allowed, handle_for_release)."""
    if not ip_limit or not ip:
        return True, None
    async with _IP_LOCK:
        cur = CONNECTED_IPS.setdefault(uuid, set())
        if ip in cur:
            return True, ip
        if len(cur) >= ip_limit:
            return False, None
        cur.add(ip)
        return True, ip

async def release_ip(uuid: str, handle):
    if not handle:
        return
    async with _IP_LOCK:
        cur = CONNECTED_IPS.get(uuid)
        if cur:
            cur.discard(handle)
            if not cur:
                CONNECTED_IPS.pop(uuid, None)
