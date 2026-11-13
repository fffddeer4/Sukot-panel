# sukot_bot.py — SUKOT Telegram admin bot (long-polling, no webhook needed on PaaS)
import asyncio, base64, json, os, time, datetime
import httpx

import core
from core import (APP_NAME, APP_VERSION, settings, save_state, log_activity,
                  human_bytes, gb_to_bytes, sanitize_label, now_iso)
import links as ln
from links import links, get_link, get_link_info, is_link_allowed, make_link, PROTOCOLS, LIVE_PROTOCOLS

API = "https://api.telegram.org"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_IDS = [int(x) for x in os.environ.get("TELEGRAM_ADMIN_IDS", "").replace(" ", "").split(",") if x.strip().isdigit()]
PAGE_SIZE = 6

TASK = None
CLIENT: httpx.AsyncClient | None = None
STATE = {"wizard": {}, "alerts": True, "last_alert": 0}

def configure(token: str = "", admin_ids: str = "", bot_username: str = ""):
    global TOKEN, ADMIN_IDS
    if token is not None and token != "":
        TOKEN = token.strip()
    if admin_ids is not None:
        ADMIN_IDS = [int(x) for x in str(admin_ids).replace(" ", "").split(",") if x.strip().isdigit()]

def running() -> bool:
    return TASK is not None and not TASK.done()

async def _call(method: str, **payload):
    global CLIENT
    try:
        if CLIENT is None:
            CLIENT = httpx.AsyncClient(timeout=40)
        r = await CLIENT.post(f"{API}/bot{TOKEN}/{method}", json=payload)
        return r.json() if r.status_code == 200 else {"ok": False, "error_code": r.status_code}
    except Exception as e:
        return {"ok": False, "description": str(e)[:120]}

async def _send(chat_id, text, kb=None, web_app=None):
    kb_rows = kb or []
    if web_app:
        kb_rows = [[{"text": web_app[0], "web_app": {"url": web_app[1]}}]] + kb_rows
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
               "link_preview_options": {"is_disabled": True}}
    if kb_rows:
        payload["reply_markup"] = {"inline_keyboard": kb_rows}
    return await _call("sendMessage", **payload)

async def _edit(chat_id, message_id, text, kb=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML",
               "link_preview_options": {"is_disabled": True}}
    if kb:
        payload["reply_markup"] = {"inline_keyboard": kb}
    r = await _call("editMessageText", **payload)
    if not r.get("ok"):
        return await _send(chat_id, text, kb)
    return r

async def _answer(cb_id, text=None):
    return await _call("answerCallbackQuery", callback_query_id=cb_id, text=text or "", show_alert=bool(text))

async def _send_photo_url(chat_id, url, caption=""):
    return await _call("sendPhoto", chat_id=chat_id, photo=url, caption=caption)

async def _upload_doc(chat_id, fname: str, raw: bytes, caption: str = ""):
    try:
        if CLIENT is None:
            CLIENT = httpx.AsyncClient(timeout=60)
        r = await CLIENT.post(f"{API}/bot{TOKEN}/sendDocument",
                              data={"chat_id": str(chat_id), "caption": caption},
                              files={"document": (fname, raw)})
        return r.json() if r.status_code == 200 else {"ok": False}
    except Exception as e:
        return {"ok": False, "description": str(e)[:120]}

def _is_admin(chat_id) -> bool:
    if chat_id in ADMIN_IDS:
        return True
    ids = str(settings().get("bot_admin_ids") or "")
    return str(chat_id) in [x.strip() for x in ids.split(",") if x.strip()]

# ------------------------------------------------------------- keyboards
def _main_menu_kb():
    ch = core.channel_url()
    rows = [
        [{"text": "⚡ ساخت سریع کانفیگ", "callback_data": "quick"}],
        [{"text": "🧩 ساخت پیشرفته", "callback_data": "newcfg"}, {"text": "📋 لیست کانفیگ‌ها", "callback_data": "list:0"}],
        [{"text": "🗂 گروه‌های ساب", "callback_data": "subs:0"}, {"text": "🟢 آنلاین‌ها", "callback_data": "online"}],
        [{"text": "🔥 پرمصرف‌ها", "callback_data": "top"}, {"text": "⏳ نزدیک انقضا", "callback_data": "expiring"}],
        [{"text": "📊 آمار", "callback_data": "stats"}, {"text": "🖥 سرور", "callback_data": "server"}],
        [{"text": "💾 بکاپ", "callback_data": "backup"},
         {"text": "🔔 هشدارها: " + ("روشن" if STATE["alerts"] else "خاموش"), "callback_data": "alerts:toggle"}],
        [{"text": "📣 کانال SUKOT", "url": ch}],
        [{"text": "📖 راهنما", "callback_data": "help"}, {"text": "🔄 رفرش", "callback_data": "menu"}],
    ]
    base = core.public_url()
    if base and TOKEN:
        rows.insert(0, [{"text": "🚀 باز کردن مینی‌اپ SUKOT", "web_app": {"url": base + "/app"}}])
    return rows

def _config_list_kb(page: int):
    items = sorted(links().values(), key=lambda x: x.get("created_at") or "", reverse=True)
    total = len(items)
    start = page * PAGE_SIZE
    chunk = items[start:start + PAGE_SIZE]
    rows = []
    for c in chunk:
        rows.append([{"text": ("🟢 " if is_link_allowed(c) else "🔴 ") + str(c.get("label"))[:26],
                      "callback_data": f"cfg:{c['uuid']}"}])
    nav = []
    if page > 0:
        nav.append({"text": "◀ قبلی", "callback_data": f"list:{page-1}"})
    if start + PAGE_SIZE < total:
        nav.append({"text": "بعدی ▶", "callback_data": f"list:{page+1}"})
    if nav:
        rows.append(nav)
    rows.append([{"text": "➕ ساخت کانفیگ جدید", "callback_data": "quick"}])
    rows.append([{"text": "⬅ منوی اصلی", "callback_data": "menu"}])
    return rows, total, chunk

def _config_detail_kb(c):
    on = is_link_allowed(c)
    return [
        [{"text": "🔗 لینک اتصال + QR", "callback_data": f"link:{c['uuid']}"}],
        [{"text": "✏️ ویرایش", "callback_data": f"edit:{c['uuid']}"},
         {"text": "👥 کلاینت‌ها", "callback_data": f"clients:{c['uuid']}"}],
        [{"text": ("⛔ غیرفعال‌سازی" if on else "✅ فعال‌سازی"), "callback_data": f"toggle:{c['uuid']}"},
         {"text": "🔄 ریست مصرف", "callback_data": f"reset:{c['uuid']}"}],
        [{"text": "🗑 حذف کانفیگ", "callback_data": f"del:{c['uuid']}"}],
        [{"text": "⬅ بازگشت به لیست", "callback_data": "list:0"}],
    ]

QUICK_PRESETS = [("۱۰ گیگ", 10, 30), ("۳۰ گیگ", 30, 30), ("۵۰ گیگ", 50, 30),
                 ("۱۰۰ گیگ", 100, 30), ("۲۰۰ گیگ", 200, 60), ("♾ نامحدود", 0, 0)]

def _quick_kb():
    rows = []
    for label, gb, days in QUICK_PRESETS:
        rows.append([{"text": f"📦 {label} · {days} روز" if days else f"📦 {label} · بدون انقضا",
                      "callback_data": f"quickmk:{gb}:{days}"}])
    rows.append([{"text": "🧩 ساخت پیشرفته (مرحله‌ای)", "callback_data": "newcfg"}])
    rows.append([{"text": "⬅ منوی اصلی", "callback_data": "menu"}])
    return rows

def _edit_kb(c):
    return [
        [{"text": "➕ ۵ گیگ", "callback_data": f"addv:{c['uuid']}:5"},
         {"text": "➕ ۱۰ گیگ", "callback_data": f"addv:{c['uuid']}:10"},
         {"text": "➕ ۵۰ گیگ", "callback_data": f"addv:{c['uuid']}:50"}],
        [{"text": "📅 +۷ روز", "callback_data": f"addd:{c['uuid']}:7"},
         {"text": "📅 +۳۰ روز", "callback_data": f"addd:{c['uuid']}:30"},
         {"text": "📅 +۹۰ روز", "callback_data": f"addd:{c['uuid']}:90"}],
        [{"text": "🔄 ریست مصرف", "callback_data": f"reset:{c['uuid']}"},
         {"text": "♾ حجم نامحدود", "callback_data": f"unlim:{c['uuid']}"}],
        [{"text": "🎲 اسم تازه", "callback_data": f"rename:{c['uuid']}"}],
        [{"text": "⬅ بازگشت", "callback_data": f"cfg:{c['uuid']}"}],
    ]

# ------------------------------------------------------------- texts
def _config_text(c) -> str:
    info = get_link_info(c)
    lim = c.get("limit_bytes") or 0
    used = c.get("used_bytes") or 0
    pct = int(used * 100 / lim) if lim else 0
    exp = "بدون انقضا" if not c.get("expires_at") else str(c.get("expires_at"))[:10]
    status = "🟢 فعال" if is_link_allowed(c) else "🔴 غیرفعال/تمام‌شده"
    ch = core.channel_url()
    return (f"<b>🖥 {c['label']}</b>\n"
            f"<code>{c['uuid']}</code>\n\n"
            f"وضعیت: {status}\n"
            f"پروتکل: <code>{c.get('protocol')}</code>\n"
            f"حجم: {human_bytes(used)} از {'♾' if not lim else human_bytes(lim)} ({pct}%)\n"
            f"انقضا: {exp}\n"
            f"کلاینت‌ها: {info.get('clients_count', 0)}\n\n"
            f"💬 پشتیبانی: @{(settings().get('support_username') or 'SUKOT1344').lstrip('@')}\n"
            f"📣 کانال: {ch}")

def _help_text():
    ch = core.channel_url()
    return (f"📖 <b>راهنمای ربات {APP_NAME}</b>\n\n"
            "/new یا /quick — ساخت سریع کانفیگ\n"
            "/find — جستجوی کانفیگ\n"
            "/online — کاربران آنلاین\n"
            "/top — پرمصرف‌ترین‌ها\n"
            "/expiring — نزدیک انقضا\n"
            "/server — وضعیت سرور\n"
            "/bulk — ساخت دسته‌ای (مثال: <code>/bulk 10 20 30</code>)\n"
            "/backup — بکاپ کامل\n"
            "/seturl — ثبت آدرس عمومی پنل\n"
            "/alerts — روشن/خاموش کردن هشدارها\n\n"
            f"📣 کانال رسمی: {ch}\n"
            f"💬 پشتیبانی: @{(settings().get('support_username') or 'SUKOT1344').lstrip('@')}")

async def _stats_text():
    st = links()
    total = len(st)
    active = sum(1 for c in st.values() if is_link_allowed(c))
    traffic = sum(c.get("used_bytes") or 0 for c in st.values())
    online = len(core.TUNNELS_NOW)
    subs = len(ln.subs())
    import psutil
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    return (f"📊 <b>آمار کلی {APP_NAME}</b>\n\n"
            f"کلی: {total}\n فعال: {active}\n گروه‌های ساب: {subs}\n"
            f"ترافیک کل: {human_bytes(traffic)}\n آنلاین الان: {online}\n\n"
            f"CPU: {cpu:.0f}%  ·  RAM: {ram:.0f}%\n\n"
            f"🌐 آدرس پنل: {core.public_url() or 'تنظیم نشده'}")

async def _server_text():
    import psutil
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    return (f"🖥 <b>وضعیت سرور</b>\n\n"
            f"CPU: {psutil.cpu_percent():.0f}%\n"
            f"RAM: {human_bytes(vm.used)} / {human_bytes(vm.total)} ({vm.percent}%)\n"
            f"دیسک: {human_bytes(disk.used)} / {human_bytes(disk.total)} ({disk.percent}%)\n"
            f"شبکه: ↓{human_bytes(net.bytes_recv)} ↑{human_bytes(net.bytes_sent)}\n"
            f"پلتفرم: {os.uname().sysname} · Python 3\n")

def _expiring_items():
    out = []
    now = time.time()
    for c in links().values():
        exp = core.expires_in_seconds(c)
        lim = c.get("limit_bytes") or 0
        used = c.get("used_bytes") or 0
        near_exp = exp is not None and 0 < exp <= 3 * 86400
        near_vol = lim and used / lim >= 0.85
        if near_exp or near_vol:
            out.append(c)
    return out

# ------------------------------------------------------------- link card
async def _send_link_card(chat_id, c):
    base = core.public_url()
    ch = core.channel_url()
    line = (ln.vless_link_for_link(c) or "")
    reach = ""
    if base:
        try:
            async with httpx.AsyncClient(timeout=6) as cli:
                r = await cli.get(base + "/assets/favicon.png")
                reach = "✅ پنل در دسترس است" if r.status_code == 200 else "⚠️ پاسخ پنل: " + str(r.status_code)
        except Exception:
            reach = "⚠️ پنل هنوز از بیرون در دسترس نیست"
    text = (f"<b>🔗 {c['label']}</b>\n"
            f"سرور: <code>{base or 'آدرس پنل تنظیم نشده'}</code>\n"
            f"{reach}\n\n"
            f"<code>{line}</code>\n\n"
            + (f"📄 صفحه‌ی اشتراک: {base}/subscription/{c['uuid']}\n"
               f"📥 لینک ساب برای اپ: {base}/sub/{c['uuid']}\n\n" if base else "")
            + f"💬 پشتیبانی: @{(settings().get('support_username') or 'SUKOT1344').lstrip('@')}\n"
              f"📣 کانال: {ch}")
    kb = [[{"text": "🌐 باز کردن صفحه‌ی اشتراک", "url": f"{base}/subscription/{c['uuid']}"}]] if base else None
    await _send(chat_id, text, kb)
    if line and base:
        from urllib.parse import quote as _q
        qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=420x420&data=" + _q(line, safe="")
        await _send_photo_url(chat_id, qr_url, "📷 QR کانفیگ — با اپ اسکن کن")

# ------------------------------------------------------------- flows
async def cb_link(chat_id, uid):
    c = get_link(uid)
    if not c:
        await _send(chat_id, "این کانفیگ دیگر وجود ندارد.")
        return
    await _send_link_card(chat_id, c)

async def cb_toggle(chat_id, uid):
    c = get_link(uid)
    if not c:
        return
    c["active"] = not c.get("active", True)
    save_state()
    log_activity(f"ربات: «{c['label']}» " + ("فعال" if c["active"] else "غیرفعال") + " شد", actor="bot")
    await _send(chat_id, ("✅ فعال شد: " if c["active"] else "⛔ غیرفعال شد: ") + c["label"])

async def cb_reset(chat_id, uid):
    c = get_link(uid)
    if not c:
        return
    c["used_bytes"] = 0
    import speed_limit
    speed_limit.reset_bucket(uid)
    save_state()
    await _send(chat_id, "🔄 حجم مصرفی ریست شد: " + c["label"])

async def cb_unlim(chat_id, uid):
    c = get_link(uid)
    if not c:
        return
    c["limit_bytes"] = 0
    save_state()
    await _send(chat_id, "♾ حجم نامحدود شد: " + c["label"])

async def cb_add_volume(chat_id, uid, gb):
    c = get_link(uid)
    if not c:
        return
    lim = c.get("limit_bytes") or 0
    c["limit_bytes"] = lim + gb_to_bytes(gb)
    save_state()
    await _send(chat_id, f"➕ {gb} گیگ اضافه شد — حجم جدید: {human_bytes(c['limit_bytes'])}")

async def cb_add_days(chat_id, uid, days):
    c = get_link(uid)
    if not c:
        return
    base = c.get("expires_at")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    d = core.parse_iso(base) if base and core.parse_iso(base) and core.parse_iso(base) > now else now
    c["expires_at"] = (d + timedelta(days=days)).isoformat()
    save_state()
    await _send(chat_id, f"📅 {days} روز تمدید شد — انقضای جدید: {c['expires_at'][:10]}")

async def cb_rename(chat_id, uid):
    c = get_link(uid)
    if not c:
        return
    nm = core.random_config_names(count=1)[0]
    c["label"] = nm
    save_state()
    await _send(chat_id, f"🎲 اسم جدید: {nm}")

async def cb_delete(chat_id, uid):
    c = get_link(uid)
    if not c:
        return
    ln.remove_link_everywhere(uid)
    links().pop(uid, None)
    save_state()
    await _send(chat_id, "🗑 حذف شد: " + c["label"])

async def cb_clients(chat_id, uid, mid=None):
    parent = get_link(uid)
    if not parent:
        return
    children = [c for c in links().values() if c.get("parent_inbound_id") == uid]
    rows = [[{"text": ("🟢 " if is_link_allowed(c) else "🔴 ") + str(c.get("label"))[:24],
              "callback_data": f"clink:{c['uuid']}"}] for c in children[:10]]
    rows.append([{"text": "➕ افزودن کاربر جدید", "callback_data": f"cadd:{uid}"}])
    rows.append([{"text": "⬅ بازگشت", "callback_data": f"cfg:{uid}"}])
    text = (f"<b>👥 کلاینت‌های «{parent['label']}»</b>\n"
            f"تعداد: {len(children)}"
            + (f"\nمحدودیت اینباند: {parent.get('client_limit') or 'بدون محدودیت'}" if parent.get("client_limit") else ""))
    if mid:
        await _edit(chat_id, mid, text, rows)
    else:
        await _send(chat_id, text, rows)

async def cb_client_add(chat_id, uid):
    parent = get_link(uid)
    if not parent:
        return
    from core import new_uuid4
    n = len([c for c in links().values() if c.get("parent_inbound_id") == uid]) + 1
    child = make_link(label=f"{parent['label']}-u{n}",
                      limit_bytes=parent.get("limit_bytes") or 0,
                      expires_at=parent.get("expires_at"),
                      protocol=parent.get("protocol"),
                      fingerprint=parent.get("fingerprint"), alpn=parent.get("alpn"),
                      port=parent.get("port"), fragment=parent.get("fragment"),
                      ip_limit=parent.get("ip_limit"), connection_limit=parent.get("connection_limit"),
                      speed_limit_bytes=parent.get("speed_limit_bytes"),
                      parent_inbound_id=uid, created_by="bot", admin_id="bot")
    await _send(chat_id, f"✅ کاربر ساخته شد: {child['label']}", )
    await cb_clients(chat_id, uid)

async def cb_client_link(chat_id, uid):
    c = get_link(uid)
    if not c:
        return
    await _send_link_card(chat_id, c)

async def quick_make(chat_id, gb, days):
    from links import create_sub_group
    c = make_link(label=core.random_config_names(count=1)[0],
                  limit_bytes=gb_to_bytes(gb), expires_at=None,
                  protocol="vless-ws", created_by="bot", admin_id="bot")
    if days:
        from datetime import datetime, timedelta, timezone
        c["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        save_state()
    base = core.public_url()
    text = (f"✅ <b>کانفیگ ساخته شد</b>\n\n🖥 {c['label']}\n"
            f"📦 حجم: {'♾' if not gb else f'{gb} گیگ'}\n"
            f"📅 انقضا: {'بدون انقضا' if not days else str(c['expires_at'])[:10]}\n\n"
            + (f"📥 لینک ساب:\n<code>{base}/sub/{c['uuid']}</code>\n" if base else "")
            + "🔗 لینک و QR با دکمه‌ی زیر")
    kb = [[{"text": "🔗 لینک اتصال + QR", "callback_data": f"link:{c['uuid']}"}],
          [{"text": "⬅ منوی اصلی", "callback_data": "menu"}]]
    await _send(chat_id, text, kb)

async def subs_page(chat_id, page, mid=None):
    subs = list(ln.subs().values())
    rows = [[{"text": "🗂 " + str(s.get("name"))[:24], "callback_data": f"sub:{s['id']}"}]
            for s in subs]
    rows.append([{"text": "➕ ساخت گروه از دو کانفیگ آخر", "callback_data": "submix"}])
    rows.append([{"text": "⬅ منوی اصلی", "callback_data": "menu"}])
    text = f"<b>🗂 گروه‌های ساب</b>\nتعداد: {len(subs)}"
    if mid:
        await _edit(chat_id, mid, text, rows)
    else:
        await _send(chat_id, text, rows)

async def cb_sub_detail(chat_id, sid, mid=None):
    s = ln.subs().get(sid)
    if not s:
        await _send(chat_id, "این گروه حذف شده است.")
        return
    base = core.public_url()
    n = len(s.get("link_ids") or [])
    text = (f"<b>🗂 {s['name']}</b>\nاعضا: {n}\n"
            + (f"لینک عمومی:\n<code>{base}/sub-group/{s['uuid_key']}</code>" if base else "آدرس پنل تنظیم نشده"))
    rows = [[{"text": "🗑 حذف گروه", "callback_data": f"subdel:{sid}"}],
            [{"text": "⬅ بازگشت", "callback_data": "subs:0"}]]
    if mid:
        await _edit(chat_id, mid, text, rows)
    else:
        await _send(chat_id, text, rows)

async def cb_sub_mix(chat_id):
    items = sorted(links().values(), key=lambda x: x.get("created_at") or "", reverse=True)[:2]
    if len(items) < 2:
        await _send(chat_id, "حداقل دو کانفیگ لازم است.")
        return
    s = ln.create_sub_group(name="گروه ربات · " + time.strftime("%m-%d %H:%M"),
                            link_ids=[c["uuid"] for c in items])
    await cb_sub_detail(chat_id, s["id"])

async def cb_sub_delete(chat_id, sid):
    ln.subs().pop(sid, None)
    save_state()
    await _send(chat_id, "🗑 گروه حذف شد.")
    await subs_page(chat_id, 0)

# ------------------------------------------------------------- bulk
async def cmd_bulk(chat_id, arg: str):
    parts = arg.split()
    try:
        n = min(int(parts[0]), 50)
        gb = int(parts[1])
        days = int(parts[2])
        name = parts[3] if len(parts) > 3 else APP_NAME
    except Exception:
        await _send(chat_id, "فرمت: <code>/bulk تعداد حجم‌گیگ روز [نام]</code>\nمثال: <code>/bulk 10 20 30</code>")
        return
    ids = []
    for i in range(n):
        c = make_link(label=f"{name}-{i+1:02d}", limit_bytes=gb_to_bytes(gb),
                      protocol="vless-ws", created_by="bot", admin_id="bot")
        if days:
            from datetime import datetime, timedelta, timezone
            c["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        ids.append(c["uuid"])
    save_state()
    s = ln.create_sub_group(name=f"بسته {name}", link_ids=ids)
    base = core.public_url()
    lines = []
    for uid in ids:
        c = get_link(uid)
        lines.append(ln.vless_link_for_link(c))
    raw = "\n".join([x for x in lines if x])
    await _upload_doc(chat_id, f"configs-{n}.txt", raw.encode(), f"📄 {n} کانفیگ ({gb} گیگ · {days} روز)")
    await _send(chat_id, f"🗂 گروه ساب ساخته شد:\n<code>{base}/sub-group/{s['uuid_key']}</code>" if base else "گروه ساخته شد (آدرس پنل تنظیم نشده)")

# ------------------------------------------------------------- wizard (advanced create)
WIZ_STEPS = ["label", "protocol", "fingerprint", "alpn", "port", "volume", "speed", "iplimit", "days"]

def _wiz_state(chat_id) -> dict:
    return STATE["wizard"].get(chat_id, {})

async def wiz_start(chat_id, mid=None):
    STATE["wizard"][chat_id] = {"step": "label", "data": {}}
    text = "🧩 <b>ساخت پیشرفته — مرحله ۱/۹</b>\nنام کانفیگ را بفرست (یا <code>auto</code> برای اسم خفن)"
    kb = [[{"text": "🎲 اسم خودکار خفن", "callback_data": "w:autolabel"}],
          [{"text": "❌ انصراف", "callback_data": "w:cancel"}]]
    if mid:
        await _edit(chat_id, mid, text, kb)
    else:
        await _send(chat_id, text, kb)

async def wiz_advance(chat_id, mid=None):
    w = _wiz_state(chat_id)
    step = w.get("step")
    d = w.get("data", {})
    idx = WIZ_STEPS.index(step) if step in WIZ_STEPS else 0
    nxt = WIZ_STEPS[idx + 1] if idx + 1 < len(WIZ_STEPS) else None
    if nxt is None:
        c = make_link(label=d.get("label") or core.random_config_names(count=1)[0],
                      limit_bytes=gb_to_bytes(d.get("volume", 0)),
                      protocol=d.get("protocol", "vless-ws"),
                      fingerprint=d.get("fingerprint", "chrome"),
                      alpn=d.get("alpn", "http1"),
                      port=int(d.get("port", 443) or 443),
                      speed_limit_bytes=gb_to_bytes(d.get("speed", 0)) // 8 if d.get("speed") else 0,
                      ip_limit=int(d.get("iplimit", 0) or 0),
                      created_by="bot", admin_id="bot")
        if d.get("days"):
            from datetime import datetime, timedelta, timezone
            c["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=int(d["days"]))).isoformat()
            save_state()
        STATE["wizard"].pop(chat_id, None)
        base = core.public_url()
        await _send(chat_id, f"✅ کانفیگ ساخته شد: <b>{c['label']}</b>"
                     + (f"\n📥 ساب: <code>{base}/sub/{c['uuid']}</code>" if base else ""),
                     [[{"text": "🔗 لینک + QR", "callback_data": f"link:{c['uuid']}"}],
                      [{"text": "⬅ منوی اصلی", "callback_data": "menu"}]])
        return
    w["step"] = nxt
    prompts = {
        "protocol": ("پروتکل را انتخاب کن:", [[{"text": "VLESS + WebSocket", "callback_data": "w:proto:vless-ws"}],
                    [{"text": "XHTTP (packet-up)", "callback_data": "w:proto:xhttp-packet-up"}],
                    [{"text": "XHTTP (stream-up)", "callback_data": "w:proto:xhttp-stream-up"}],
                    [{"text": "VMess + WebSocket 🔗", "callback_data": "w:proto:vmess-ws"}],
                    [{"text": "Trojan + WebSocket 🔗", "callback_data": "w:proto:trojan-ws"}],
                    [{"text": "❌ انصراف", "callback_data": "w:cancel"}]]),
        "fingerprint": ("اثر انگشت TLS (uTLS):", [[{"text": t, "callback_data": f"w:fp:{t}"}] for t in
                    ["chrome", "firefox", "safari", "ios", "android", "edge", "random"]] + [[{"text": "❌ انصراف", "callback_data": "w:cancel"}]]),
        "alpn": ("ALPN:", [[{"text": "http/1.1 (پیشنهادی)", "callback_data": "w:alpn:http1"}],
                [{"text": "h2,http/1.1", "callback_data": "w:alpn:h2h1"}],
                [{"text": "پیش‌فرض", "callback_data": "w:alpn:http1"}],
                [{"text": "❌ انصراف", "callback_data": "w:cancel"}]]),
        "port": ("پورت را بفرست (عدد) — خالی/پیش‌فرض یعنی 443:", [[{"text": "۴۴۳ پیش‌فرض", "callback_data": "w:port:443"}], [{"text": "❌ انصراف", "callback_data": "w:cancel"}]]),
        "volume": ("حجم به گیگ (۰ = نامحدود):", [[{"text": "۱۰", "callback_data": "w:vol:10"}], [{"text": "۳۰", "callback_data": "w:vol:30"}], [{"text": "۵۰", "callback_data": "w:vol:50"}], [{"text": "♾ نامحدود", "callback_data": "w:vol:0"}], [{"text": "❌ انصراف", "callback_data": "w:cancel"}]]),
        "speed": ("محدودیت سرعت مگابیت (۰ = بی‌مرز):", [[{"text": "بدون محدودیت", "callback_data": "w:spd:0"}], [{"text": "۵ Mbit", "callback_data": "w:spd:5"}], [{"text": "۲۰ Mbit", "callback_data": "w:spd:20"}], [{"text": "❌ انصراف", "callback_data": "w:cancel"}]]),
        "iplimit": ("سقف IP هم‌زمان (۰ = بی‌مرز):", [[{"text": "بدون محدودیت", "callback_data": "w:ip:0"}], [{"text": "۱", "callback_data": "w:ip:1"}], [{"text": "۲", "callback_data": "w:ip:2"}], [{"text": "۳", "callback_data": "w:ip:3"}], [{"text": "❌ انصراف", "callback_data": "w:cancel"}]]),
        "days": ("مدت اعتبار به روز (۰ = بی‌نهایت):", [[{"text": "۳۰ روز", "callback_data": "w:days:30"}], [{"text": "۶۰ روز", "callback_data": "w:days:60"}], [{"text": "بی‌نهایت", "callback_data": "w:days:0"}], [{"text": "✅ ساخت کانفیگ", "callback_data": "w:days:0"}], [{"text": "❌ انصراف", "callback_data": "w:cancel"}]]),
    }
    titles = {"protocol": "۲/۹ · پروتکل", "fingerprint": "۳/۹ · اثر انگشت TLS", "alpn": "۴/۹ · ALPN",
              "port": "۵/۹ · پورت", "volume": "۶/۹ · حجم", "speed": "۷/۹ · سرعت",
              "iplimit": "۸/۹ · سقف IP", "days": "۹/۹ · اعتبار"}
    p, kb = prompts[nxt]
    await _send(chat_id, f"🧩 <b>ساخت پیشرفته — {titles[nxt]}</b>\n{p}", kb)

async def wiz_pick(chat_id, data: str, mid=None):
    w = _wiz_state(chat_id)
    k, _, v = data.partition(":")
    d = w.setdefault("data", {})
    if k == "autolabel":
        d["label"] = core.random_config_names(count=1)[0]
    elif k == "proto":
        d["protocol"] = v
    elif k == "fp":
        d["fingerprint"] = v
    elif k == "alpn":
        d["alpn"] = v
    elif k == "port":
        d["port"] = v
    elif k == "vol":
        d["volume"] = v
    elif k == "spd":
        d["speed"] = v
    elif k == "ip":
        d["iplimit"] = v
    elif k == "days":
        d["days"] = v
    await wiz_advance(chat_id)

async def wiz_text(chat_id, text: str):
    w = _wiz_state(chat_id)
    step = w.get("step")
    d = w.setdefault("data", {})
    if step == "label":
        d["label"] = sanitize_label(text) if text.lower() != "auto" else core.random_config_names(count=1)[0]
        await wiz_advance(chat_id)
    elif step == "port":
        d["port"] = text.strip() if text.strip().isdigit() else 443
        await wiz_advance(chat_id)
    elif step == "volume":
        d["volume"] = text.strip() if text.strip().replace(".", "").isdigit() else 0
        await wiz_advance(chat_id)
    elif step == "speed":
        d["speed"] = text.strip() if text.strip().replace(".", "").isdigit() else 0
        await wiz_advance(chat_id)
    elif step == "iplimit":
        d["iplimit"] = text.strip() if text.strip().isdigit() else 0
        await wiz_advance(chat_id)
    elif step == "days":
        d["days"] = text.strip() if text.strip().isdigit() else 30
        await wiz_advance(chat_id)
    else:
        await _send(chat_id, "از دکمه‌ها استفاده کن یا /cancel بزن.")

# ------------------------------------------------------------- alerts loop
async def _alerts_loop():
    while True:
        try:
            await asyncio.sleep(600)
            if not STATE["alerts"]:
                continue
            ids = ADMIN_IDS + [int(x) for x in str(settings().get("bot_admin_ids") or "").replace(" ", "").split(",") if x.strip().isdigit()]
            if not ids or not links():
                continue
            now = time.time()
            for c in links().values():
                exp = core.expires_in_seconds(c)
                if exp is not None and 0 < exp <= 3600 * 3 and not c.get("_warned_exp"):
                    for cid in set(ids):
                        await _send(cid, f"⏳ «{c['label']}» تا {int(exp//3600)} ساعت دیگه منقضی می‌شه.",
                                    [[{"text": "⏳ نمایش لیست", "callback_data": "expiring"}]])
                    c["_warned_exp"] = True
                elif exp is not None and exp <= 0 and not c.get("_warned_dead"):
                    for cid in set(ids):
                        await _send(cid, f"⛔ «{c['label']}» منقضی شد.")
                    c["_warned_dead"] = True
                lim = c.get("limit_bytes") or 0
                used = c.get("used_bytes") or 0
                if lim and used / lim >= 0.95 and not c.get("_warned_vol"):
                    for cid in set(ids):
                        await _send(cid, f"📦 «{c['label']}» حجمش تموم شد ({human_bytes(used)}/{human_bytes(lim)}).")
                    c["_warned_vol"] = True
            save_state()
        except Exception as e:
            await asyncio.sleep(30)

# ------------------------------------------------------------- polling
async def _handle_update(up: dict):
    if not up:
        return
    msg = up.get("message") or up.get("channel_post")
    cb = up.get("callback_query")
    if cb:
        chat_id = (cb.get("message") or {}).get("chat", {}).get("id")
        data = cb.get("data") or ""
        cid = cb.get("id")
        if not _is_admin(chat_id):
            await _answer(cid, "فقط ادمین‌ها")
            return
        await _answer(cid)
        try:
            if data.startswith("list:"):
                rows, total, _ = _config_list_kb(int(data.split(":")[1]))
                await _edit(chat_id, cb["message"]["message_id"],
                            f"📋 <b>لیست کانفیگ‌ها</b> ({total})", rows)
            elif data == "menu":
                STATE["wizard"].pop(chat_id, None)
                await _edit(chat_id, cb["message"]["message_id"],
                            f"👋 🛠 <b>{APP_NAME} Control Center</b>", _main_menu_kb())
            elif data == "quick":
                await _edit(chat_id, cb["message"]["message_id"],
                            "⚡ <b>ساخت سریع</b> — یک پریست انتخاب کن:", _quick_kb())
            elif data.startswith("quickmk:"):
                _, gb, days = data.split(":")
                await quick_make(chat_id, int(gb), int(days))
            elif data == "newcfg":
                await wiz_start(chat_id, mid=cb["message"]["message_id"])
            elif data.startswith("w:"):
                if data == "w:cancel":
                    STATE["wizard"].pop(chat_id, None)
                    await _edit(chat_id, cb["message"]["message_id"], "انصراف داده شد.",
                                [[{"text": "⬅ منوی اصلی", "callback_data": "menu"}]])
                elif data == "w:autolabel":
                    await wiz_pick(chat_id, "autolabel", mid=cb["message"]["message_id"])
                else:
                    await wiz_pick(chat_id, data[2:], mid=cb["message"]["message_id"])
            elif data.startswith("cfg:"):
                c = get_link(data.split(":")[1])
                if not c:
                    await _edit(chat_id, cb["message"]["message_id"], "این کانفیگ حذف شده است.")
                    return
                await _edit(chat_id, cb["message"]["message_id"], _config_text(c), _config_detail_kb(c))
            elif data.startswith("link:"):
                await cb_link(chat_id, data.split(":")[1])
            elif data.startswith("toggle:"):
                await cb_toggle(chat_id, data.split(":")[1])
            elif data.startswith("reset:"):
                await cb_reset(chat_id, data.split(":")[1])
            elif data.startswith("unlim:"):
                await cb_unlim(chat_id, data.split(":")[1])
            elif data.startswith("addv:"):
                _, uid, gb = data.split(":")
                await cb_add_volume(chat_id, uid, int(gb))
            elif data.startswith("addd:"):
                _, uid, days = data.split(":")
                await cb_add_days(chat_id, uid, int(days))
            elif data.startswith("rename:"):
                await cb_rename(chat_id, data.split(":")[1])
            elif data.startswith("del:"):
                await cb_delete(chat_id, data.split(":")[1])
            elif data.startswith("clients:"):
                await cb_clients(chat_id, data.split(":")[1], mid=cb["message"]["message_id"])
            elif data.startswith("cadd:"):
                await cb_client_add(chat_id, data.split(":")[1])
            elif data.startswith("clink:"):
                await cb_client_link(chat_id, data.split(":")[1])
            elif data.startswith("subs:"):
                await subs_page(chat_id, int(data.split(":")[1]), mid=cb["message"]["message_id"])
            elif data.startswith("sub:"):
                await cb_sub_detail(chat_id, data.split(":")[1], mid=cb["message"]["message_id"])
            elif data == "submix":
                await cb_sub_mix(chat_id)
            elif data.startswith("subdel:"):
                await cb_sub_delete(chat_id, data.split(":")[1])
            elif data == "online":
                on = [c for c in links().values() if core.TUNNELS_NOW.get(c["uuid"])]
                txt = "🟢 <b>آنلاین‌ها</b>\n" + ("\n".join("• " + c["label"] for c in on[:15]) if on else "کسی آنلاین نیست.")
                await _edit(chat_id, cb["message"]["message_id"], txt)
            elif data == "top":
                top = sorted(links().values(), key=lambda c: -(c.get("used_bytes") or 0))[:10]
                txt = "🔥 <b>پرمصرف‌ترین‌ها</b>\n" + "\n".join(
                    f"• {c['label']} — {human_bytes(c.get('used_bytes') or 0)}" for c in top) if top else "چیزی نیست."
                await _edit(chat_id, cb["message"]["message_id"], txt)
            elif data == "expiring":
                ex = _expiring_items()
                txt = "⏳ <b>نزدیک انقضا / پرحجم</b>\n" + ("\n".join("• " + c["label"] for c in ex[:15]) if ex else "چیزی نیست.")
                await _edit(chat_id, cb["message"]["message_id"], txt)
            elif data == "stats":
                await _edit(chat_id, cb["message"]["message_id"], await _stats_text())
            elif data == "server":
                await _edit(chat_id, cb["message"]["message_id"], await _server_text())
            elif data == "backup":
                await cmd_backup(chat_id, mid=cb["message"]["message_id"])
            elif data == "help":
                await _edit(chat_id, cb["message"]["message_id"], _help_text())
            elif data == "alerts:toggle":
                STATE["alerts"] = not STATE["alerts"]
                await _edit(chat_id, cb["message"]["message_id"],
                            f"👋 🛠 <b>{APP_NAME} Control Center</b>", _main_menu_kb())
        except Exception as e:
            await _send(chat_id, f"خطا: {str(e)[:120]}")
        return

    if not msg:
        return
    chat_id = msg["chat"]["id"]
    if not _is_admin(chat_id):
        return
    text = (msg.get("text") or "").strip()
    if not text:
        return
    if text.startswith("/start") or text in ("/menu", "/admin"):
        await _send(chat_id, f"👋 🛠 <b>{APP_NAME} Control Center</b>", _main_menu_kb())
    elif text.startswith("/id"):
        await _send(chat_id, f"شناسه‌ی عددی تو: <code>{chat_id}</code>")
    elif text in ("/new", "/quick"):
        await _send(chat_id, "⚡ <b>ساخت سریع</b> — یک پریست انتخاب کن:", _quick_kb())
    elif text.startswith("/find"):
        q = text[6:].strip().lower()
        res = [c for c in links().values() if q in str(c.get("label")).lower() or q in c["uuid"].lower()][:8] if q else []
        if res:
            rows = [[{"text": "🟢 " + c["label"], "callback_data": f"cfg:{c['uuid']}"}] for c in res]
            await _send(chat_id, f"🔎 {len(res)} نتیجه:", rows)
        else:
            await _send(chat_id, "چیزی پیدا نشد.")
    elif text == "/online":
        on = [c for c in links().values() if core.TUNNELS_NOW.get(c["uuid"])]
        txt = "🟢 <b>آنلاین‌ها</b>\n" + ("\n".join("• " + c["label"] for c in on[:15]) if on else "کسی آنلاین نیست.")
        await _send(chat_id, txt)
    elif text == "/top":
        top = sorted(links().values(), key=lambda c: -(c.get("used_bytes") or 0))[:10]
        await _send(chat_id, "🔥 <b>پرمصرف‌ترین‌ها</b>\n" + "\n".join(
            f"• {c['label']} — {human_bytes(c.get('used_bytes') or 0)}" for c in top))
    elif text == "/expiring":
        ex = _expiring_items()
        await _send(chat_id, "⏳ <b>نزدیک انقضا</b>\n" + ("\n".join("• " + c["label"] for c in ex[:15]) if ex else "چیزی نیست."))
    elif text == "/server":
        await _send(chat_id, await _server_text())
    elif text == "/stats":
        await _send(chat_id, await _stats_text())
    elif text.startswith("/bulk"):
        await cmd_bulk(chat_id, text[6:].strip())
    elif text == "/backup":
        await cmd_backup(chat_id)
    elif text.startswith("/seturl"):
        u = text[7:].strip()
        if u and not (u.startswith("http://localhost") or u.startswith("http://127.")):
            if not u.startswith("http"):
                u = "https://" + u
            settings()["public_base_url"] = u.rstrip("/")
            save_state()
            await _send(chat_id, f"🌐 آدرس پنل ثبت شد: {u}")
        else:
            await _send(chat_id, "آدرس معتبر بفرست (مثل https://x.shiprr.dev)")
    elif text == "/alerts":
        STATE["alerts"] = not STATE["alerts"]
        await _send(chat_id, "هشدارها: " + ("روشن 🔔" if STATE["alerts"] else "خاموش 🔕"))
    elif text == "/cancel":
        STATE["wizard"].pop(chat_id, None)
        await _send(chat_id, "انصراف داده شد.", [[{"text": "⬅ منوی اصلی", "callback_data": "menu"}]])
    elif text.startswith("/"):
        await _send(chat_id, "دستور ناشناخته. /help بزن.")
    elif chat_id in STATE["wizard"]:
        await wiz_text(chat_id, text)
    elif len(text) >= 2:
        q = text.lower()
        res = [c for c in links().values() if q in str(c.get("label")).lower() or q in c["uuid"].lower()][:8]
        if res:
            rows = [[{"text": ("🟢 " if is_link_allowed(c) else "🔴 ") + c["label"], "callback_data": f"cfg:{c['uuid']}"}] for c in res]
            await _send(chat_id, f"🔎 {len(res)} نتیجه:", rows)
        else:
            await _send(chat_id, "چیزی پیدا نشد.")

async def cmd_backup(chat_id, mid=None):
    stamp = time.strftime("%Y%m%d-%H%M")
    fname = f"sukot-backup-{stamp}.json"
    raw = json.dumps(core.load_state(), ensure_ascii=False, default=str).encode()
    await _upload_doc(chat_id, fname, raw, f"💾 بکاپ {APP_NAME} · {stamp}")

async def _poll_loop():
    offset = 0
    while True:
        try:
            r = await _call("getUpdates", offset=offset, timeout=30,
                            allowed_updates=["message", "callback_query", "channel_post"])
            if r.get("ok"):
                for up in r.get("result") or []:
                    offset = max(offset, (up.get("update_id") or 0) + 1)
                    asyncio.ensure_future(_handle_update(up))
            else:
                if r.get("error_code") == 409:
                    try:
                        await _call("deleteWebhook", drop_pending_updates=False)
                    except Exception:
                        pass
                await asyncio.sleep(3)
        except Exception:
            await asyncio.sleep(5)

async def _register_commands():
    cmds = [
        {"command": "start", "description": "منوی اصلی"},
        {"command": "new", "description": "ساخت سریع کانفیگ"},
        {"command": "find", "description": "جستجوی کانفیگ"},
        {"command": "online", "description": "کاربران آنلاین"},
        {"command": "top", "description": "پرمصرف‌ترین‌ها"},
        {"command": "expiring", "description": "نزدیک انقضا"},
        {"command": "server", "description": "وضعیت سرور"},
        {"command": "bulk", "description": "ساخت دسته‌ای"},
        {"command": "backup", "description": "بکاپ"},
        {"command": "seturl", "description": "ثبت آدرس پنل"},
        {"command": "alerts", "description": "هشدارها"},
        {"command": "id", "description": "شناسه‌ی عددی من"},
    ]
    await _call("setMyCommands", commands=cmds)
    if core.public_url() and TOKEN:
        await _call("setChatMenuButton", menu_button={"type": "web_app",
                    "text": "🚀 مینی‌اپ", "web_app": {"url": core.public_url().rstrip("/") + "/app"}})

async def start_bot():
    """Start polling + alerts. No-op without token."""
    global TASK
    if not TOKEN:
        return False
    if TASK and not TASK.done():
        return True
    await _register_commands()
    TASK = asyncio.ensure_future(_poll_loop())
    asyncio.ensure_future(_alerts_loop())
    print(f"sukot-bot: polling started ({len(ADMIN_IDS)} admin id(s) from env)")
    return True

async def stop_bot():
    global TASK
    if TASK:
        TASK.cancel()
        TASK = None
