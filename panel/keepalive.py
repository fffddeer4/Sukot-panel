# keepalive.py — self-ping loop so PaaS free tiers don't sleep
import os, asyncio, httpx

ENABLED = str(os.environ.get("KEEPALIVE_ENABLED", "1")).lower() not in ("0", "false", "no")
INTERVAL = max(60, int(os.environ.get("KEEPALIVE_INTERVAL", "240") or 240))
URL = os.environ.get("KEEPALIVE_URL", "")
_task = None

async def _loop():
    import core
    bases = []
    if URL:
        bases.append(URL.rstrip("/"))
    pub = core.public_url()
    if pub:
        bases.append(pub.rstrip("/"))
    bases.append(f"http://127.0.0.1:{core.PORT}")
    async with httpx.AsyncClient(timeout=10) as cli:
        while True:
            for b in dict.fromkeys(bases):
                try:
                    await cli.get(b + "/ping")
                except Exception:
                    pass
            await asyncio.sleep(INTERVAL)

def start():
    global _task
    if not ENABLED:
        return
    try:
        loop = asyncio.get_running_loop()
        _task = loop.create_task(_loop())
    except Exception:
        pass
