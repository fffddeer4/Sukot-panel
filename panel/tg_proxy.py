# tg_proxy.py — SUKOT Telegram Proxy Engine
# MTProto (obfuscated2 + "dd" padded secret) + Telegram-only SOCKS5, single-port mux.
# Wire format follows the MTProto proxy spec (interoperable with Telegram clients).
import asyncio, hashlib, hmac, ipaddress, json, os, secrets, struct, time, uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

TG_DC_V4 = {1: "149.154.175.50", 2: "149.154.167.51", 3: "149.154.175.100",
            4: "149.154.167.91", 5: "149.154.171.5"}
TG_NETS = [ipaddress.ip_network(n) for n in (
    "149.154.160.0/20", "91.108.4.0/22", "91.108.8.0/22", "91.108.12.0/22",
    "91.108.16.0/22", "91.108.20.0/22", "91.108.56.0/22", "95.161.64.0/20",
    "185.76.151.0/24", "109.239.140.0/24")]
GOOD_TAGS = (b"\xdd\xdd\xdd\xdd", b"\xee\xee\xee\xee", b"\xef\xef\xef\xef")
FORBIDDEN_START = (b"HEAD", b"POST", b"GET ", b"OPTI", b"\xdd\xdd\xdd\xdd",
                   b"\xee\xee\xee\xee", b"\x16\x03\x01\x02")
GB = 1024 ** 3
TG_DC_PORT = int(os.environ.get("TG_DC_PORT_OVERRIDE", "443") or 443)
if os.environ.get("TG_DC_HOST_OVERRIDE"):
    TG_DC_V4 = {k: os.environ["TG_DC_HOST_OVERRIDE"] for k in TG_DC_V4}

def _ctr(key: bytes, iv: bytes):
    return Cipher(algorithms.AES(key), modes.CTR(iv)).encryptor()

class TgProxyManager:
    def __init__(self, data_dir, logger=None):
        self.file = Path(data_dir) / "sukot_tg_proxies.json"
        self.log = logger
        self.settings = {
            "enabled": True,
            "mt_port": int(os.environ.get("TG_PROXY_PORT", "8443") or 8443),
            "socks_port": int(os.environ.get("TG_SOCKS_PORT", "0") or 0),
            "public_host": os.environ.get("TG_PUBLIC_HOST", ""),
            "socks_tg_only": True,
            "share_panel_port": True,
            "public_port": int(os.environ.get("TG_PUBLIC_PORT", "0") or 0),
            "default_created": False,
        }
        self.mux_active = False
        self.shared = False
        self.items: dict = {}
        self.live: dict = {}
        self.errors: dict = {}
        self._mt = None
        self._sk = None
        self._dirty = False
        self._task = None
        self._load()

    def _load(self):
        try:
            d = json.loads(self.file.read_text(encoding="utf-8"))
            self.settings.update(d.get("settings") or {})
            self.items = d.get("items") or {}
        except Exception:
            pass

    def save(self):
        try:
            tmp = self.file.with_suffix(".tmp")
            tmp.write_text(json.dumps({"settings": self.settings, "items": self.items},
                                      ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.file)
            self._dirty = False
        except Exception as e:
            print("tg_proxy save:", e)

    async def _flusher(self):
        while True:
            await asyncio.sleep(15)
            if self._dirty:
                self.save()

    async def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._flusher())
        self.ensure_default()
        await self.restart_servers()

    def ensure_default(self):
        if self.settings.get("default_created") or self.items:
            self.settings["default_created"] = True
            return
        px = self.create("mtproto", "پروکسی پیش‌فرض SUKOT", 0, 0, 0, "پیش‌فرض")
        px["default"] = True
        self.settings["default_created"] = True
        self.save()

    async def stop(self):
        if self._task:
            self._task.cancel(); self._task = None
        await self._close_servers()
        self.save()

    async def _close_servers(self):
        for name in ("_mt", "_sk"):
            srv = getattr(self, name)
            if srv:
                try: srv.close(); await srv.wait_closed()
                except Exception: pass
                setattr(self, name, None)
        self.shared = False

    async def restart_servers(self):
        await self._close_servers()
        loop = asyncio.get_event_loop()
        if self.settings.get("enabled") and not self.settings.get("share_panel_port"):
            port = int(self.settings.get("mt_port") or 8443)
            try:
                self._mt = await asyncio.start_server(self._handle_mt, "0.0.0.0", port)
                self.errors.pop("mt", None)
            except Exception as e:
                self._mt = None
                self.errors["mt"] = f"پورت {port} در دسترس نیست: {e}"
        if self.settings.get("enabled") and int(self.settings.get("socks_port") or 0):
            try:
                self._sk = await asyncio.start_server(self._handle_socks, "0.0.0.0",
                                                      int(self.settings["socks_port"]))
                self.errors.pop("socks", None)
            except Exception as e:
                self._sk = None
                self.errors["socks"] = f"پورت SOCKS در دسترس نیست: {e}"

    # ---------------- validity ----------------
    def _expired(self, px) -> bool:
        exp = px.get("expires_at")
        if not exp:
            return False
        try:
            return datetime.fromisoformat(exp) < datetime.now()
        except Exception:
            return False

    def usable(self, px) -> bool:
        if not px.get("enabled", True) or self._expired(px):
            return False
        lim = int(px.get("limit_bytes") or 0)
        return not (lim and int(px.get("used_bytes") or 0) >= lim)

    def _account(self, px, n):
        px["used_bytes"] = int(px.get("used_bytes") or 0) + n
        px["last_seen"] = datetime.now().isoformat(timespec="seconds")
        self._dirty = True

    def _slot(self, px) -> bool:
        mc = int(px.get("max_conn") or 0)
        if mc and self.live.get(px["id"], 0) >= mc:
            return False
        self.live[px["id"]] = self.live.get(px["id"], 0) + 1
        return True

    def _release(self, px):
        self.live[px["id"]] = max(0, self.live.get(px["id"], 1) - 1)

    @staticmethod
    async def _close(*ws):
        for w in ws:
            try:
                w.close(); await w.wait_closed()
            except Exception:
                pass

    # ---------------- MTProto ----------------
    def _match(self, init: bytes):
        for px in self.items.values():
            if px.get("kind") != "mtproto" or not self.usable(px):
                continue
            try:
                sec = bytes.fromhex(px["secret"])
            except Exception:
                continue
            dec_key = hashlib.sha256(init[8:40] + sec).digest()
            rev = init[8:56][::-1]
            enc_key = hashlib.sha256(rev[:32] + sec).digest()
            dec = _ctr(dec_key, init[40:56])
            plain = dec.update(init)
            if plain[56:60] in GOOD_TAGS:
                dc = struct.unpack("<h", plain[60:62])[0]
                if 1 <= abs(dc) <= 5:
                    return px, dec, _ctr(enc_key, rev[32:48]), plain[56:60], dc
        return None

    async def _handle_mt(self, reader, writer):
        up = None
        try:
            init = await asyncio.wait_for(reader.readexactly(64), 10)
            m = self._match(init)
            if not m:
                await asyncio.sleep(1.0)
                return
            px, dec, enc, tag, dc = m
            if not self._slot(px):
                return
            up = px
            ur, uw = await asyncio.wait_for(
                asyncio.open_connection(TG_DC_V4[abs(dc)], TG_DC_PORT), 10)
            while True:
                rnd = bytearray(os.urandom(64))
                if rnd[0] == 0xEF or bytes(rnd[:4]) in FORBIDDEN_START or rnd[4:8] == b"\0\0\0\0":
                    continue
                break
            rnd[56:60] = tag
            rnd[60:62] = struct.pack("<h", dc)
            rev = bytes(rnd[8:56])[::-1]
            dc_enc = _ctr(bytes(rnd[8:40]), bytes(rnd[40:56]))
            dc_dec = _ctr(rev[:32], rev[32:48])
            sealed = dc_enc.update(bytes(rnd))
            uw.write(bytes(rnd[:56]) + sealed[56:64])
            await uw.drain()

            async def c2d():
                while True:
                    data = await reader.read(16384)
                    if not data:
                        break
                    uw.write(dc_enc.update(dec.update(data)))
                    await uw.drain()
                    self._account(px, len(data))
                    if not self.usable(px):
                        break

            async def d2c():
                while True:
                    data = await ur.read(16384)
                    if not data:
                        break
                    writer.write(enc.update(dc_dec.update(data)))
                    await writer.drain()
                    self._account(px, len(data))
                    if not self.usable(px):
                        break

            t1, t2 = asyncio.ensure_future(c2d()), asyncio.ensure_future(d2c())
            await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
            for t in (t1, t2):
                t.cancel()
            await self._close(uw)
        except Exception:
            pass
        finally:
            if up:
                self._release(up)
            await self._close(writer)

    # ---------------- SOCKS5 (Telegram only) ----------------
    def _find_socks(self, user, pw):
        for px in self.items.values():
            if px.get("kind") == "socks" and self.usable(px) \
                    and hmac.compare_digest(px.get("user", ""), user) \
                    and hmac.compare_digest(px.get("password", ""), pw):
                return px
        return None

    def _tg_ok(self, host) -> bool:
        if not self.settings.get("socks_tg_only", True):
            return True
        try:
            ip = ipaddress.ip_address(host)
            return any(ip in n for n in TG_NETS)
        except ValueError:
            h = host.lower()
            return h.endswith((".telegram.org", ".t.me", ".telegra.ph")) or h in ("telegram.org", "t.me")

    async def _handle_socks(self, reader, writer):
        px = None
        try:
            v, n = await asyncio.wait_for(reader.readexactly(2), 10)
            if v != 5:
                return
            methods = await reader.readexactly(n)
            if 2 not in methods:
                writer.write(b"\x05\xff"); return
            writer.write(b"\x05\x02"); await writer.drain()
            if (await reader.readexactly(1)) != b"\x01":
                return
            ul = (await reader.readexactly(1))[0]
            user = (await reader.readexactly(ul)).decode("utf-8", "ignore")
            pl = (await reader.readexactly(1))[0]
            pw = (await reader.readexactly(pl)).decode("utf-8", "ignore")
            px = self._find_socks(user, pw)
            if not px or not self._slot(px):
                writer.write(b"\x01\x01"); px = None; return
            writer.write(b"\x01\x00")
            _, cmd, _, atyp = await reader.readexactly(4)
            if atyp == 1:
                host = str(ipaddress.ip_address(await reader.readexactly(4)))
            elif atyp == 4:
                host = str(ipaddress.ip_address(await reader.readexactly(16)))
            elif atyp == 3:
                ln = (await reader.readexactly(1))[0]
                host = (await reader.readexactly(ln)).decode("ascii", "ignore")
            else:
                return
            port = struct.unpack(">H", await reader.readexactly(2))[0]
            if cmd != 1 or not self._tg_ok(host):
                writer.write(b"\x05\x02\x00\x01\0\0\0\0\0\0"); return
            ur, uw = await asyncio.wait_for(asyncio.open_connection(host, port), 10)
            writer.write(b"\x05\x00\x00\x01\0\0\0\0\0\0"); await writer.drain()

            async def pipe(r, w):
                while True:
                    data = await r.read(16384)
                    if not data:
                        break
                    w.write(data); await w.drain()
                    self._account(px, len(data))
                    if not self.usable(px):
                        break

            t1, t2 = asyncio.ensure_future(pipe(reader, uw)), asyncio.ensure_future(pipe(ur, writer))
            await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
            for t in (t1, t2):
                t.cancel()
            await self._close(uw)
        except Exception:
            pass
        finally:
            if px:
                self._release(px)
            await self._close(writer)

    # ---------------- auto ----------------
    AUTO_PORTS = (443, 8443, 2053, 2083, 2087, 2096, 8080)

    async def _probe_dcs(self):
        async def probe(dc, ip):
            t0 = time.perf_counter()
            try:
                _r, w = await asyncio.wait_for(asyncio.open_connection(ip, TG_DC_PORT), 4)
                w.close()
                return {"dc": dc, "ok": True, "ms": round((time.perf_counter() - t0) * 1000)}
            except Exception as exc:
                return {"dc": dc, "ok": False, "err": type(exc).__name__}
        return await asyncio.gather(*[probe(k, v) for k, v in TG_DC_V4.items()])

    @staticmethod
    async def _can_bind(port) -> bool:
        try:
            srv = await asyncio.start_server(lambda r, w: None, "0.0.0.0", port)
            srv.close(); await srv.wait_closed()
            return True
        except Exception:
            return False

    async def auto_setup(self, req_port=0, https=True, fresh=False) -> dict:
        steps = []
        s = self.settings
        dcs = await self._probe_dcs()
        okd = [d for d in dcs if d["ok"]]
        avg = round(sum(d["ms"] for d in okd) / len(okd)) if okd else 0
        steps.append({"k": "dc", "ok": bool(okd),
                      "text": f"اتصال به دیتاسنترهای تلگرام: {len(okd)} از {len(dcs)}" +
                              (f" · میانگین {avg}ms" if okd else " — هاست خروجی تلگرام را بسته است"),
                      "dcs": dcs})
        s["enabled"] = True
        mode = "shared"
        if self.mux_active:
            s["share_panel_port"] = True
            if not req_port and not int(s.get("public_port") or 0):
                s["public_port"] = 443 if https else 80
            steps.append({"k": "port", "ok": True, "text": "تک‌پورتی روی پورت پنل فعال شد"})
        else:
            mode = "dedicated"
            s["share_panel_port"] = False
            cur = int(s.get("mt_port") or 0)
            port = 0
            if cur and self._mt is not None:
                port = cur
            else:
                for p in ([cur] if cur else []) + [x for x in self.AUTO_PORTS if x != cur]:
                    if await self._can_bind(p):
                        port = p
                        break
            if port:
                s["mt_port"] = port
                s["public_port"] = 0
            steps.append({"k": "port", "ok": bool(port),
                          "text": f"بهترین پورت آزاد انتخاب شد: {port}" if port else "هیچ پورت آزادی پیدا نشد"})
        await self.restart_servers()
        listening = bool(self._mt) or self.shared
        steps.append({"k": "listen", "ok": listening,
                      "text": "سرور MTProto در حال اجراست" if listening else "سرور MTProto بالا نیامد"})
        px = None
        if not fresh:
            for x in self.items.values():
                if x.get("kind") == "mtproto" and (x.get("auto") or x.get("default")) and self.usable(x):
                    px = x
                    break
        if px is None:
            px = self.create("mtproto", "Auto · " + datetime.now().strftime("%m-%d %H:%M"), 0, 0, 0, "ساخت خودکار")
            px["auto"] = True
            steps.append({"k": "secret", "ok": True, "text": "secret اختصاصی (dd · padded) ساخته شد"})
        else:
            steps.append({"k": "secret", "ok": True, "text": "از پروکسی خودکار قبلی استفاده شد"})
        self.save()
        return {"mode": mode, "steps": steps, "healthy": bool(okd) and listening, "px": px}

    # ---------------- CRUD ----------------
    def create(self, kind, label, limit_gb=0, days=0, max_conn=0, note=""):
        kind = "socks" if kind == "socks" else "mtproto"
        pid = uuid.uuid4().hex[:10]
        px = {
            "id": pid, "kind": kind, "label": (label or f"Proxy {len(self.items)+1}")[:60],
            "enabled": True, "created_at": datetime.now().isoformat(timespec="seconds"),
            "expires_at": (datetime.now() + timedelta(days=days)).isoformat(timespec="seconds") if days > 0 else None,
            "limit_bytes": int(limit_gb * GB) if limit_gb > 0 else 0,
            "used_bytes": 0, "max_conn": max(0, int(max_conn)), "note": (note or "")[:200],
        }
        if kind == "mtproto":
            px["secret"] = secrets.token_hex(16)
        else:
            px["user"] = "u" + secrets.token_hex(4)
            px["password"] = secrets.token_urlsafe(9)
        self.items[pid] = px
        self.save()
        return px

    def eff_port(self, req_port=0) -> int:
        pp = int(self.settings.get("public_port") or 0)
        if pp:
            return pp
        if self.shared and req_port:
            return req_port
        return int(self.settings.get("mt_port") or 0)

    def links(self, px, host, req_port=0) -> dict:
        host = self.settings.get("public_host") or host
        if px["kind"] == "mtproto":
            port = self.eff_port(req_port)
            sec = "dd" + px["secret"]
            q = f"server={quote(host)}&port={port}&secret={sec}"
            return {"tg": f"tg://proxy?{q}", "web": f"https://t.me/proxy?{q}",
                    "server": host, "port": port, "secret": sec}
        port = int(self.settings.get("socks_port") or 0)
        q = f"server={quote(host)}&port={port}&user={quote(px['user'])}&pass={quote(px['password'])}"
        return {"tg": f"tg://socks?{q}", "web": f"https://t.me/socks?{q}",
                "server": host, "port": port, "user": px["user"], "password": px["password"]}

    def public(self, px, host, req_port=0) -> dict:
        d = {k: v for k, v in px.items() if k not in ("secret", "password")}
        d["usable"] = self.usable(px)
        d["live"] = self.live.get(px["id"], 0)
        d["links"] = self.links(px, host, req_port)
        d["expired"] = self._expired(px)
        return d


# ============================================================
# Single-port mux: HTTP (panel/VLESS-WS) + MTProto on one port
# ============================================================
HTTP_PREFIXES = (b"GET ", b"POST", b"PUT ", b"HEAD", b"DELE", b"OPTI", b"PATC",
                 b"CONN", b"TRAC", b"PRI ")

class MuxProtocol(asyncio.Protocol):
    """Peeks first bytes: HTTP → uvicorn, else → MTProto."""

    def __init__(self, inner_factory, mgr):
        self._factory, self._mgr = inner_factory, mgr
        self._inner = self._reader = self._writer = self._fc = None
        self._mode = None
        self._buf = b""
        self._t = None
        self._timer = None

    def connection_made(self, transport):
        self._t = transport
        self._timer = asyncio.get_event_loop().call_later(20, self._timeout)

    def _timeout(self):
        if self._mode is None and self._t is not None:
            self._t.close()

    def data_received(self, data):
        if self._mode == "http":
            return self._inner.data_received(data)
        if self._mode == "mt":
            return self._reader.feed_data(data)
        self._buf += data
        if len(self._buf) < 4:
            return
        if self._timer:
            self._timer.cancel()
        if self._buf[:4] in HTTP_PREFIXES or not self._mgr.shared:
            self._to_http()
        else:
            self._to_mt()

    def _to_http(self):
        self._mode = "http"
        self._inner = self._factory()
        self._inner.connection_made(self._t)
        b, self._buf = self._buf, b""
        self._inner.data_received(b)

    def _to_mt(self):
        self._mode = "mt"
        loop = asyncio.get_event_loop()
        self._reader = asyncio.StreamReader(limit=2 ** 17, loop=loop)
        self._reader.set_transport(self._t)
        self._fc = asyncio.streams.FlowControlMixin(loop=loop)
        self._writer = asyncio.StreamWriter(self._t, self._fc, self._reader, loop)
        self._reader.feed_data(self._buf)
        self._buf = b""
        asyncio.ensure_future(self._mgr._handle_mt(self._reader, self._writer))

    def connection_lost(self, exc):
        if self._timer:
            self._timer.cancel()
        if self._mode == "http":
            self._inner.connection_lost(exc)
        elif self._mode == "mt":
            self._reader.feed_eof()
            self._fc.connection_lost(exc)

    def eof_received(self):
        if self._mode == "http":
            return self._inner.eof_received()
        if self._mode == "mt":
            self._reader.feed_eof()
            return True
        return False

    def pause_writing(self):
        if self._mode == "http":
            self._inner.pause_writing()
        elif self._mode:
            self._fc.pause_writing()

    def resume_writing(self):
        if self._mode == "http":
            self._inner.resume_writing()
        elif self._mode:
            self._fc.resume_writing()


def attach_mux(app, config):
    """Called from app.py — wraps uvicorn's HTTP protocol class with the mux."""
    mgr = getattr(app.state, "tg_proxy", None)
    if mgr is None:
        return False
    inner = config.http_protocol_class

    def factory(*a, **kw):
        return MuxProtocol(lambda: inner(*a, **kw), mgr)

    config.http_protocol_class = factory
    mgr.mux_active = True
    return True


# ============================================================
# FastAPI routes
# ============================================================
def register(app, require_auth, data_dir, logger=None):
    from fastapi import Depends, Request, Body
    mgr = TgProxyManager(data_dir, logger)
    app.state.tg_proxy = mgr

    def host_of(request: Request) -> str:
        h = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost"
        return h.split(",")[0].strip().rsplit(":", 1)[0] if not h.startswith("[") else h

    def port_of(request: Request) -> int:
        h = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
        if h and not h.startswith("[") and ":" in h:
            try:
                return int(h.rsplit(":", 1)[1])
            except ValueError:
                return 0
        return 0

    @app.on_event("startup")
    async def _tg_start():
        await mgr.start()

    @app.on_event("shutdown")
    async def _tg_stop():
        await mgr.stop()

    @app.get("/api/tgproxy")
    async def tg_list(request: Request, _=Depends(require_auth)):
        host = host_of(request)
        items = sorted(mgr.items.values(), key=lambda x: x.get("created_at", ""), reverse=True)
        return {"ok": True, "settings": mgr.settings, "errors": mgr.errors, "host": host,
                "running": {"mtproto": (mgr._mt is not None) or mgr.shared,
                            "socks": mgr._sk is not None, "shared": mgr.shared},
                "stats": {"total": len(items), "active": sum(1 for x in items if mgr.usable(x)),
                          "live": sum(mgr.live.values()),
                          "used_bytes": sum(int(x.get("used_bytes") or 0) for x in items)},
                "items": [mgr.public(x, host, port_of(request)) for x in items]}

    @app.post("/api/tgproxy/auto")
    async def tg_auto(request: Request, body: dict = Body(default={}), _=Depends(require_auth)):
        res = await mgr.auto_setup(port_of(request), https=True,
                                   fresh=bool((body or {}).get("fresh")))
        res["px"] = mgr.public(res["px"], host_of(request), port_of(request)) if res.get("px") else None
        return {"ok": True, **res}

    @app.post("/api/tgproxy")
    async def tg_create(request: Request, body: dict = Body(...), _=Depends(require_auth)):
        px = mgr.create(str(body.get("kind") or "mtproto"), str(body.get("label") or ""),
                        float(body.get("limit_gb") or 0), int(body.get("days") or 0),
                        int(body.get("max_conn") or 0), str(body.get("note") or ""))
        return {"ok": True, "item": mgr.public(px, host_of(request), port_of(request))}

    @app.patch("/api/tgproxy/{pid}")
    async def tg_patch(pid: str, body: dict = Body(...), _=Depends(require_auth)):
        px = mgr.items.get(pid)
        if not px:
            return {"ok": False, "error": "پروکسی پیدا نشد"}
        for k in ("label", "note", "max_conn", "limit_bytes", "enabled"):
            if k in body and body[k] is not None:
                px[k] = body[k]
        mgr.save()
        return {"ok": True, "item": mgr.public(px, host_of(request), port_of(request))}

    @app.post("/api/tgproxy/{pid}/reset")
    async def tg_reset(pid: str, _=Depends(require_auth)):
        px = mgr.items.get(pid)
        if not px:
            return {"ok": False}
        px["used_bytes"] = 0
        mgr.save()
        return {"ok": True}

    @app.post("/api/tgproxy/{pid}/regenerate")
    async def tg_regenerate(pid: str, request: Request, _=Depends(require_auth)):
        px = mgr.items.get(pid)
        if not px:
            return {"ok": False}
        if px["kind"] == "mtproto":
            px["secret"] = secrets.token_hex(16)
        else:
            px["user"] = "u" + secrets.token_hex(4)
            px["password"] = secrets.token_urlsafe(9)
        px["used_bytes"] = 0
        mgr.save()
        return {"ok": True, "item": mgr.public(px, host_of(request), port_of(request))}

    @app.delete("/api/tgproxy/{pid}")
    async def tg_delete(pid: str, _=Depends(require_auth)):
        return {"ok": mgr.items.pop(pid, None) is not None}

    @app.post("/api/tgproxy-settings")
    async def tg_settings(body: dict = Body(...), _=Depends(require_auth)):
        for k in ("enabled", "mt_port", "socks_port", "public_host", "public_port",
                  "share_panel_port", "socks_tg_only"):
            if k in body:
                mgr.settings[k] = body[k]
        mgr.save()
        await mgr.restart_servers()
        return {"ok": True, "settings": mgr.settings, "running": {
            "mtproto": (mgr._mt is not None) or mgr.shared, "socks": mgr._sk is not None}}

    @app.get("/api/tgproxy-selftest")
    async def tg_selftest(request: Request, _=Depends(require_auth)):
        async def probe(dc, ip):
            t0 = time.perf_counter()
            try:
                r, w = await asyncio.wait_for(asyncio.open_connection(ip, TG_DC_PORT), 4)
                w.close()
                return {"dc": dc, "ok": True, "ms": round((time.perf_counter() - t0) * 1000)}
            except Exception as exc:
                return {"dc": dc, "ok": False, "err": type(exc).__name__}
        dcs = await asyncio.gather(*[probe(k, v) for k, v in TG_DC_V4.items()])
        rp = port_of(request)
        tips = []
        if not any(d["ok"] for d in dcs):
            tips.append("سرور به دیتاسنترهای تلگرام وصل نمی‌شود؛ روی چنین هاستی MTProto کار نمی‌کند.")
        if mgr.shared and not rp and not mgr.settings.get("public_port"):
            tips.append("آدرس پنل پورت ندارد (احتمالاً پشت HTTPS است). در تنظیمات «پورت عمومی» را دستی وارد کن.")
        if not mgr.shared and not mgr._mt:
            tips.append("پورت MTProto باز نشده است؛ خطای پورت را ببین.")
        if not mgr.mux_active and mgr.settings.get("share_panel_port"):
            tips.append("اشتراک پورت فقط با اجرای app.py فعال می‌شود (نه uvicorn مستقیم).")
        return {"ok": True, "dcs": dcs, "tips": tips,
                "mux": mgr.mux_active, "shared": mgr.shared, "mt": mgr._mt is not None}

    return mgr
