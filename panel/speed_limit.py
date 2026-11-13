# speed_limit.py — per-UUID token-bucket throttling
import time, asyncio, threading

_BUCKETS: dict = {}
_LOCK = threading.Lock()
CAP = 4 * 1024 * 1024  # 4MB burst buffer

def reset_bucket(uuid: str):
    with _LOCK:
        _BUCKETS.pop(uuid, None)

def _bucket(uuid: str, rate: int):
    b = _BUCKETS.get(uuid)
    if b is None or b.get("rate") != rate:
        b = {"rate": rate, "tokens": float(CAP), "last": time.monotonic()}
        _BUCKETS[uuid] = b
    return b

async def throttle(uuid: str, n: int, rate: int):
    """rate = bytes/sec, 0 = unlimited."""
    if not rate or rate <= 0:
        return
    with _LOCK:
        b = _bucket(uuid, rate)
    while True:
        with _LOCK:
            now = time.monotonic()
            b["tokens"] = min(CAP, b["tokens"] + (now - b["last"]) * b["rate"])
            b["last"] = now
            if b["tokens"] >= n:
                b["tokens"] -= n
                return
            need = (n - b["tokens"]) / max(b["rate"], 1)
        await asyncio.sleep(min(max(need, 0.01), 1.0))
