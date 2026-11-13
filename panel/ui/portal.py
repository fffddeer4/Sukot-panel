# ui/portal.py — customer-facing pages: subscription portal, group portal, info page
import html as _html
from ui.theme import page_head, toast_js, APP, LOGO, AVATAR

def esc(s): return _html.escape(str(s or ""))

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
def fa(x): return str(x).translate(_FA)
def hb(n):
    try: n = float(n or 0)
    except Exception: n = 0.0
    if not n: return "۰ B"
    for u in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024 or u == "PB":
            s = f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
            return s.translate(_FA)
        n /= 1024
    return "۰ B"

PROTO_LABELS = {
    "vless-ws": "VLESS + WebSocket", "vless-tcp": "VLESS + TCP",
    "xhttp-packet-up": "XHTTP packet-up", "xhttp-stream-up": "XHTTP stream-up",
    "xhttp-stream-one": "XHTTP stream-one", "vmess-ws": "VMess + WebSocket",
    "trojan-ws": "Trojan + WebSocket", "manual": "لینک دستی",
}
OP_LABELS = {"mci": "همراه اول", "irancell": "ایرانسل", "tci": "مخابرات", "rightel": "رایتل"}

def _common_css() -> str:
    return """
body{min-height:100vh;display:flex;flex-direction:column;position:relative}
.bgfx{position:fixed;inset:0;z-index:-1;overflow:hidden;pointer-events:none}
.bgfx .orb{position:absolute;border-radius:50%;filter:blur(80px);opacity:.4;animation:drift 18s ease-in-out infinite alternate}
.bgfx .orb.b1{width:480px;height:480px;background:rgba(var(--accent-rgb),.30);top:-150px;inset-inline-end:-120px}
.bgfx .orb.b2{width:380px;height:380px;background:rgba(var(--accent-rgb),.18);bottom:-120px;inset-inline-start:-100px;animation-delay:-8s}
@keyframes drift{from{transform:translate3d(0,0,0) scale(1)}to{transform:translate3d(-34px,26px,0) scale(1.12)}}
nav.top{position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:12px;padding:13px 20px;
  background:rgba(12,8,9,.7);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}
[data-theme="light"] nav.top{background:rgba(255,255,255,.78)}
nav.top .b{display:flex;align-items:center;gap:10px}
nav.top img{width:40px;height:40px;border-radius:50%;object-fit:cover;border:2px solid rgba(var(--accent-rgb),.55);box-shadow:0 0 14px rgba(var(--accent-rgb),.3)}
nav.top b{letter-spacing:.18em;font-size:1.02em}
nav.top small{display:block;color:var(--sub2);font-size:.62em;letter-spacing:.3em;font-weight:800}
nav.top .row{margin-inline-start:auto;gap:8px}
main{flex:1;width:min(980px,100%);margin:0 auto;padding:22px 18px 40px}
footer{text-align:center;color:var(--sub2);font-size:.78em;letter-spacing:.24em;padding:18px;font-weight:800;border-top:1px solid var(--line)}
.hero{display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.gauge{--p:0;width:128px;height:128px;border-radius:50%;flex:none;position:relative;
  background:conic-gradient(rgba(var(--accent-rgb),1) calc(var(--p)*1%),var(--line2) 0);
  display:flex;align-items:center;justify-content:center;box-shadow:0 0 34px rgba(var(--accent-rgb),.18)}
.gauge::before{content:'';position:absolute;inset:10px;border-radius:50%;background:var(--panel-solid)}
.gauge b{position:relative;z-index:2;font-size:1.2em}
.hero h1{font-size:1.4em}
.minis{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.mstat{background:var(--panel2);border:1px solid var(--line);border-radius:13px;padding:9px 14px;text-align:center;flex:1;min-width:110px}
.mstat b{display:block;font-size:1.06em}
.mstat span{color:var(--sub2);font-size:.74em}
.apps{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.app{display:flex;flex-direction:column;align-items:center;gap:7px;padding:13px 8px;border-radius:15px;border:1px solid var(--line2);
  background:var(--panel2);cursor:pointer;transition:.16s;color:var(--text);font-weight:700;font-size:.86em;position:relative}
.app:hover{border-color:rgba(var(--accent-rgb),.55);transform:translateY(-2px)}
.app .ti{font-size:24px;color:var(--accent)}
.app .rec{position:absolute;top:-10px;inset-inline-end:-4px}
.steps{counter-reset:s;display:flex;flex-direction:column;gap:11px}
.step{display:flex;gap:13px;align-items:flex-start}
.step::before{counter-increment:s;content:counter(s);flex:none;width:30px;height:30px;border-radius:11px;display:flex;align-items:center;justify-content:center;
  background:rgba(var(--accent-rgb),.14);color:var(--accent);font-weight:800;font-size:.9em}
.opc{border-inline-start:3px solid var(--line2)}
.opc.mci{border-inline-start-color:#38bdf8}.opc.irancell{border-inline-start-color:#facc15}
.opc.tci{border-inline-start-color:#a78bfa}.opc.rightel{border-inline-start-color:#fb7185}
.cfgcard{margin-bottom:12px}
.qrbox{display:flex;justify-content:center;padding:10px;background:#fff;border-radius:14px;margin:12px 0}
/* ---- detail-rich additions ---- */
.card h3{letter-spacing:0}
.detailgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:9px}
.dcell{display:flex;align-items:center;justify-content:space-between;gap:9px;background:var(--panel2);
  border:1px solid var(--line);border-radius:12px;padding:10px 13px;transition:.16s}
.dcell:hover{border-color:rgba(var(--accent-rgb),.45)}
.dcell .k{color:var(--sub);font-size:.78em;display:flex;align-items:center;gap:7px;flex:none}
.dcell .k .ti{color:var(--accent);font-size:15px}
.dcell .v{font-weight:800;font-size:.88em;text-align:left;word-break:break-all}
.dcell .v.mono{font-family:monospace;direction:ltr;unicode-bidi:embed;font-size:.8em}
.uuidrow{display:flex;gap:8px;align-items:center;background:rgba(0,0,0,.25);border:1px solid var(--line2);
  border-radius:12px;padding:9px 12px;direction:ltr}
[data-theme="light"] .uuidrow{background:#fff}
.uuidrow code{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.82em;font-family:monospace}
.appdl{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}
.dlap{display:flex;flex-direction:column;gap:8px;background:var(--panel2);border:1px solid var(--line2);
  border-radius:15px;padding:14px;transition:.18s;position:relative}
.dlap:hover{border-color:rgba(var(--accent-rgb),.5);transform:translateY(-3px);box-shadow:0 12px 26px rgba(0,0,0,.3)}
.dlap .hd{display:flex;align-items:center;gap:9px}
.dlap .hd .ti{font-size:22px;color:var(--accent)}
.dlap .hd b{font-size:.95em}
.dlap .pl{font-size:.7em;color:var(--sub2);letter-spacing:.06em}
.dlap .desc{font-size:.76em;color:var(--sub);line-height:1.7;flex:1}
.dlap .btn{justify-content:center}
.chiprow{display:flex;gap:7px;flex-wrap:wrap;align-items:center;margin-top:8px}
.bigqr{padding:16px;background:#fff;border-radius:18px;margin:12px auto;max-width:270px;box-shadow:0 14px 34px rgba(0,0,0,.28)}
.refreshnote{display:flex;gap:8px;align-items:center;font-size:.78em;color:var(--sub2);margin-top:8px}
"""

FX = r"""
(function(){
  const h=document.documentElement;
  const saved=localStorage.getItem('sk_portal_theme');
  if(saved)h.dataset.theme=saved; else if(matchMedia('(prefers-color-scheme: light)').matches)h.dataset.theme='light';
  window.tgl=function(){h.dataset.theme=h.dataset.theme==='light'?'dark':'light';localStorage.setItem('sk_portal_theme',h.dataset.theme)};
})();
function fa(n){return String(n).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d])}
function hb(n){n=Number(n)||0;if(!n)return '۰ B';const u=['B','KB','MB','GB','TB','PB'];let i=0;while(Math.abs(n)>=1024&&i<u.length-1){n/=1024;i++}return fa(i?n.toFixed(1):n.toFixed(0))+' '+u[i]}
function cp(t){navigator.clipboard.writeText(t).then(()=>toast('کپی شد ✔','ok'),()=>toast('کپی نشد','err'))}
function qrSrc(text){
  try{
    if(typeof qrcode==='function'){
      const q=qrcode(0,'M');q.addData(String(text||''));q.make();
      return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(q.createSvgTag(4,4));
    }
  }catch(e){}
  return 'https://api.qrserver.com/v1/create-qr-code/?size=210x210&data='+encodeURIComponent(String(text||''));
}
function countdown(exp){
  const el=document.getElementById('timeleft'); if(!el) return;
  function tick(){const d=new Date(exp)-Date.now();
    if(d<=0){el.textContent='منقضی شده';return}
    const days=Math.floor(d/86400000),hrs=Math.floor(d%86400000/3600000),mins=Math.floor(d%3600000/60000);
    el.textContent=fa((days?days+' روز ':'')+(hrs?hrs+' ساعت ':'')+mins+' دقیقه');}
  tick();setInterval(tick,30000);
}
function toggleUuid(){
  const full=document.getElementById('uuidfull')?.textContent||'';
  const el=document.getElementById('uuidview');
  const btn=document.getElementById('uuidbtn');
  if(!el) return;
  if(el.dataset.shown==='1'){ el.textContent=full.slice(0,8)+' ••••••••••••'; el.dataset.shown='0'; btn.textContent='نمایش کامل'; }
  else{ el.textContent=full; el.dataset.shown='1'; btn.textContent='پنهان کن'; }
}
""" + toast_js()

def _nav(info_url: str, sub_url: str) -> str:
    return f"""
<nav class="top">
  <div class="b"><img src="{LOGO}" alt="SUKOT"><span><b>SUKOT</b><small>SUBSCRIPTION PORTAL</small></span></div>
  <div class="row">
    <button class="iconbtn" onclick="tgl()"><span class="ti ti-sun-moon"></span></button>
    <a class="btn sm soft" href="{info_url}"><span class="ti ti-info-circle"></span> اطلاعات سرویس</a>
    <a class="btn sm" href="{sub_url}"><span class="ti ti-refresh"></span> بروزرسانی</a>
  </div>
</nav>"""

def _footer() -> str:
    return '<footer>SUKOT · SUBSCRIPTION · v3.0</footer>'

def _apps_script(sub_url: str) -> str:
    import urllib.parse
    enc = urllib.parse.quote(sub_url, safe="")
    return f"""
const isIOS=/iphone|ipad/i.test(navigator.userAgent);
const apps=[
 ["Hiddify","ti-world","hiddify://import/{enc}",true],
 ["v2rayNG","ti-brand-android","v2rayng://install-sub?url={enc}",!isIOS],
 ["Streisand","ti-brand-apple","streisand://import/{enc}",isIOS],
 ["Shadowrocket","ti-device-mobile","sub://{enc}",isIOS],
 ["sing-box","ti-box","sing-box://import-remote-profile?url={enc}",false]];
document.getElementById('apps').innerHTML=apps.map(a=>`<a class="app" href="${{a[2]}}"><span class="ti ${{a[1]}}"></span>${{a[0]}}${{a[3]?'<span class="rec chip">پیشنهادی</span>':''}}</a>`).join('');
"""

# real download links for VPN client apps
_DL_APPS = [
    ("Hiddify", "همه‌پلتفرم (اندروید · iOS · ویندوز · مک)", "ti-world",
     "ساده‌ترین اپ برای شروع؛ ساب را مستقیم ایمپورت می‌کند.", "https://github.com/hiddify/hiddify-app/releases", "https://hiddify.app"),
    ("v2rayNG", "اندروید", "ti-brand-android",
     "محبوب‌ترین کلاینت اندروید برای VLESS و XHTTP.", "https://github.com/2dust/v2rayNG/releases", "https://play.google.com/store/apps/details?id=com.v2ray.app"),
    ("sing-box", "اندروید · iOS", "ti-box",
     "موتور مدرن با پشتیبانی کامل از پروتکل‌های جدید.", "https://github.com/SagerNet/sing-box/releases", "https://play.google.com/store/apps/details?id=io.nekohasekai.sagernet"),
    ("Streisand", "iOS · آیفون و آیپد", "ti-brand-apple",
     "بهترین انتخاب آیفون؛ ایمپورت ساب و QR.", "https://apps.apple.com/us/app/streisand/id6490262373", ""),
    ("Shadowrocket", "iOS", "ti-device-mobile",
     "سبک و سریع برای آیفون (نیاز به اپ‌استور خارجی).", "https://apps.apple.com/us/app/shadowrocket/id932747118", ""),
    ("NekoBox", "اندروید", "ti-router",
     "کلاینت متن‌باز با تنظیمات پیشرفته.", "https://github.com/MatsuriDayo/NekoBoxForAndroid/releases", ""),
]

def _downloads_html() -> str:
    cards = []
    for name, plat, icon, desc, url1, url2 in _DL_APPS:
        btns = f'<a class="btn sm" href="{url1}" target="_blank" rel="noopener"><span class="ti ti-download"></span> دانلود مستقیم</a>'
        if url2:
            btns += f'<a class="btn ghost sm" href="{url2}" target="_blank" rel="noopener">استور / سایت</a>'
        cards.append(f"""
    <div class="dlap">
      <div class="hd"><span class="ti {icon}"></span><div><b>{name}</b><div class="pl">{plat}</div></div></div>
      <div class="desc">{desc}</div>
      <div class="wrapgap" style="gap:7px">{btns}</div>
    </div>""")
    return "".join(cards)

def subscription(d: dict, support: str) -> str:
    name = d.get("name") or "config"
    used, limit = d.get("used") or 0, d.get("limit") or 0
    pct = min(100.0, (used * 100.0 / limit)) if limit else 0.0
    color = "var(--good)" if pct < 70 else "var(--warn)" if pct < 90 else "var(--bad)"
    remain = max(0, (limit or 0) - used)
    active = bool(d.get("active"))
    proto_label = PROTO_LABELS.get(d.get("protocol") or "", d.get("protocol") or "—")
    op = (d.get("operator") or "").lower()
    opn = OP_LABELS.get(op, "")
    ip_cur, ip_max = d.get("ip_cur") or 0, d.get("ip_max") or 0
    online = d.get("online") or 0
    speed = d.get("speed_mbit") or 0
    support_clean = (support or "SUKOT1344").lstrip("@")
    uuid = d.get("uid") or ""
    import urllib.parse
    sub_enc = urllib.parse.quote(d.get("sub_url") or "", safe="")
    hist_svg = ""
    if d.get("usage_hist") and len(d["usage_hist"]) >= 2:
        lim = limit or max(max(d["usage_hist"]), 1)
        w = 560
        pts = " ".join(f"{int(i*(w/(len(d['usage_hist'])-1)))},{90-int((min(h,lim)/lim)*84)}"
                       for i, h in enumerate(d["usage_hist"][-24:]))
        hist_svg = f'''<div class="card" style="margin-top:14px"><h3><span class="ti ti-chart-histogram"></span> روند مصرف</h3>
        <svg viewBox="0 0 {w} 92" width="100%" height="92" preserveAspectRatio="none">
        <polyline fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" points="{pts}"/></svg></div>'''
    ip_chip = f'<span class="chip gray"><span class="ti ti-device-mobile"></span> IP: {fa(ip_cur)}/{fa(ip_max) if ip_max else "∞"}</span>' if ip_max else ""
    dl = _downloads_html()
    return page_head(f"{esc(name)} · اشتراک SUKOT", extra_css=_common_css()) + f"""
<body>
<script src="/assets/qr.js"></script>
<script>{FX}</script>
<div class="bgfx"><div class="orb b1"></div><div class="orb b2"></div></div>
{_nav(d.get('info_url') or '#', d.get('sub_url') or '#')}
<main>
  <div class="card pad-lg hero" style="margin-bottom:14px">
    <div class="gauge" style="--p:{pct:.0f}"><b style="color:{color}">{fa(f'{pct:.0f}')}٪</b></div>
    <div style="flex:1;min-width:230px">
      <div class="row"><h1>{esc(name)}</h1><span class="chip {'good' if active else 'bad'}">
        <span class="dot {'pulse' if active else 'bad'}"></span> {'فعال' if active else 'غیرفعال / تمام‌شده'}</span></div>
      <div class="chiprow">
        <span class="chip gray"><span class="ti ti-protocol"></span> {esc(proto_label)}</span>
        <span class="chip good"><span class="ti ti-plug-connected"></span> {fa(online)} نفر آنلاین</span>
        {f'<span class="optag {esc(op)}">{esc(opn)}</span>' if opn else ''}
        {ip_chip}
        <span class="chip gray"><span class="ti ti-stack-2"></span> {fa(d.get('config_count') or 1)} کانفیگ در ساب</span>
      </div>
      <div class="minis">
        <div class="mstat"><b>{hb(used)}</b><span>مصرف‌شده</span></div>
        <div class="mstat"><b>{'∞' if not limit else hb(remain)}</b><span>باقی‌مانده</span></div>
        <div class="mstat"><b id="timeleft">—</b><span>زمان باقی‌مانده</span></div>
        <div class="mstat"><b>{fa(speed) if speed else '∞'}</b><span>محدودیت سرعت (Mbps)</span></div>
        <div class="mstat"><b>{fa(ip_cur)}/{fa(ip_max) if ip_max else '∞'}</b><span>دستگاه متصل</span></div>
      </div>
    </div>
  </div>
  {hist_svg}
  <div class="card" style="margin-top:14px">
    <h3><span class="ti ti-link"></span> لینک اشتراک</h3>
    <div class="linkline"><code>{esc(d.get('sub_url'))}</code><button class="btn sm" onclick="cp(`{esc(d.get('sub_url'))}`)"><span class="ti ti-copy"></span> کپی</button></div>
    <div class="bigqr" id="qr"></div>
    <p class="small mut" style="margin:6px 0 0;text-align:center">QR را با اپ اسکن کن یا لینک را کپی و «Update subscription» بزن.</p>
    <div class="refreshnote"><span class="ti ti-refresh"></span> اشتراک هر ۱۲ ساعت خودکار آپدیت می‌شود؛ بعد از شارژ یا تمدید، اپ را دستی آپدیت هم بزن.</div>
  </div>
  <div class="card" style="margin-top:14px">
    <h3><span class="ti ti-details"></span> جزئیات کامل کانفیگ</h3>
    <div class="detailgrid">
      <div class="dcell"><span class="k"><span class="ti ti-protocol"></span> پروتکل</span><span class="v">{esc(proto_label)}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-server"></span> آدرس سرور</span><span class="v mono">{esc(d.get('host'))}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-plug-connected"></span> پورت</span><span class="v mono">{fa(d.get('port'))}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-shield-lock"></span> امنیت</span><span class="v">{esc(str(d.get('security') or '—').upper())}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-world"></span> SNI</span><span class="v mono">{esc(d.get('sni'))}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-route"></span> شبکه</span><span class="v">{esc(str(d.get('network') or '—').upper())}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-api"></span> مسیر (Path)</span><span class="v mono">{esc(d.get('path'))}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-fingerprint"></span> اثر انگشت</span><span class="v">{esc(d.get('fingerprint'))}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-stack"></span> ALPN</span><span class="v mono">{esc(d.get('alpn'))}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-user"></span> اپراتور پیشنهادی</span><span class="v">{esc(opn or 'همه اپراتورها')}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-calendar"></span> تاریخ ساخت</span><span class="v">{esc(d.get('created_at') or '—')}</span></div>
      <div class="dcell"><span class="k"><span class="ti ti-folders"></span> کلاینت‌های زیرمجموعه</span><span class="v">{fa(d.get('clients_count') or 0)}</span></div>
    </div>
    <label class="lb">شناسه (UUID)</label>
    <div class="uuidrow"><code id="uuidview" data-shown="0">{esc(str(uuid)[:8])} ••••••••••••</code>
      <button class="btn sm ghost" id="uuidbtn" onclick="toggleUuid()">نمایش کامل</button>
      <button class="btn sm" onclick="cp(document.getElementById('uuidfull').textContent)"><span class="ti ti-copy"></span></button></div>
    <code id="uuidfull" style="display:none">{esc(str(uuid))}</code>
    {f'<label class="lb">یادداشت مدیر</label><div class="dcell" style="margin-top:0"><span class="k"><span class="ti ti-note"></span> یادداشت</span><span class="v">{esc(d.get("note"))}</span></div>' if d.get('note') else ''}
  </div>
  <div class="card" style="margin-top:14px">
    <h3><span class="ti ti-link"></span> لینک اتصال خام</h3>
    <p class="small mut" style="margin:0 0 9px">اگر اپت لینک ساب را نگرفت، این لینک را مستقیم ایمپورت کن:</p>
    <div class="uuidrow"><code id="rawlink">{esc(d.get('link_uri'))}</code>
      <button class="btn sm" onclick="cp(document.getElementById('rawlink').textContent)"><span class="ti ti-copy"></span></button></div>
  </div>
  <div class="card" style="margin-top:14px">
    <h3><span class="ti ti-rocket"></span> اتصال سریع (ایمپورت خودکار)</h3>
    <div class="apps" id="apps"></div>
  </div>
  <div class="card" style="margin-top:14px">
    <h3><span class="ti ti-download"></span> دانلود برنامه‌های وی‌پی‌ان</h3>
    <p class="small mut" style="margin:0 0 12px">هر کدام از این اپ‌ها با لینک ساب SUKOT کار می‌کند؛ برای اندروید Hiddify یا v2rayNG، برای آیفون Streisand پیشنهاد می‌شود.</p>
    <div class="appdl">{dl}</div>
  </div>
  <div class="grid g2" style="margin-top:14px">
    <div class="card">
      <h3><span class="ti ti-note"></span> راهنمای اتصال</h3>
      <div class="steps">
        <div class="step"><span>یکی از اپ‌های بالا را نصب کن (اندروید: Hiddify یا v2rayNG — آیفون: Streisand یا Shadowrocket).</span></div>
        <div class="step"><span>لینک اشتراک را کپی کن؛ در اپ گزینه Add Subscription / ایمپورت از کلیپ‌بورد را بزن.</span></div>
        <div class="step"><span>اشتراک را آپدیت کن تا کانفیگ‌ها بیاید؛ کانفیگ متناسب با اپراتورت را انتخاب و وصل شو.</span></div>
        <div class="step"><span>اگر وصل نشد: یک بار حالت هواپیما را روشن/خاموش کن یا اپ را عوض کن؛ مصرف و وضعیت از همین صفحه قابل مشاهده است.</span></div>
      </div>
    </div>
    <div class="card">
      <h3><span class="ti ti-headset"></span> پشتیبانی آنلاین SUKOT</h3>
      <p class="small mut" style="line-height:1.9">برای تمدید اشتراک، افزایش حجم یا هر مشکل در اتصال، مستقیم در تلگرام پیام بده.</p>
      <a class="btn" href="https://t.me/{support_clean}" target="_blank" rel="noopener"><span class="ti ti-brand-telegram"></span> گفتگو با پشتیبان SUKOT</a>
      <div class="mt"><a class="btn ghost sm" href="https://t.me/SUKOT1344" target="_blank"><span class="ti ti-speakerphone"></span> کانال رسمی SUKOT</a></div>
      <div class="mt small mut2">پاسخگویی معمولاً کمتر از چند دقیقه است.</div>
    </div>
  </div>
</main>
{_footer()}
<script>
document.getElementById('qr').innerHTML='<img src="'+qrSrc(`{esc(d.get('sub_url'))}`)+'" width="230" alt="QR">';
{_apps_script(d.get('sub_url') or '')}
countdown('{esc(d.get('expires_at') or "")}');
</script>
</body>
</html>"""

# ---------------------------------------------------------------- group portal
def group(key: str, name: str, items: list, has_pw: bool, support: str) -> str:
    support_clean = (support or "SUKOT1344").lstrip("@")
    cards = []
    for c in items:
        op = (c.get("operator") or "").lower()
        opn = OP_LABELS.get(op, "")
        lim, used = c.get("limit_bytes") or 0, c.get("used_bytes") or 0
        pct = min(100.0, used * 100 / lim) if lim else 0
        cards.append(f"""
  <div class="card cfgcard opc {esc(op)}">
    <div class="spread"><h3 style="margin:0">{esc(c.get('label'))}</h3>
    <span class="chip {'good' if c.get('active') else 'bad'}">{'فعال' if c.get('active') else 'غیرفعال'}</span></div>
    <div class="wrapgap" style="margin-top:7px">
      <span class="chip gray">{esc(c.get('protocol'))}</span>
      {f'<span class="optag {esc(op)}">{esc(opn)}</span>' if opn else ''}
      <span class="small mut">{hb(used)} / {'∞' if not lim else hb(lim)}</span>
      <span class="small mut">·</span><span class="small mut">{fa(f'{pct:.0f}')}٪</span>
    </div>
    <div class="qrbox" id="qr-{esc(c.get('key'))}"></div>
    <div class="wrapgap">
      <button class="btn sm" onclick="cp(document.getElementById('cf-{esc(c.get('key'))}').textContent)"><span class="ti ti-copy"></span> کانفیگ</button>
      <a class="btn sm soft" href="{esc(c.get('sub'))}"><span class="ti ti-qrcode"></span> ساب</a>
    </div>
    <pre id="cf-{esc(c.get('key'))}" class="mono small" style="white-space:pre-wrap;word-break:break-all;max-height:92px;overflow:hidden;margin:9px 0 0;color:var(--sub);background:rgba(0,0,0,.22);padding:9px 11px;border-radius:11px;border:1px solid var(--line)">{esc(c.get('link'))}</pre>
  </div>""")
    lock_html = f"""
  <div class="card lockbox pad-lg" id="lockCard">
    <h3><span class="ti ti-lock"></span> اشتراک با رمز محافظت می‌شود</h3>
    <p class="small mut">رمز را از مدیر سرویس بگیر و این‌جا وارد کن.</p>
    <div class="row" style="justify-content:center">
      <input class="inp" id="pw" dir="ltr" placeholder="رمز اشتراک" style="max-width:240px">
      <button class="btn" onclick="unlock()">نمایش</button>
    </div>
    <div id="lockErr" class="small" style="color:var(--bad);margin-top:10px"></div>
  </div>"""
    head_card = (f'<div class="card pad-lg" style="margin-bottom:14px"><h1>{esc(name)}</h1>'
                 f'<p class="small mut">اشتراک ترکیبی SUKOT — همه کانفیگ‌ها یک‌جا</p></div>') if name else ''
    body_cards = f'<div id="cards" style="display:none">{head_card}{"".join(cards)}</div>'
    unlock_js = """
async function unlock(){
  const pw=document.getElementById('pw').value;
  const r=await fetch(`?pw=${encodeURIComponent(pw)}`);
  const j=await r.json().catch(()=>({}));
  if(j.ok){document.getElementById('lockCard').style.display='none';renderCards()}
  else document.getElementById('lockErr').textContent='رمز اشتباه است';
}
""" if has_pw else "renderCards();\n"
    qr_paint = "".join(f"""
  const el{i}=document.getElementById('qr-{esc(c.get("key"))}');
  if(el{i}) el{i}.innerHTML='<img src="'+qrSrc(document.getElementById('cf-{esc(c.get("key"))}').textContent)+'" width="150">';
""" for i, c in enumerate(items))
    return page_head(f"{esc(name) or 'اشتراک'} · SUKOT", extra_css=_common_css()) + f"""
<body>
<script src="/assets/qr.js"></script>
<script>{FX}</script>
<div class="bgfx"><div class="orb b1"></div><div class="orb b2"></div></div>
{_nav('#', '#')}
<main>
  {lock_html if has_pw else ''}
  {body_cards}
  <div class="card" style="margin-top:14px">
    <h3><span class="ti ti-headset"></span> پشتیبانی SUKOT</h3>
    <div class="wrapgap">
      <a class="btn" href="https://t.me/{support_clean}" target="_blank"><span class="ti ti-brand-telegram"></span> پشتیبانی</a>
      <a class="btn ghost" href="https://t.me/SUKOT1344" target="_blank"><span class="ti ti-speakerphone"></span> کانال SUKOT</a>
    </div>
  </div>
</main>
{_footer()}
<script>
function renderCards(){{document.getElementById('cards').style.display='block';paint()}}
{unlock_js}
function paint(){{{qr_paint}}}
</script>
</body>
</html>"""

# ---------------------------------------------------------------- info page
def info(uid: str, name: str, protocol: str, active: bool, used: int, limit: int,
         expires_at: str, ip_cur: int, ip_max: int, conn: int, fp: str,
         support: str, base: str) -> str:
    pct = min(100.0, (used * 100.0 / limit)) if limit else 0.0
    color = "var(--good)" if pct < 70 else "var(--warn)" if pct < 90 else "var(--bad)"
    support_clean = (support or "SUKOT1344").lstrip("@")
    return page_head(f"{esc(name)} · SUKOT Access", extra_css=_common_css()) + f"""
<body>
<script src="/assets/qr.js"></script>
<script>{FX}</script>
<div class="bgfx"><div class="orb b1"></div><div class="orb b2"></div></div>
<nav class="top">
  <div class="b"><img src="{LOGO}" alt="SUKOT"><span><b>SUKOT</b><small>SECURE CLIENT PORTAL</small></span></div>
  <div class="row"><button class="iconbtn" onclick="tgl()"><span class="ti ti-sun-moon"></span></button></div>
</nav>
<main>
  <div class="card pad-lg hero" style="margin-bottom:14px">
    <img src="{AVATAR}" alt="profile" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:2px solid rgba(var(--accent-rgb),.55);box-shadow:0 0 20px rgba(var(--accent-rgb),.3)">
    <div style="flex:1">
      <h1>{esc(name)}</h1>
      <div class="chips" style="display:flex;gap:7px;margin-top:8px;flex-wrap:wrap">
        <span class="chip {'good' if active else 'bad'}"><span class="dot {'pulse' if active else 'bad'}"></span>{'فعال' if active else 'غیرفعال'}</span>
        <span class="chip gray">{esc(protocol)}</span>
        <span class="chip gray">Fingerprint: {esc(fp or 'chrome')}</span>
      </div>
    </div>
  </div>
  <div class="grid g3">
    <div class="card"><h3><span class="ti ti-arrows-exchange"></span> مصرف</h3>
      <div class="mstat" style="border:0;background:none;padding:0"><b style="font-size:1.3em">{hb(used)}</b><span>از {('∞' if not limit else hb(limit))}</span></div>
      <div class="bar" style="margin-top:10px"><i style="width:{pct:.0f}%;background:{color}"></i></div></div>
    <div class="card"><h3><span class="ti ti-hourglass"></span> انقضا</h3><b style="font-size:1.2em">{esc(str(expires_at)[:10]) if expires_at else '∞ بدون انقضا'}</b>
      <div class="small mut mt" id="timeleft"></div></div>
    <div class="card"><h3><span class="ti ti-shield"></span> دسترسی</h3>
      <div class="mini-stat"><span class="mut">IP هم‌زمان</span><b>{fa(ip_cur)}/{fa(ip_max) if ip_max else '∞'}</b></div>
      <div class="mini-stat"><span class="mut">اتصال باز</span><b>{fa(conn)}</b></div></div>
  </div>
  <div class="card mt">
    <h3><span class="ti ti-details"></span> اطلاعات فنی</h3>
    <div class="mini-stat"><span class="mut">پروتکل</span><b>{esc(protocol)}</b></div>
    <div class="mini-stat"><span class="mut">سرور</span><b class="mono">{esc(base or '—')}</b></div>
    <div class="mini-stat"><span class="mut">پورت</span><b>443 (TLS)</b></div>
  </div>
  <div class="card mt">
    <h3><span class="ti ti-download"></span> کلاینت‌های پیشنهادی</h3>
    <div class="appdl" style="margin-top:4px">{_downloads_html()}</div>
  </div>
  <div class="card mt">
    <h3><span class="ti ti-headset"></span> پشتیبانی SUKOT</h3>
    <div class="wrapgap">
      <a class="btn" href="https://t.me/{support_clean}" target="_blank"><span class="ti ti-brand-telegram"></span> پشتیبانی آنلاین</a>
      <a class="btn ghost sm" href="https://t.me/SUKOT1344" target="_blank"><span class="ti ti-speakerphone"></span> کانال SUKOT</a>
    </div>
  </div>
  <p class="small mut2" style="text-align:center;margin-top:16px">اطلاعات اتصال فقط برای صاحب این لینک نمایش داده می‌شود.</p>
</main>
{_footer()}
<script>
countdown('{esc(str(expires_at) if expires_at else "")}');
</script>
</body>
</html>"""

# ---------------------------------------------------------------- mini app (Telegram)
def miniapp() -> str:
    return page_head("SUKOT · مینی‌اپ", extra_css=_common_css()) + "<script src='/assets/qr.js'></script><script>" + FX + "</script>" + r"""
<body>
<nav class="top">
  <div class="b"><img src="/assets/logo.webp" alt="SUKOT"><span><b>SUKOT</b><small>TELEGRAM MINI APP</small></span></div>
  <div class="row"><span class="chip" id="tgWho">—</span></div>
</nav>
<main>
  <div class="grid g3" id="stats"></div>
  <div class="card mt">
    <h3><span class="ti ti-rocket"></span> ساخت سریع</h3>
    <div class="wrapgap" id="presets"></div>
  </div>
  <div class="card mt">
    <h3><span class="ti ti-link"></span> کانفیگ‌ها</h3>
    <div class="feed" id="list" style="max-height:44vh"></div>
  </div>
</main>
<footer>SUKOT · MINI APP</footer>
<script src="/assets/qr.js"></script>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script>
const tg=window.Telegram&&window.Telegram.WebApp;
if(tg){tg.ready();tg.expand();try{tg.setHeaderColor('#0a0709')}catch(e){}}
async function api(path,opts){
  opts=opts||{};opts.headers=Object.assign({'Content-Type':'application/json'},opts.headers||{});
  const r=await fetch(path,opts);
  if(r.status===401){document.body.innerHTML='<div class="card lockbox"><h3>دسترسی فقط برای ادمین‌های ربات</h3></div>';throw 0}
  return r.json();}
function qrSrc(t){try{if(typeof qrcode==='function'){const q=qrcode(0,'M');q.addData(String(t||''));q.make();
  return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(q.createSvgTag(4,4))}}catch(e){}
  return 'https://api.qrserver.com/v1/create-qr-code/?size=210x210&data='+encodeURIComponent(t||'')}
function cp(t){navigator.clipboard.writeText(t).then(()=>toast('کپی شد ✔','ok'),()=>{});}
async function boot(){
  try{
    const me=await api('/api/tma/session',{method:'POST',body:JSON.stringify({init:tg?tg.initData:''})});
    document.getElementById('tgWho').textContent=me.username||'ادمین';
    await refresh();
  }catch(e){console.warn(e)}
}
async function refresh(){
  const st=await api('/api/tma/state');
  document.getElementById('stats').innerHTML=[
   ['کل کانفیگ‌ها','ti-link',st.total],['فعال','ti-circle-check',st.active],['ترافیک','ti-arrows-exchange',st.traffic_h]]
   .map(x=>`<div class="kpi"><div class="lab"><span class="ti ${x[1]}"></span>${x[0]}</div><div class="val">${x[2]}</div></div>`).join('');
  document.getElementById('presets').innerHTML=[[10,30],[30,30],[50,30],[0,0]]
   .map(p=>`<button class="btn sm" onclick="quick(${p[0]},${p[1]})">${p[0]||'♾'}گیگ · ${p[1]||'∞'}روز</button>`).join('');
  document.getElementById('list').innerHTML=(st.items||[]).map(c=>`
   <div class="fitem"><span class="ti ti-link"></span>
   <span><b>${c.label}</b><br><small class="mut">${c.used_h} / ${c.limit_h}</small></span>
   <span class="row" style="margin-inline-start:auto">
     <button class="iconbtn" onclick="cp('${c.sub_url}')"><span class="ti ti-copy"></span></button>
     <button class="iconbtn" onclick="qr('${c.uuid}')"><span class="ti ti-qrcode"></span></button>
     <button class="iconbtn" onclick="tglc('${c.uuid}',${c.active})"><span class="ti ${c.active?'ti-player-pause':'ti-player-play'}"></span></button>
   </span></div>`).join('')||'<div class="empty small">بدون کانفیگ</div>';
}
async function quick(gb,days){await api('/api/tma/create',{method:'POST',body:JSON.stringify({gb,days})});toast('ساخته شد ✔','ok');refresh()}
async function tglc(uid,a){await api('/api/tma/edit',{method:'POST',body:JSON.stringify({uuid:uid,active:!a})});refresh()}
function qr(uid){
  const c=(stCache.items||[]).find(x=>x.uuid===uid);if(!c)return;
  const w=window.open('','_blank');w.document.write('<title>QR</title><body style="display:grid;place-items:center;height:90vh;background:#111"><img src="'+qrSrc(c.sub_url)+'" width="320"></body>');
}
let stCache={};
const _r=refresh;refresh=async function(){stCache=await api('/api/tma/state');await _r()};
boot();
</script>
</body>
</html>"""
