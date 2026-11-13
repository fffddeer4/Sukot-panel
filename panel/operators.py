# operators.py — Iranian ISP presets (fragment / fingerprint / clean-IPs)
import json, os

DATA_DIR = os.environ.get("DATA_DIR", "./data")
FILE = os.path.join(DATA_DIR, "sukot_operators.json")

DEFAULTS = {
    "mci": {
        "name": "همراه اول", "fragment": "none", "fingerprint": "chrome",
        "alpn": "http1", "clean_ips": ["104.16.0.0/12 suggestions via panel scan"],
        "note": "پریست پیش‌فرض همراه اول",
    },
    "irancell": {
        "name": "ایرانسل", "fragment": "tlshello", "fingerprint": "chrome",
        "alpn": "http1", "clean_ips": [],
        "note": "فرگمنت روشن برای ایرانسل",
    },
    "tci": {
        "name": "مخابرات", "fragment": "tlshello", "fingerprint": "ios",
        "alpn": "h2,http/1.1", "clean_ips": [],
        "note": "پریست مخابرات",
    },
    "rightel": {
        "name": "رایتل", "fragment": "none", "fingerprint": "chrome",
        "alpn": "http1", "clean_ips": [],
        "note": "پریست رایتل",
    },
    "all": {
        "name": "همه اپراتورها", "fragment": "none", "fingerprint": "chrome",
        "alpn": "http1", "clean_ips": [], "note": "بدون پریست",
    },
}

def _load() -> dict:
    data = {}
    try:
        if os.path.exists(FILE):
            data = json.load(open(FILE, encoding="utf-8")) or {}
    except Exception:
        data = {}
    for k, v in DEFAULTS.items():
        if k not in data:
            data[k] = dict(v)
    return data

def _save(d):
    try:
        tmp = FILE + ".tmp"
        json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tmp, FILE)
    except Exception:
        pass

def get_operators() -> dict:
    return _load()

def get_operator(key: str):
    return _load().get(key)

def set_operator(key: str, patch: dict) -> dict | None:
    d = _load()
    if key not in DEFAULTS:
        return None
    d[key].update({k: v for k, v in (patch or {}).items() if k in DEFAULTS[key]})
    _save(d)
    return d[key]

def preset_for(key: str) -> dict:
    """Fragment/fingerprint/alpn values to apply at config creation."""
    op = get_operator(key or "all") or dict(DEFAULTS["all"])
    frag = (op.get("fragment") or "none").lower()
    return {"fragment": "" if frag == "none" else frag,
            "fingerprint": op.get("fingerprint") or "chrome",
            "alpn": op.get("alpn") or "http1"}
