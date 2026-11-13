# app.py — SUKOT launcher (Shiprr / Railway / any host)
# Loads main as a real module (healthy import cycle) and mounts the Telegram
# MTProto mux onto the same port for single-port hosts.
import os

from main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT") or os.environ.get("SERVER_PORT") or 8000)
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    config.load()
    try:
        import tg_proxy
        if tg_proxy.attach_mux(app, config):
            print("tg-proxy: single-port mux enabled")
    except Exception as exc:
        print("tg-proxy mux skipped:", exc)
    print(f"sukot launcher → starting on 0.0.0.0:{port}")
    uvicorn.Server(config).run()
