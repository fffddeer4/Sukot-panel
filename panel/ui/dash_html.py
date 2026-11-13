# ui/dash_html.py — dashboard SPA body (all sections)
from ui.theme import LOGO, AVATAR, APP
def nav_items():
    return [
        ("sec", "نمای کلی"),
        ("overview", "داشبورد", "ti-dashboard"),
        ("sec", "سرویس‌ها"),
        ("links", "اینباندها", "ti-link", "nb-links"),
        ("clientmgr", "ساخت کلاینت", "ti-user-plus"),
        ("categories", "دسته‌بندی‌ها", "ti-category"),
        ("subgroups", "گروه‌های ساب", "ti-folders", "nb-subs"),
        ("sec", "زیرساخت"),
        ("nodes", "نودها", "ti-server-2"),
        ("vps", "سرورهای VPS", "ti-server-cog"),
        ("tgproxy", "پروکسی تلگرام", "ti-brand-telegram"),
        ("sec", "مدیریت"),
        ("reports", "گزارش‌ها", "ti-chart-histogram"),
        ("admins", "ادمین‌ها", "ti-users-group"),
        ("activity", "فعالیت‌ها", "ti-logs"),
        ("messages", "پیام‌ها", "ti-messages", "nb-errors"),
        ("settings", "تنظیمات", "ti-settings"),
    ]

def sidebar() -> str:
    out = ['''
<aside id="sidebar">
  <div class="brand">
    <img src="{logo}" alt="SUKOT">
    <div><b>SUKOT</b><small>CONTROL PANEL</small></div>
  </div>
  <nav class="nav" id="nav">'''.format(logo=LOGO)]
    for it in nav_items():
        if it[0] == "sec":
            out.append(f'<div class="sec">{it[1]}</div>')
        else:
            pid, label, icon = it[0], it[1], it[2]
            badge = f'<span class="nb" id="{it[3]}">0</span>' if len(it) > 3 else ""
            out.append(f'<a data-pg="{pid}" onclick="go(\'{pid}\')"><span class="ti {icon}"></span> {label} {badge}</a>')
    out.append(f'''
  </nav>
  <div class="sidefoot">
    <div class="uchip">
      <img src="{AVATAR}" alt="profile">
      <div><b id="whoName">مدیر</b><small id="whoRole">مالک پنل</small></div>
      <button class="iconbtn" onclick="logout()" title="خروج"><span class="ti ti-logout"></span></button>
    </div>
  </div>
</aside>
<div id="sideovl" onclick="toggleSide(false)"></div>''')
    return "\n".join(out)

def topbar() -> str:
    return f'''
<header id="topbar">
  <button class="iconbtn" id="burger" onclick="toggleSide()"><span class="ti ti-menu-2"></span></button>
  <div class="tt"><b id="pageTitle">داشبورد</b><small id="pageSub">وضعیت لحظه‌ای سرویس، کانفیگ‌ها و ربات</small></div>
  <div class="row" style="margin-inline-start:auto;gap:9px">
    <span class="chip tchip" id="tbClock" title="تاریخ و ساعت تهران"><span class="ti ti-clock"></span> <span>—</span></span>
    <span class="chip tchip tver"><span class="ti ti-shield-star"></span> SUKOT v3.0</span>
    <button class="sbtn" onclick="openCmd()"><span class="ti ti-search"></span><span>جستجوی سراسری</span><span class="kbd">Ctrl K</span></button>
    <button class="iconbtn" id="themeBtn" onclick="toggleTheme()" title="تغییر پوسته"><span class="ti ti-sun-moon"></span></button>
    <a class="iconbtn" href="https://t.me/SUKOT1344" target="_blank" title="کانال SUKOT"><span class="ti ti-brand-telegram"></span></a>
    <div class="tavatar" title="حساب مدیر"><img src="{AVATAR}" alt="مدیر"><i class="on"></i></div>
  </div>
</header>'''

PAGES = {
"overview": ("داشبورد", "وضعیت لحظه‌ای سرویس، کانفیگ‌ها و ربات", '''
<section class="pg" data-pg="overview" id="pg-overview">
  <div class="ov-grid">
    <div>
      <div class="pg-head">
        <span class="eyebrow"><span class="dot pulse"></span> مانیتور زنده سیستم</span>
        <h1>مرکز کنترل SUKOT</h1>
        <p>همه‌چیز سر جاشه؛ از اینباند تا کلاینت، از پروکسی تلگرام تا سرورهای VPS — از همین‌جا کنترل کن.</p>
      </div>
      <div class="hero hero3d">
        <div class="h-ring hr1"></div><div class="h-ring hr2"></div><div class="h-ring hr3"></div>
        <div class="h-glow"></div>
        <div class="h-content">
          <h2>خوش اومدی به مرکز کنترل SUKOT ⚡</h2>
          <p>ساخت کانفیگ، مدیریت اشتراک‌ها و مانیتورینگ لحظه‌ای؛ همه با چند کلیک. اگر تازه‌ای، از «ساخت سریع» شروع کن.</p>
          <div class="wrapgap">
            <button class="btn" onclick="go('clientmgr')"><span class="ti ti-user-plus"></span> ساخت کلاینت</button>
            <button class="btn gold" onclick="go('links')"><span class="ti ti-link"></span> اینباندها</button>
            <button class="btn ghost" onclick="go('vps')"><span class="ti ti-server-cog"></span> سرورهای VPS</button>
            <button class="btn ghost" onclick="go('tgproxy')"><span class="ti ti-brand-telegram"></span> پروکسی تلگرام</button>
          </div>
          <div class="chips">
            <span class="chip"><span class="ti ti-antenna-bars-5"></span> پریست اپراتورها</span>
            <span class="chip"><span class="ti ti-heartbeat"></span> مانیتورینگ زنده</span>
            <span class="chip"><span class="ti ti-shield-bolt"></span> VLESS + XHTTP زنده</span>
          </div>
        </div>
      </div>
      <div class="grid g6" id="ovBiz" style="margin-bottom:var(--density)"></div>
      <div class="grid g4" id="ovRes" style="margin-bottom:var(--density)"></div>
      <div class="grid g2">
        <div class="card">
          <h3><span class="ti ti-heartbeat"></span> سلامت سرویس</h3>
          <div class="row" style="gap:18px">
            <div class="gauge" id="healthGauge"><b id="healthVal">—</b></div>
            <div class="flexcol" style="flex:1">
              <div class="mini-stat"><span class="mut">وضعیت پنل</span><b class="st"><span class="dot pulse"></span> آنلاین</b></div>
              <div class="mini-stat"><span class="mut">آپتایم</span><b id="uptimeTxt">—</b></div>
              <div class="mini-stat"><span class="mut">پلتفرم</span><b id="platTxt">—</b></div>
              <div class="mini-stat"><span class="mut">نسخه پنل</span><b>SUKOT v3.0</b></div>
            </div>
          </div>
        </div>
        <div class="card">
          <h3><span class="ti ti-rocket"></span> سرویس ربات</h3>
          <div class="mini-stat"><span class="mut">ربات تلگرام</span><b id="botState">—</b></div>
          <div class="mini-stat"><span class="mut">آدرس عمومی پنل</span><b class="mono small" id="pubUrl">—</b></div>
          <div class="mini-stat"><span class="mut">کانال پشتیبانی</span><b><a href="https://t.me/SUKOT1344" target="_blank">@SUKOT1344</a></b></div>
          <div class="wrapgap mt">
            <button class="btn sm" onclick="botAction('start')"><span class="ti ti-player-play"></span> شروع ربات</button>
            <button class="btn ghost sm" onclick="botAction('stop')"><span class="ti ti-player-stop"></span> توقف</button>
          </div>
        </div>
      </div>
      <div class="card mt">
        <h3><span class="ti ti-trending-up"></span> پرمصرف‌ترین کانفیگ‌ها (۷ روز اخیر)</h3>
        <div id="topConfigs"></div>
      </div>
    </div>
    <div class="rightbar">
      <div class="card">
        <h3><span class="ti ti-activity"></span> فعالیت لحظه‌ای</h3>
        <div class="feed" id="ovFeed"></div>
      </div>
      <div class="card">
        <h3><span class="ti ti-plug-connected"></span> اتصال‌های زنده</h3>
        <div class="mini-stat"><span class="mut">تونل‌های فعال</span><b id="tunnelsNow">۰</b></div>
        <div class="mini-stat"><span class="mut">IPهای منحصربه‌فرد</span><b id="ipsNow">۰</b></div>
        <div id="connList" class="small mut mt" style="max-height:190px;overflow:auto"></div>
      </div>
    </div>
  </div>
</section>'''),

"links": ("اینباندها", "مدیریت کانفیگ‌های اصلی، حجم، انقضا و کلاینت‌ها", '''
<section class="pg" data-pg="links" id="pg-links">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-link"></span> مدیریت سرویس</span>
    <h1>اینباندها</h1>
    <p>هر اینباند یک کانفیگ اصلی است؛ کلاینت‌ها زیرمجموعه‌اش ساخته می‌شوند. حجم، انقضا، سقف IP و سرعت را همین‌جا تنظیم کن.</p>
    <div class="toolbar">
      <button class="btn" onclick="openLinkDrawer()"><span class="ti ti-plus"></span> اینباند جدید</button>
      <button class="btn ghost" onclick="loadLinks()"><span class="ti ti-refresh"></span> بروزرسانی</button>
    </div>
  </div>
  <div class="card" style="padding:6px">
    <div style="overflow:auto;max-height:60vh"><table class="tbl" id="linksTbl"></table></div>
  </div>
</section>'''),

"clientmgr": ("ساخت کلاینت", "ساخت و مدیریت کلاینت‌های زیرمجموعه هر اینباند", '''
<section class="pg" data-pg="clientmgr" id="pg-clientmgr">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-user-plus"></span> کلاینت‌ها</span>
    <h1>ساخت کلاینت</h1>
    <p>برای هر اینباند می‌توانی چندین کلاینت با حجم و انقضای جدا بسازی؛ همه روی یک لینک والد سوار می‌شوند.</p>
  </div>
  <div class="grid g2">
    <div class="card pad-lg">
      <h3><span class="ti ti-wand"></span> کلاینت جدید</h3>
      <label class="lb">اینباند والد</label>
      <select class="inp" id="cmParent"></select>
      <label class="lb">نام کلاینت</label>
      <input class="inp" id="cmName" placeholder="مثلاً علی — 0912" maxlength="48">
      <label class="lb">حجم (گیگ — ۰ یعنی ارث‌بری از والد)</label>
      <input class="inp" id="cmVol" type="number" min="0" value="0" dir="ltr">
      <label class="lb">مدت (روز — ۰ یعنی ارث‌بری)</label>
      <input class="inp" id="cmDays" type="number" min="0" value="0" dir="ltr">
      <label class="lb">سقف IP هم‌زمان (۰ = بی‌مرز)</label>
      <input class="inp" id="cmIp" type="number" min="0" value="0" dir="ltr">
      <button class="btn block mt" onclick="addClient()"><span class="ti ti-plus"></span> ساخت کلاینت</button>
    </div>
    <div class="card" style="padding:6px">
      <h3 style="padding:12px 14px 0"><span class="ti ti-users"></span> کلاینت‌های اینباند انتخابی</h3>
      <div style="overflow:auto;max-height:52vh"><table class="tbl" id="cmTbl"></table></div>
    </div>
  </div>
</section>'''),

"categories": ("دسته‌بندی‌ها", "گروه‌بندی کانفیگ‌ها برای فروش منظم‌تر", '''
<section class="pg" data-pg="categories" id="pg-categories">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-category"></span> سازماندهی</span>
    <h1>دسته‌بندی‌ها</h1>
    <p>دسته‌بندی برای مرتب‌سازی اینباندها (مثلاً «اقتصادی»، «گیمینگ»، «نامحدود») — حداکثر ۱۰ دسته.</p>
  </div>
  <div class="grid g2">
    <div class="card pad-lg">
      <h3><span class="ti ti-plus"></span> دسته جدید</h3>
      <label class="lb">نام دسته</label>
      <input class="inp" id="catName" maxlength="32" placeholder="مثلاً اقتصادی">
      <button class="btn block mt" onclick="addCat()"><span class="ti ti-plus"></span> افزودن دسته</button>
    </div>
    <div class="card" style="padding:6px">
      <div style="overflow:auto;max-height:44vh"><table class="tbl" id="catTbl"></table></div>
    </div>
  </div>
</section>'''),

"subgroups": ("گروه‌های ساب", "ترکیب چند کانفیگ در یک لینک اشتراک حرفه‌ای", '''
<section class="pg" data-pg="subgroups" id="pg-subgroups">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-folders"></span> اشتراک حرفه‌ای</span>
    <h1>گروه‌های ساب</h1>
    <p>چند کانفیگ را در یک لینک اشتراک ترکیب کن؛ اختیاری رمز بگذار و لینک عمومی را به مشتری بده.</p>
    <div class="toolbar">
      <button class="btn" onclick="openSubDrawer()"><span class="ti ti-plus"></span> گروه جدید</button>
    </div>
  </div>
  <div class="card" style="padding:6px">
    <div style="overflow:auto;max-height:60vh"><table class="tbl" id="subTbl"></table></div>
  </div>
</section>'''),

"reports": ("گزارش‌ها", "آمار مصرف روزانه و پرمصرف‌ترین‌ها", '''
<section class="pg" data-pg="reports" id="pg-reports">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-chart-histogram"></span> تحلیل</span>
    <h1>گزارش‌ها</h1>
    <p>روند ترافیک روزانه، وضعیت کانفیگ‌ها و پرمصرف‌ترین‌ها؛ خروجی CSV هم می‌گیری.</p>
    <div class="toolbar">
      <div class="seg" id="repRange">
        <button class="on" data-r="7" onclick="repRange(7,this)">۷ روز اخیر</button>
        <button data-r="14" onclick="repRange(14,this)">۱۴ روز اخیر</button>
        <button data-r="30" onclick="repRange(30,this)">۳۰ روز اخیر</button>
      </div>
      <a class="btn ghost" href="/api/reports/export.csv"><span class="ti ti-download"></span> خروجی CSV</a>
    </div>
  </div>
  <div class="grid g4" id="repStats"></div>
  <div class="card mt">
    <h3><span class="ti ti-chart-bar"></span> ترافیک روزانه</h3>
    <div id="repChart"></div>
  </div>
  <div class="card mt">
    <h3><span class="ti ti-fire"></span> پرمصرف‌ترین کانفیگ‌ها</h3>
    <div style="overflow:auto"><table class="tbl" id="repTop"></table></div>
  </div>
</section>'''),

"nodes": ("نودها", "اتصال پنل‌های SUKOT دیگر به عنوان نود", '''
<section class="pg" data-pg="nodes" id="pg-nodes">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-server-2"></span> زیرساخت</span>
    <h1>نودها</h1>
    <p>پنل‌های SUKOT دیگری را به عنوان نود وصل کن؛ وضعیت، تاخیر و ترافیک‌شان همین‌جا دیده می‌شود.</p>
  </div>
  <div class="grid g2">
    <div class="card pad-lg">
      <h3><span class="ti ti-key"></span> توکن این پنل</h3>
      <p class="small mut">این توکن را در پنلِ «نود» وارد کن تا به عنوان نود شناخته شود.</p>
      <div class="linkline mt"><code id="nodeToken">—</code><button class="btn sm" onclick="copyText(document.getElementById('nodeToken').textContent)"><span class="ti ti-copy"></span></button></div>
    </div>
    <div class="card pad-lg">
      <h3><span class="ti ti-plus"></span> افزودن نود</h3>
      <label class="lb">نام نود</label>
      <input class="inp" id="ndName" placeholder="مثلاً نود فرانکفورت">
      <label class="lb">آدرس پنل نود</label>
      <input class="inp" id="ndUrl" dir="ltr" placeholder="https://node.example.com">
      <label class="lb">توکن نود</label>
      <input class="inp" id="ndTok" dir="ltr" placeholder="skn_...">
      <button class="btn block mt" onclick="addNode()"><span class="ti ti-plus"></span> افزودن و تست</button>
    </div>
  </div>
  <div class="card mt" style="padding:6px">
    <div style="overflow:auto;max-height:46vh"><table class="tbl" id="nodeTbl"></table></div>
  </div>
</section>'''),

"vps": ("سرورهای VPS", "ثبت سرور، اسکن پورت، اسکن SNI و خروجی نصب Xray/WireGuard", '''
<section class="pg" data-pg="vps" id="pg-vps">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-server-cog"></span> زیرساخت</span>
    <h1>سرورهای VPS</h1>
    <p>سرورهای واقعی‌ات را ثبت کن؛ پنل پروفایل Reality/WireGuard می‌سازد، اسکریپت نصب و کانفیگ آماده می‌دهد.</p>
    <div class="toolbar">
      <button class="btn" onclick="openVpsDrawer()"><span class="ti ti-plus"></span> ثبت سرور جدید</button>
      <button class="btn ghost" onclick="loadVps()"><span class="ti ti-refresh"></span> بروزرسانی</button>
    </div>
  </div>
  <div id="vpsList" class="grid g2"></div>
</section>'''),

"tgproxy": ("پروکسی تلگرام", "ساخت و مدیریت پروکسی MTProto برای تلگرام", '''
<section class="pg" data-pg="tgproxy" id="pg-tgproxy">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-brand-telegram"></span> تلگرام</span>
    <h1>پروکسی تلگرام</h1>
    <p>پروکسی MTProto با secret امن (dd·padded) — مناسب فیلترینگ تلگرام؛ حجم، انقضا و سقف اتصال جدا برای هر پروکسی.</p>
  </div>
  <div class="grid g3" id="tgStats"></div>
  <div class="card mt">
    <h3><span class="ti ti-wand"></span> حالت خودکار <span class="chip" id="tgMode">—</span></h3>
    <div class="row">
      <button class="btn" onclick="tgAuto()"><span class="ti ti-sparkles"></span> خودکار — بهترین پروکسی را بساز</button>
      <button class="btn ghost" onclick="tgCreate()"><span class="ti ti-plus"></span> پروکسی جدید (برای کاربر دیگر)</button>
      <button class="btn ghost" onclick="tgSelftest()"><span class="ti ti-heartbeat"></span> تست سلامت</button>
    </div>
    <div id="tgTips" class="small mut mt"></div>
  </div>
  <div id="tgList" class="grid g2 mt"></div>
</section>'''),

"admins": ("ادمین‌ها", "مدیریت حساب‌های مدیریتی و مجوزها", '''
<section class="pg" data-pg="admins" id="pg-admins">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-user-shield"></span> مدیریت حساب‌ها</span>
    <h1>ادمین‌ها</h1>
    <p>حساب‌های ادمین با مجوزهای تفکیک‌شده — از ساخت اینباند تا مدیریت کلاینت‌ها.</p>
  </div>
  <div class="grid g4" id="admStats"></div>
  <div class="card mt" style="padding:6px">
    <h3 style="padding:12px 14px 0"><span class="ti ti-users"></span> حساب‌ها</h3>
    <div style="overflow:auto;max-height:40vh"><table class="tbl" id="admTbl"></table></div>
  </div>
  <div class="card mt">
    <h3><span class="ti ti-inbox"></span> درخواست‌های ثبت‌نام ادمینی</h3>
    <div id="admReqs"></div>
  </div>
</section>'''),

"activity": ("فعالیت‌ها", "لاگ رویدادهای اخیر پنل", '''
<section class="pg" data-pg="activity" id="pg-activity">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-logs"></span> رویدادها</span>
    <h1>لاگ فعالیت‌ها</h1>
    <p>آخرین رویدادهای پنل — ساخت، ویرایش، حذف، ورود و ...</p>
    <div class="toolbar"><button class="btn ghost" onclick="loadActivity()"><span class="ti ti-refresh"></span> بروزرسانی</button></div>
  </div>
  <div class="card"><div class="feed" id="actFeed" style="max-height:60vh"></div></div>
</section>'''),

"messages": ("پیام‌ها", "مرکز پیام و خطاهای سیستم", '''
<section class="pg" data-pg="messages" id="pg-messages">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-messages"></span> مرکز پیام</span>
    <h1>پیام‌ها و خطاها</h1>
    <p>خطاهای سرور و گزارش‌های سمت کاربر این‌جا جمع می‌شود.</p>
    <div class="toolbar"><button class="btn danger" onclick="clearErrors()"><span class="ti ti-trash"></span> پاک‌سازی همه</button></div>
  </div>
  <div class="card"><div class="feed" id="errFeed" style="max-height:60vh"></div></div>
</section>'''),

"settings": ("تنظیمات", "استودیو ظاهر، امنیت، ربات و برند اشتراک", '''
<section class="pg" data-pg="settings" id="pg-settings">
  <div class="pg-head">
    <span class="eyebrow"><span class="ti ti-settings"></span> تنظیمات و استودیو ظاهر</span>
    <h1>تنظیمات</h1>
    <p>ظاهر پنل را همان‌جا که هست ببین و عوض کن؛ رنگ اصلی، پوسته، فشردگی و امنیت حساب.</p>
  </div>
  <div class="grid g2">
    <div class="card pad-lg">
      <h3><span class="ti ti-palette"></span> استودیو ظاهر</h3>
      <label class="lb">پوسته</label>
      <div class="seg" id="setTheme">
        <button data-t="dark" onclick="setPref('theme','dark',this)">تیره</button>
        <button data-t="light" onclick="setPref('theme','light',this)">روشن</button>
      </div>
      <label class="lb">رنگ اصلی</label>
      <div class="swatches" id="swatches"></div>
      <label class="lb">اندازه متن</label>
      <input type="range" min="0.85" max="1.25" step="0.05" id="setFont" oninput="setPref('font',this.value,this)" style="width:100%;accent-color:var(--accent)">
      <label class="lb">گوشه‌ها</label>
      <div class="seg" id="setRadius">
        <button data-r="10" onclick="setPref('radius','10',this)">مربع</button>
        <button data-r="18" onclick="setPref('radius','18',this)">استاندارد</button>
        <button data-r="24" onclick="setPref('radius','24',this)">گرد</button>
      </div>
      <div class="row mt" style="gap:18px">
        <label class="chk"><input type="checkbox" id="setAnim" onchange="setPref('anim',this.checked?'1':'0',this)"> انیمیشن‌های پنل</label>
        <label class="chk"><input type="checkbox" id="setGlow" onchange="setPref('glow',this.checked?'1':'0',this)"> هاله نورانی</label>
      </div>
    </div>
    <div class="flexcol">
      <div class="card pad-lg">
        <h3><span class="ti ti-shield-lock"></span> امنیت حساب</h3>
        <label class="lb">نام کاربری جدید</label>
        <input class="inp" id="secUser" dir="ltr" placeholder="نام کاربری فعلی: —">
        <button class="btn soft sm mt" onclick="changeUsername()"><span class="ti ti-user-edit"></span> تغییر نام کاربری</button>
        <div class="hr"></div>
        <label class="lb">رمز فعلی</label>
        <input class="inp" id="secOld" type="password" dir="ltr">
        <label class="lb">رمز جدید</label>
        <input class="inp" id="secNew" type="password" dir="ltr">
        <button class="btn soft sm mt" onclick="changePassword()"><span class="ti ti-key"></span> تغییر رمز عبور</button>
        <div class="hr"></div>
        <button class="btn danger sm" onclick="revokeSessions()"><span class="ti ti-power"></span> لغو نشست‌های دیگر</button>
      </div>
      <div class="card pad-lg">
        <h3><span class="ti ti-rocket"></span> ربات فروش و مدیریت</h3>
        <label class="lb">Bot Token</label>
        <input class="inp" id="setBotTok" dir="ltr" placeholder="123456:ABC...">
        <label class="lb">آیدی ادمین‌ها (با کاما)</label>
        <input class="inp" id="setBotIds" dir="ltr" placeholder="111, 222">
        <div class="row mt">
          <button class="btn" onclick="saveBot()"><span class="ti ti-device-floppy"></span> ذخیره و شروع</button>
          <button class="btn ghost" onclick="botAction('stop')"><span class="ti ti-player-stop"></span> توقف</button>
        </div>
      </div>
      <div class="card pad-lg">
        <h3><span class="ti ti-world"></span> عمومی و برند اشتراک</h3>
        <label class="lb">آدرس عمومی پنل</label>
        <input class="inp" id="setPubUrl" dir="ltr" placeholder="https://your-app.shiprr.dev">
        <label class="lb">آیدی پشتیبان</label>
        <input class="inp" id="setSup" dir="ltr" placeholder="@SUKOT1344">
        <label class="lb">کانال اطلاع‌رسانی</label>
        <input class="inp" id="setChan" dir="ltr" placeholder="SUKOT1344">
        <label class="lb">استایل نام کانفیگ‌ها</label>
        <div class="linkline"><code id="namePrev">SUKOT|توفان۲۴🚀</code></div>
        <div class="row mt">
          <button class="btn" onclick="saveGeneral()"><span class="ti ti-device-floppy"></span> ذخیره تنظیمات</button>
          <button class="btn ghost" onclick="testSupport()"><span class="ti ti-send"></span> تست لینک پشتیبان</button>
        </div>
      </div>
    </div>
  </div>
</section>'''),
}

def body() -> str:
    parts = [sidebar(), '<div id="main">', topbar()]
    for pid, (title, sub, html) in PAGES.items():
        parts.append(html)
    parts.append('''
<div class="ovl" id="ovl"></div>
<div class="drawer" id="drawer"></div>
<div id="cmdk"><div class="cmdk-box">
  <input id="cmdkInp" placeholder="جستجو... (اینباند، صفحه، گروه)">
  <div class="cmdk-list" id="cmdkList"></div>
</div></div>
</div>
<div id="toasts"></div>''')
    return "\n".join(parts)

TITLES = {k: (t, s) for k, (t, s, _) in PAGES.items()}
