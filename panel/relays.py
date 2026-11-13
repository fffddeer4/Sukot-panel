# relays.py — SUKOT data plane: VLESS over WebSocket (/ws/{uuid}) + XHTTP routes
# Fresh implementation of the Xray VLESS wire protocol for single-port PaaS deployment.
import asyncio, struct, time, contextlib
from starlette.websockets import WebSocket, WebSocketDisconnect
from fastapi import Request
from fastapi.responses import StreamingResponse

import speed_limit
from core import is_ip_allowed, release_ip, client_ip_from_headers, log_error, tunnel_open, tunnel_close
from links import is_link_allowed, check_and_use, get_link
from outbound import open_target_connection

WS_FIRST_MSG_TIMEOUT = 15
CHUNK = 65536

# ---------------------------------------------------------------- VLESS header
def parse_vless_header(data: bytes):
    """Returns (ok, version, cmd, port, addrtype, addr, rest) — Xray VLESS v0."""
    try:
        if len(data) < 24:
            return False, None, None, None, None, None, None
        version = data[0]
        uid = data[1:17]
        addon_len = data[17]
        pos = 18 + addon_len
        if len(data) < pos + 4:
            return False, None, None, None, None, None, None
        cmd = data[pos]
        port = struct.unpack(">H", data[pos + 1:pos + 3])[0]
        atyp = data[pos + 3]
        pos += 4
        if atyp == 1:  # IPv4
            if len(data) < pos + 4: return False, None, None, None, None, None, None
            addr = ".".join(str(b) for b in data[pos:pos + 4]); pos += 4
        elif atyp == 2:  # domain
            ln = data[pos]
            if len(data) < pos + 1 + ln: return False, None, None, None, None, None, None
            addr = data[pos + 1:pos + 1 + ln].decode("idna", "ignore"); pos += 1 + ln
        elif atyp == 3:  # IPv6
            if len(data) < pos + 16: return False, None, None, None, None, None, None
            raw = data[pos:pos + 16]; pos += 16
            groups = []
            for i in range(0, 16, 2):
                groups.append(format((raw[i] << 8) | raw[i + 1], "x"))
            addr = ":".join(groups)
        else:
            return False, None, None, None, None, None, None
        return True, version, cmd, port, atyp, addr, data[pos:]
    except Exception:
        return False, None, None, None, None, None, None

# ---------------------------------------------------------------- WS tunnel
async def _pump_ws_to_tcp(ws: WebSocket, writer, uid: str, link):
    rate = link.get("speed_limit_bytes") or 0
    while True:
        msg = await ws.receive_bytes()
        await speed_limit.throttle(uid, len(msg), rate)
        if not check_and_use(uid, len(msg)):
            with contextlib.suppress(Exception):
                await ws.close(code=1008)
            return
        writer.write(msg)
        with contextlib.suppress(Exception):
            await writer.drain()

async def _pump_tcp_to_ws(ws: WebSocket, reader, uid: str, link):
    rate = link.get("speed_limit_bytes") or 0
    # Xray WS convention: first downstream chunk carries a 2-byte length prefix
    first = await reader.read(CHUNK)
    if not first:
        return
    payload = b"\x00\x00" + first
    if not check_and_use(uid, len(payload)):
        with contextlib.suppress(Exception):
            await ws.close(code=1008)
        return
    await speed_limit.throttle(uid, len(payload), rate)
    await ws.send_bytes(payload)
    while True:
        data = await reader.read(CHUNK)
        if not data:
            return
        await speed_limit.throttle(uid, len(data), rate)
        if not check_and_use(uid, len(data)):
            with contextlib.suppress(Exception):
                await ws.close(code=1008)
            return
        await ws.send_bytes(data)

async def websocket_tunnel(ws: WebSocket, uid: str):
    await ws.accept()
    link = get_link(uid)
    if not is_link_allowed(link):
        await ws.close(code=1008)
        return
    ip = client_ip_from_headers(ws.headers, ws.client)
    ok, handle = await is_ip_allowed(uid, ip, link.get("ip_limit") or 0)
    if not ok:
        await ws.close(code=1008)
        return
    writer = None
    tunnel_open(uid)
    try:
        try:
            first = await asyncio.wait_for(ws.receive_bytes(), timeout=WS_FIRST_MSG_TIMEOUT)
        except asyncio.TimeoutError:
            await ws.close(code=1008)
            return
        okhdr, _v, cmd, port, atyp, addr, rest = parse_vless_header(first)
        if not okhdr or cmd not in (1, 2):
            await ws.close(code=1008)
            return
        reader, writer = await open_target_connection(link, addr, port)
        if rest:
            writer.write(rest)
            with contextlib.suppress(Exception):
                await writer.drain()
        t1 = asyncio.create_task(_pump_ws_to_tcp(ws, writer, uid, link))
        t2 = asyncio.create_task(_pump_tcp_to_ws(ws, reader, uid, link))
        done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
            with contextlib.suppress(Exception):
                await t
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log_error(f"ws relay {uid[:8]}: {e}", source="relay")
    finally:
        tunnel_close(uid)
        await release_ip(uid, handle)
        if writer:
            with contextlib.suppress(Exception):
                writer.close()

# ---------------------------------------------------------------- XHTTP
class XhttpSession:
    __slots__ = ("uid", "reader", "writer", "queue", "alive", "last", "opened",
                 "exp_seq", "buf", "closed")
    def __init__(self, uid):
        self.uid = uid
        self.reader = None
        self.writer = None
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=1024)
        self.alive = True
        self.last = time.time()
        self.opened = False      # tunnel established
        self.closed = False      # header seen (first uplink chunk)
        self.exp_seq = 0         # packet-up ordering
        self.buf = {}            # seq -> payload (out-of-order cache)

SESSIONS: dict[str, XhttpSession] = {}
SESS_LOCK = asyncio.Lock()
SESS_IDLE = 30

async def reap_sessions():
    while True:
        await asyncio.sleep(10)
        now = time.time()
        async with SESS_LOCK:
            for sid, s in list(SESSIONS.items()):
                if now - s.last > SESS_IDLE:
                    if s.writer:
                        with contextlib.suppress(Exception):
                            s.writer.close()
                    SESSIONS.pop(sid, None)

async def _get_session(sid: str, uid: str) -> XhttpSession | None:
    async with SESS_LOCK:
        s = SESSIONS.get(sid)
        if not s:
            link = get_link(uid)
            if not is_link_allowed(link):
                return None
            s = XhttpSession(uid)
            SESSIONS[sid] = s
        s.last = time.time()
        return s

async def _read_down(link, s: XhttpSession, uid: str):
    """Tunnel → GET response."""
    try:
        while True:
            data = await s.reader.read(CHUNK)
            if not data:
                with contextlib.suppress(Exception):
                    await s.queue.put(None)
                return
            await speed_limit.throttle(uid, len(data), link.get("speed_limit_bytes") or 0)
            if not check_and_use(uid, len(data)):
                with contextlib.suppress(Exception):
                    await s.queue.put(None)
                return
            with contextlib.suppress(Exception):
                await s.queue.put(("down", data))
    except Exception:
        with contextlib.suppress(Exception):
            await s.queue.put(None)

async def xhttp_downlink(request: Request, mode: str, uid: str, session_id: str):
    """GET /xhttp-siz10/{mode}/{uid}/{session_id} — streaming downlink."""
    link = get_link(uid)
    if not is_link_allowed(link):
        return StreamingResponse(iter([b"forbidden"]), status_code=403, media_type="text/plain")
    s = await _get_session(session_id, uid)
    if not s:
        return StreamingResponse(iter([b"forbidden"]), status_code=403, media_type="text/plain")

    async def gen():
        try:
            while True:
                item = await s.queue.get()
                if item is None:
                    break
                kind, payload = item
                if kind == "header":
                    ok, _v, cmd, port, atyp, addr, rest = parse_vless_header(payload)
                    if not ok or cmd not in (1, 2):
                        break
                    reader, writer = await open_target_connection(link, addr, port)
                    s.reader, s.writer, s.opened = reader, writer, True
                    if rest:
                        if not check_and_use(uid, len(rest)):
                            break
                        writer.write(rest)
                        with contextlib.suppress(Exception):
                            await writer.drain()
                    asyncio.create_task(_read_down(link, s, uid))
                    continue
                if kind == "up":
                    if s.writer:
                        s.writer.write(payload)
                        with contextlib.suppress(Exception):
                            await s.writer.drain()
                    continue
                if kind == "down":
                    yield payload
        finally:
            s.alive = False

    headers = {"server": "cloudflare", "content-type": "application/grpc",
               "cache-control": "no-store", "x-accel-buffering": "no"}
    return StreamingResponse(gen(), headers=headers, media_type="application/grpc")

async def xhttp_uplink(request: Request, mode: str, uid: str, session_id: str, seq: str = ""):
    """POST /xhttp-siz10/packet-up/{uid}/{sid}/{seq}  or  stream-up/{uid}/{sid}."""
    link = get_link(uid)
    if not is_link_allowed(link):
        return StreamingResponse(iter([b"forbidden"]), status_code=403, media_type="text/plain")
    s = await _get_session(session_id, uid)
    if not s:
        return StreamingResponse(iter([b"forbidden"]), status_code=403, media_type="text/plain")
    ip = client_ip_from_headers(request.headers, request.client)
    ok, handle = await is_ip_allowed(uid, ip, link.get("ip_limit") or 0)
    if not ok:
        return StreamingResponse(iter([b"too many ips"]), status_code=429, media_type="text/plain")
    try:
        seq_n: int | None = None
        if mode == "packet-up" and str(seq).lstrip("-").isdigit():
            seq_n = int(seq)
        async for chunk in request.stream():
            if not chunk:
                continue
            await speed_limit.throttle(uid, len(chunk), link.get("speed_limit_bytes") or 0)
            if not check_and_use(uid, len(chunk)):
                s.closed = True
                break
            if seq_n is not None:
                # reorder buffer for packet-up
                if seq_n == s.exp_seq:
                    s.exp_seq += 1
                    with contextlib.suppress(Exception):
                        await s.queue.put(("header" if not s.closed else "up", chunk))
                    while s.exp_seq in s.buf:
                        nxt = s.buf.pop(s.exp_seq)
                        s.exp_seq += 1
                        with contextlib.suppress(Exception):
                            await s.queue.put(("up", nxt))
                elif seq_n > s.exp_seq:
                    s.buf[seq_n] = chunk
                # seq < exp_seq → duplicate, drop
            else:
                # stream-up: single ordered body
                with contextlib.suppress(Exception):
                    await s.queue.put(("header" if not s.closed else "up", chunk))
                s.closed = True
    except Exception as e:
        log_error(f"xhttp up {uid[:8]}: {e}", source="relay")
    finally:
        await release_ip(uid, handle)
        s.last = time.time()
        if mode == "packet-up":
            s.closed = False  # next POST starts a fresh chunk series
    return StreamingResponse(iter([b""]), status_code=200, headers={"server": "cloudflare"},
                             media_type="application/grpc")

async def xhttp_uplink_packet(request: Request, uid: str, session_id: str, seq: str = ""):
    return await xhttp_uplink(request, "packet-up", uid, session_id, seq)

async def xhttp_uplink_stream(request: Request, uid: str, session_id: str):
    return await xhttp_uplink(request, "stream-up", uid, session_id)

def register_xhttp(app):
    app.add_api_route("/xhttp-siz10/{mode}/{uid}/{session_id}", xhttp_downlink, methods=["GET"])
    app.add_api_route("/xhttp-siz10/packet-up/{uid}/{session_id}/{seq}", xhttp_uplink_packet, methods=["POST"])
    app.add_api_route("/xhttp-siz10/stream-up/{uid}/{session_id}", xhttp_uplink_stream, methods=["POST"])
