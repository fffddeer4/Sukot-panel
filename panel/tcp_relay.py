# tcp_relay.py — SUKOT raw-TCP VLESS relay (optional; needs an exposed TCP port)
import asyncio, struct, contextlib, os
from core import log_error, tunnel_open, tunnel_close
from links import is_link_allowed, check_and_use, get_link, links
import speed_limit
from outbound import open_target_connection

TCP_LISTEN_PORT = int(os.environ.get("TCP_LISTEN_PORT", "6543") or 6543)
SERVER = None

def _parse_header(data: bytes):
    """Raw TCP: UUID comes from the VLESS header itself (bytes 1..17)."""
    try:
        if len(data) < 24:
            return None, 0, 0, None, data
        uuid_hex = data[1:17]
        uid = "-".join((uuid_hex.hex()[0:8], uuid_hex.hex()[8:12], uuid_hex.hex()[12:16],
                        uuid_hex.hex()[16:20], uuid_hex.hex()[20:32]))
        addon = data[17]
        pos = 18 + addon
        if len(data) < pos + 4:
            return None, 0, 0, None, data
        cmd = data[pos]
        port = struct.unpack(">H", data[pos + 1:pos + 3])[0]
        atyp = data[pos + 3]
        pos += 4
        if atyp == 1 and len(data) >= pos + 4:
            addr = ".".join(str(b) for b in data[pos:pos + 4]); pos += 4
        elif atyp == 2 and len(data) >= pos + 1 + data[pos]:
            ln = data[pos]; addr = data[pos + 1:pos + 1 + ln].decode("idna", "ignore"); pos += 1 + ln
        else:
            return None, 0, 0, None, data
        return uid, cmd, port, addr, data[pos:]
    except Exception:
        return None, 0, 0, None, data

async def _pump(reader, writer_b, uid, link, drop_first: bool = False, prefix: bytes = b""):
    """Pipe reader → writer_b. `prefix` is sent once before the first payload."""
    rate = link.get("speed_limit_bytes") or 0
    first = True
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                return
            if drop_first and first:
                first = False
                continue
            out = (prefix + data) if (first and prefix) else data
            first = False
            await speed_limit.throttle(uid, len(out), rate)
            if not check_and_use(uid, len(out)):
                return
            writer_b.write(out)
            with contextlib.suppress(Exception):
                await writer_b.drain()
    except Exception:
        pass

async def handle_client(reader, writer):
    peer = writer.get_extra_info("peername")
    uid = None
    tw = None
    head = b""
    try:
        # accumulate until the VLESS header parses (headers can straddle segments)
        for _ in range(4):
            chunk = await asyncio.wait_for(reader.read(4096), timeout=10)
            if not chunk:
                break
            head += chunk
            uid, cmd, port, addr, rest = _parse_header(head)
            if uid:
                break
            if len(head) > 16384:
                break
        else:
            uid, cmd, port, addr, rest = _parse_header(head)
        if not uid:
            writer.close()
            return
        link = links().get(uid)
        if not is_link_allowed(link) or cmd not in (1, 2):
            writer.close()
            return
        tunnel_open(uid)
        tr, tw = await open_target_connection(link, addr, port)
        if rest:
            tw.write(rest)
            with contextlib.suppress(Exception):
                await tw.drain()
        await asyncio.gather(
            _pump(reader, tw, uid, link),          # client → target
            _pump(tr, writer, uid, link, drop_first=False, prefix=b"\x00\x00"),  # target → client (VLESS response header)
            return_exceptions=True,
        )
    except Exception as e:
        log_error(f"tcp relay {str(uid)[:8]}: {e}", source="relay")
    finally:
        if uid:
            tunnel_close(uid)
        for w in (writer, tw):
            if w:
                with contextlib.suppress(Exception):
                    w.close()

async def start_server():
    global SERVER
    try:
        SERVER = await asyncio.start_server(handle_client, "0.0.0.0", TCP_LISTEN_PORT)
        print(f"sukot tcp-relay listening on :{TCP_LISTEN_PORT}")
    except Exception as e:
        print("tcp-relay skipped:", e)
        SERVER = None
