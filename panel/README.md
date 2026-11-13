# SUKOT Panel — پنل مدیریت VPN نسل جدید

پنل تحت وب + ربات تلگرام برای فروش و مدیریت کانفیگ‌های VLESS/XHTTP — نسخه‌ی کاملاً بازطراحی‌شده با برند **SUKOT**، آماده‌ی اجرا روی **Shiprr** (و هر PaaS دیگر مثل Railway).

> 🔗 کانال رسمی: https://t.me/SUKOT1344  ·  پشتیبانی: @SUKOT1344

---

## ✨ امکانات

| بخش | امکانات |
|---|---|
| **پنل وب** | داشبورد زنده (CPU/RAM/دیسک/شبکه + نمودار)، اینباندها، ساخت کلاینت، دسته‌بندی‌ها، گروه‌های ساب، گزارش‌ها با خروجی CSV، نودها، سرورهای VPS، پروکسی تلگرام، ادمین‌ها با مجوز تفکیکی، لاگ فعالیت‌ها، مرکز پیام‌ها، استودیو ظاهر (تغییر رنگ و پوسته از داخل پنل) |
| **موتور اتصال** | VLESS + WebSocket (`/ws/{uuid}`)، XHTTP (packet-up / stream-up)، VLESS + TCP خام، توکن‌باکت محدودیت سرعت، سقف IP هم‌زمان، سقف اتصال، خروجی از طریق پروکسی SOCKS/HTTP |
| **اشتراک** | لینک ساب استاندارد (`/sub/{uuid}`) با هدر `subscription-userinfo`، پورتال مشتری با گیج مصرف و QR آفلاین، گروه ساب با رمز اختیاری، صفحه اطلاعات، دیپ‌لینک اپ‌ها (Hiddify/v2rayNG/Streisand/Shadowrocket/sing-box) |
| **ربات تلگرام** | ساخت سریع و پیشرفته (۹ مرحله‌ای)، لیست/ویرایش/حذف، لینک + QR، گروه ساب، بکاپ، بیلک (ساخت دسته‌ای)، هشدار انقضا و حجم، مینی‌اپ تلگرام |
| **زیرساخت** | نودهای پنل‌به‌پنل با توکن، ثبت سرور VPS + اسکن پورت + اسکن SNI + خروجی Xray/WireGuard و اسکریپت نصب خودکار، پروکسی MTProto تلگرام با secret امن (dd·padded) و اشتراک پورت |
| **پایداری** | ذخیره JSON محلی + آینه‌سازی خودکار روی Postgres (برای هاست‌های بدون دیسک دائمی)، Keep-alive خودکار، بکاپ JSON کامل |

## 🚀 اجرا روی Shiprr (قدم‌به‌قدم)

1. کد را در یک ریپوی GitHub/GitLab بگذار (یا در Shiprr آپلود کن).
2. در Shiprr یک اپ جدید بساز و ریپو را وصل کن. Shiprr خودش `Dockerfile` را تشخیص می‌دهد.
3. در **Settings → Environment Variables** این متغیرها را بگذار:

```
ADMIN_USERNAME=Sukot
ADMIN_PASSWORD=Sukot
SECRET_KEY=یک-رشته-تصادفی-طولانی
PUBLIC_BASE_URL=https://YOUR-APP.shiprr.app
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
TELEGRAM_BOT_TOKEN=123456:ABC...        (اختیاری)
TELEGRAM_ADMIN_IDS=111111,222222        (اختیاری)
```

> **DATABASE_URL**: یک Postgres رایگان از [neon.tech](https://neon.tech) یا [supabase.com](https://supabase.com) بساز و Connection string را اینجا بگذار — بدون آن، بعد از هر ری‌استارت داده‌ها پاک می‌شود (دیسک Shiprr موقتی است).

4. Deploy بزن. آدرس عمومی اپ را در `PUBLIC_BASE_URL` بگذار (برای ساخت لینک ساب).
5. بعد از بالا آمدن، با `ADMIN_USERNAME` / `ADMIN_PASSWORD` وارد `/login` شو (پیش‌فرض: **Sukot / Sukot**).

### نکته‌های مهم

- روی Shiprr فقط پورت 443 (TLS) از بیرون باز است؛ لینک‌ها خودکار روی `security=tls` و `port=443` ساخته می‌شوند (`SUKOT_TLS=1`, `SUKOT_FORCE_PORT=443`).
- پنل همیشه با `python app.py` اجرا شود تا پروکسی تلگرام روی همان پورت سوار شود (تک‌پورتی).
- رله‌ی TCP خام (`TCP_LISTEN_PORT=6543`) روی PaaS بدون پورت TCP اضافه، فقط لینک می‌سازد و ترافیک رد نمی‌کند — روی VPS واقعی کار می‌کند.
- برای پروکسی تلگرام: از صفحه «پروکسی تلگرام» دکمه «خودکار» را بزن. اگر Shiprr فقط HTTP عبور دهد، خودتست داخل همان صفحه هشدار می‌دهد.

## 🖥 اجرای محلی

```bash
pip install -r requirements.txt
python app.py            # http://localhost:8000
```

پیش‌فرض ورود: **Sukot / Sukot** (بلافاصله از تنظیمات عوضش کن).

## 🎨 شخصی‌سازی ظاهر

از **تنظیمات → استودیو ظاهر** داخل خود پنل:
- پوسته تیره/روشن، ۹ رنگ اصلی آماده + ذخیره خودکار در مرورگر
- اندازه متن، گردی گوشه‌ها، انیمیشن‌ها، هاله نورانی

برای تغییر رنگ پیش‌فرض کل پنل، در `ui/theme.py` مقدارهای `--accent` / `--accent-rgb` را عوض کن.

## 📁 ساختار کد

```
app.py          اجراکننده (uvicorn + mux پروکسی تلگرام)
main.py         اپ FastAPI، همه‌ی روت‌ها و APIها
core.py         تنظیمات، نشست‌ها، مجوزها، لاگ، ابزارها
links.py        موتور کانفیگ‌ها و لینک‌های اشتراک
relays.py       رله VLESS-WS + XHTTP
tcp_relay.py    رله TCP خام
outbound.py     استخر پروکسی خروجی (SOCKS/HTTP)
speed_limit.py  محدودیت سرعت توکن‌باکت
tg_proxy.py     پروکسی MTProto تلگرام + SOCKS
nodes.py        نودهای پنل‌به‌پنل
vps_serv.py     سرورهای VPS، Xray/WireGuard، اسکنرها
operators.py    پریست اپراتورها (همراه اول، ایرانسل، ...)
persist_db.py   آینه‌سازی Postgres
keepalive.py    پینگ خودکار
sukot_bot.py    ربات تلگرام
ui/             صفحات پنل، لاگین، پورتال مشتری، مینی‌اپ
app_assets/     فونت، آیکون‌ها، QR lib، تصاویر برند
```

— ساخته‌شده برای SUKOT · https://t.me/SUKOT1344
