# ui/login.py — SUKOT login page · full 3D animated edition
from ui.theme import page_head, toast_js, APP, LOGO, HERO, AVATAR

def render(error: str = "", year: int = 2026) -> str:
    err_html = f'<div class="err"><span class="ti ti-alert-circle"></span> {error}</div>' if error else ""
    css = """
body{display:flex;min-height:100vh;overflow-x:hidden;overflow-y:auto}
/* ---------- ambient 3D space ---------- */
.space{position:fixed;inset:0;z-index:0;overflow:hidden;perspective:1100px;pointer-events:none}
.orb{position:absolute;border-radius:50%;filter:blur(70px);opacity:.5;animation:drift 16s ease-in-out infinite alternate}
.orb.o1{width:520px;height:520px;background:rgba(var(--accent-rgb),.35);top:-160px;inset-inline-start:-120px}
.orb.o2{width:420px;height:420px;background:rgba(var(--accent-rgb),.22);bottom:-140px;inset-inline-end:-110px;animation-delay:-6s}
.orb.o3{width:260px;height:260px;background:rgba(255,176,32,.14);top:38%;inset-inline-start:52%;animation-delay:-11s}
@keyframes drift{from{transform:translate3d(0,0,0) scale(1)}to{transform:translate3d(40px,32px,0) scale(1.14)}}
.floor{position:absolute;left:-60%;right:-60%;top:58%;bottom:-42%;
  background:linear-gradient(rgba(var(--accent-rgb),.16) 1px,transparent 1px),
             linear-gradient(90deg,rgba(var(--accent-rgb),.16) 1px,transparent 1px);
  background-size:52px 52px;transform:rotateX(72deg);transform-origin:top center;
  animation:floorrun 2.6s linear infinite;opacity:.5;
  -webkit-mask-image:linear-gradient(180deg,transparent,#000 26%,transparent 92%);
  mask-image:linear-gradient(180deg,transparent,#000 26%,transparent 92%)}
@keyframes floorrun{from{background-position:0 0,0 0}to{background-position:0 52px,52px 0}}
.stars{position:absolute;inset:0}
.stars i{position:absolute;width:2px;height:2px;border-radius:50%;background:rgba(255,255,255,.75);
  animation:tw 3.2s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:.15;transform:scale(.7)}50%{opacity:.9;transform:scale(1.2)}}

/* ---------- layout ---------- */
.wrap{position:relative;z-index:2;display:grid;grid-template-columns:1.05fr .95fr;min-height:100vh;width:100%}
@media(max-width:920px){.wrap{grid-template-columns:1fr}.hero{display:none}}

/* ---------- left hero (desktop) ---------- */
.hero{position:relative;overflow:hidden;border-inline-end:1px solid var(--line)}
.hero img.art{position:absolute;inset:-6%;width:112%;height:112%;object-fit:cover;opacity:.9;animation:kb 26s ease-in-out infinite alternate}
@keyframes kb{from{transform:scale(1) translate(0,0)}to{transform:scale(1.12) translate(-1.6%,1.4%)}}
.hero .shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(8,4,5,.30),rgba(8,4,5,.90) 80%)}
.hero .inner{position:relative;z-index:2;display:flex;flex-direction:column;justify-content:flex-end;padding:44px;height:100%;gap:15px}
.wordmark{position:absolute;top:32px;inset-inline-start:44px;z-index:2;display:flex;align-items:center;gap:12px}
.wordmark img{width:52px;height:52px;border-radius:50%;object-fit:cover;border:2px solid rgba(var(--accent-rgb),.65);
  box-shadow:var(--glow);animation:spinGlow 7s linear infinite}
@keyframes spinGlow{0%{box-shadow:0 0 22px rgba(var(--accent-rgb),.35),0 0 46px rgba(var(--accent-rgb),.12)}
 50%{box-shadow:0 0 30px rgba(var(--accent-rgb),.6),0 0 60px rgba(var(--accent-rgb),.22)}
 100%{box-shadow:0 0 22px rgba(var(--accent-rgb),.35),0 0 46px rgba(var(--accent-rgb),.12)}}
.wordmark b{font-size:1.6em;letter-spacing:.16em;color:#fff;text-shadow:0 2px 18px rgba(255,61,84,.55)}
.wordmark small{display:block;font-size:.6em;letter-spacing:.4em;color:rgba(255,255,255,.65);font-weight:700}
.hero h2{color:#fff;font-size:2.05em;line-height:1.4;max-width:540px;margin:0;
  background:linear-gradient(120deg,#fff,rgba(255,120,140,.95));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero p{color:rgba(255,255,255,.78);max-width:560px;line-height:1.95;margin:0}
.chips{display:flex;gap:9px;flex-wrap:wrap}
.chips .chip{background:rgba(255,255,255,.10);border-color:rgba(255,255,255,.26);color:#fff;backdrop-filter:blur(6px);
  animation:chipfloat 4.6s ease-in-out infinite}
.chips .chip:nth-child(2){animation-delay:-1.1s}.chips .chip:nth-child(3){animation-delay:-2.2s}.chips .chip:nth-child(4){animation-delay:-3.3s}
@keyframes chipfloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
.hstats{display:flex;gap:10px;flex-wrap:wrap;margin-top:4px}
.hstat{flex:1;min-width:118px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.2);border-radius:15px;
  padding:11px 14px;backdrop-filter:blur(8px);transform:perspective(600px) rotateX(6deg);transition:.3s}
.hstat:hover{transform:perspective(600px) rotateX(0) translateY(-3px);border-color:rgba(var(--accent-rgb),.5)}
.hstat b{display:block;font-size:1.02em;color:#fff}
.hstat span{font-size:.72em;color:rgba(255,255,255,.6);letter-spacing:.06em}

/* ---------- right card ---------- */
.side{display:flex;align-items:center;justify-content:center;padding:34px 22px;position:relative}
.card.login{width:min(444px,100%);padding:26px 26px 20px;position:relative;
  transform-style:preserve-3d;transition:transform .18s ease-out;will-change:transform;
  box-shadow:0 30px 70px rgba(0,0,0,.55),0 0 0 1px rgba(var(--accent-rgb),.12),0 0 60px rgba(var(--accent-rgb),.08)}
.secure{position:absolute;top:16px;inset-inline-end:16px;z-index:3}

/* ---------- 3D avatar scene ---------- */
.avscene{position:relative;width:150px;height:150px;margin:2px auto 6px;transform:translateZ(46px);transform-style:preserve-3d}
.avatar{position:absolute;inset:17px;width:116px;height:116px;border-radius:50%;object-fit:cover;display:block;z-index:2;
  border:2px solid rgba(var(--accent-rgb),.7);box-shadow:0 0 26px rgba(var(--accent-rgb),.45),0 0 70px rgba(var(--accent-rgb),.18);
  animation:avfloat 4.2s ease-in-out infinite}
@keyframes avfloat{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-7px) rotate(1.6deg)}}
.avhalo{position:absolute;inset:8px;border-radius:50%;background:radial-gradient(circle,rgba(var(--accent-rgb),.3),transparent 66%);
  animation:halo 4.2s ease-in-out infinite;filter:blur(6px)}
@keyframes halo{0%,100%{opacity:.5;transform:scale(.94)}50%{opacity:.95;transform:scale(1.08)}}
.ring{position:absolute;inset:0;border-radius:50%;border:1px solid rgba(var(--accent-rgb),.45);transform-style:preserve-3d}
.ring.r1{animation:orbit 9s linear infinite}
.ring.r2{inset:-11px;border-color:rgba(var(--accent-rgb),.28);border-style:dashed;animation:orbit 14s linear infinite reverse}
.ring.r3{inset:9px;border-color:rgba(255,255,255,.14);transform:rotateX(66deg);animation:orbitflat 7s linear infinite}
.ring::after{content:'';position:absolute;top:-4px;inset-inline-start:calc(50% - 4px);width:8px;height:8px;border-radius:50%;
  background:var(--accent);box-shadow:0 0 12px rgba(var(--accent-rgb),.9),0 0 26px rgba(var(--accent-rgb),.5)}
@keyframes orbit{from{transform:rotateX(62deg) rotateZ(0)}to{transform:rotateX(62deg) rotateZ(360deg)}}
@keyframes orbitflat{from{transform:rotateX(66deg) rotateZ(360deg)}to{transform:rotateX(66deg) rotateZ(0)}}

.card.login h1{font-size:1.32em;text-align:center;margin-top:8px}
.card.login .sub{text-align:center;color:var(--sub);font-size:.85em;margin:7px 0 13px;line-height:1.8}
.dtbar{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:0 0 13px;transform:translateZ(22px)}
.dtbar .chip{font-variant-numeric:tabular-nums}
.dtbar .chip .ti{animation:tick 1s steps(2) infinite}
@keyframes tick{50%{opacity:.45}}
.err{background:rgba(255,77,94,.12);border:1px solid rgba(255,77,94,.4);color:var(--bad);
  border-radius:12px;padding:11px 14px;font-size:.88em;margin-bottom:12px;display:flex;gap:8px;align-items:center}
.frow{position:relative;margin-bottom:12px;transform:translateZ(16px)}
.frow .ti{position:absolute;top:13px;inset-inline-start:13px;color:var(--sub2);font-size:17px;transition:.2s}
.frow:focus-within .ti{color:var(--accent)}
.frow .inp{padding-inline-start:42px;direction:ltr;text-align:left}
.frow .eye{position:absolute;top:9px;inset-inline-end:9px}
.caps{display:none;color:var(--warn);font-size:.8em;margin:-6px 0 10px;padding-inline-start:42px}
.caps.show{display:block}
.remember{display:flex;justify-content:space-between;align-items:center;margin:4px 0 16px;transform:translateZ(14px)}
.gobtn{position:relative;overflow:hidden;transform:translateZ(26px)}
.gobtn::after{content:'';position:absolute;top:0;bottom:0;width:46%;inset-inline-start:-70%;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.34),transparent);transform:skewX(-18deg);
  animation:shine 3.4s ease-in-out infinite}
@keyframes shine{0%,55%{inset-inline-start:-70%}85%,100%{inset-inline-start:130%}}
.req{font-size:.86em;color:var(--sub);text-align:center;margin-top:12px}
.req a{cursor:pointer}
.tgstrip{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:15px;
  background:rgba(var(--accent-rgb),.08);border:1px solid rgba(var(--accent-rgb),.32);border-radius:14px;padding:11px 14px;
  transform:translateZ(14px)}
.tgstrip .l{display:flex;align-items:center;gap:10px;font-size:.86em;color:var(--sub)}
.tgstrip .l .ti{color:var(--accent);font-size:20px}
.tgstrip .l b{color:var(--text);letter-spacing:.04em}
.foot{display:flex;align-items:center;justify-content:center;gap:10px;color:var(--sub2);font-size:.76em;
  letter-spacing:.16em;margin-top:15px;font-weight:700;transform:translateZ(10px)}
.foot .sep{opacity:.4}
.livedot{display:inline-flex;align-items:center;gap:6px;color:var(--good);letter-spacing:.04em}
.ping{color:var(--sub2);font-weight:600;letter-spacing:0}
.embers{position:fixed;inset:0;pointer-events:none;z-index:1}
@keyframes spin{to{transform:rotate(360deg)}}
.spin{display:inline-block;animation:spin 1s linear infinite}
/* registration modal */
.center-modal .card{width:min(460px,94vw)}
"""
    js = """
const eye=document.getElementById('eye'); const pw=document.getElementById('pw');
eye&&eye.addEventListener('click',()=>{ if(pw.type==='password'){pw.type='text';eye.className='ti ti-eye-off iconbtn eye'} else {pw.type='password';eye.className='ti ti-eye iconbtn eye'} });
pw&&pw.addEventListener('keyup',e=>{ document.getElementById('caps').classList.toggle('show', e.getModifierState&&e.getModifierState('CapsLock')); });
/* ---- 3D tilt of the login card ---- */
(function(){
  const card=document.querySelector('.card.login'); if(!card||matchMedia('(pointer:coarse)').matches) return;
  const wrap=card.parentElement;
  wrap.addEventListener('mousemove',e=>{
    const r=card.getBoundingClientRect();
    const x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5;
    card.style.transform=`perspective(950px) rotateY(${(x*7).toFixed(2)}deg) rotateX(${(-y*7).toFixed(2)}deg) translateZ(6px)`;
  });
  wrap.addEventListener('mouseleave',()=>{card.style.transform=''});
})();
/* ---- stars field ---- */
(function(){
  const s=document.querySelector('.stars'); if(!s) return;
  for(let i=0;i<26;i++){const d=document.createElement('i');
    d.style.left=(Math.random()*100)+'%';d.style.top=(Math.random()*100)+'%';
    d.style.animationDelay=(Math.random()*3)+'s';d.style.opacity=(Math.random()*.6+.2);
    s.appendChild(d);}
})();
/* ---- live Persian (Jalali) date + clock ---- */
(function(){
  const dEl=document.getElementById('jdate'), tEl=document.getElementById('jclock'); if(!dEl||!tEl) return;
  const df=new Intl.DateTimeFormat('fa-IR-u-ca-persian',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
  function tick(){
    const n=new Date();
    dEl.textContent=df.format(n);
    tEl.textContent=n.toLocaleTimeString('fa-IR',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
  }
  tick();setInterval(tick,1000);
})();
/* ---- live ping to /health ---- */
(async function(){
  const p=document.getElementById('ping'); if(!p) return;
  async function beat(){
    const t0=performance.now();
    try{ await fetch('/health?_=' + Date.now(),{cache:'no-store'});
      p.textContent=Math.max(1,Math.round(performance.now()-t0))+'ms'; }
    catch(_){ p.textContent='—'; }
  }
  beat();setInterval(beat,8000);
})();
/* ---- admin registration ---- */
function openReq(){ document.getElementById('reqModal').classList.add('show'); document.getElementById('ovl').classList.add('show'); }
function closeAll(){ document.querySelectorAll('.center-modal,.ovl').forEach(x=>x.classList.remove('show')); }
document.getElementById('ovl')?.addEventListener('click', closeAll);
document.getElementById('reqForm')?.addEventListener('submit', async e=>{
  e.preventDefault();
  const f=e.target; const b=f.querySelector('button[type=submit]'); b.disabled=true; b.textContent='در حال ارسال...';
  try{
    const r=await fetch('/api/admin-requests',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:f.name.value, tg:f.tg.value, note:f.note.value})});
    const j=await r.json();
    if(j.ok){ toast('درخواستت ثبت شد؛ منتظر تایید مدیر باش.','ok'); closeAll(); f.reset(); }
    else { toast(j.error||'خطا در ثبت درخواست','err'); }
  }catch(_){ toast('ارتباط برقرار نشد','err') }
  b.disabled=false; b.innerHTML='ارسال درخواست';
});
/* ---- login submit loading ---- */
document.getElementById('loginForm')?.addEventListener('submit',()=>{
  const b=document.querySelector('#loginForm button[type=submit]');
  if(b){b.disabled=true;b.innerHTML='<span class="ti ti-loader-2 spin"></span> در حال ورود...';}
});
(function embers(){
  const c=document.getElementById('embers'); if(!c) return;
  c.width=innerWidth; c.height=innerHeight; const x=c.getContext('2d');
  const P=[...Array(52)].map(()=>({x:Math.random()*c.width,y:Math.random()*c.height,r:Math.random()*2.2+.6,
    vy:-(Math.random()*.45+.15),vx:(Math.random()-.5)*.3,o:Math.random()*.5+.2,a:Math.random()*6.28}));
  (function tick(){ x.clearRect(0,0,c.width,c.height);
    for(const p of P){ p.y+=p.vy; p.x+=p.vx+Math.sin(p.a+=.012)*.16; if(p.y<-6){p.y=c.height+6;p.x=Math.random()*c.width}
      const g=x.createRadialGradient(p.x,p.y,0,p.x,p.y,p.r*4);
      g.addColorStop(0,'rgba(255,80,100,'+p.o+')'); g.addColorStop(1,'rgba(255,80,100,0)');
      x.fillStyle=g; x.beginPath(); x.arc(p.x,p.y,p.r*4,0,6.28); x.fill(); }
    requestAnimationFrame(tick); })();
})();
""" + toast_js()

    body = f"""
<body>
<canvas id="embers" class="embers"></canvas>
<div class="space" aria-hidden="true">
  <div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div>
  <div class="floor"></div>
  <div class="stars"></div>
</div>
<div class="wrap">
  <section class="hero">
    <img class="art" src="{HERO}" alt="SUKOT">
    <div class="shade"></div>
    <div class="wordmark"><img src="{LOGO}" alt="SUKOT"><span><b>SUKOT</b><small>PANEL · نسل جدید</small></span></div>
    <div class="inner">
      <h2>کنترل کامل شبکه‌ات؛ قدرت در دست‌های خودته.</h2>
      <p>مدیریت اینباندها، کلاینت‌ها، گروه‌های اشتراک و پروکسی تلگرام — همه در یک مرکز کنترل SUKOT؛ با مانیتورینگ زنده و پریست مخصوص هر اپراتور.</p>
      <div class="hstats">
        <div class="hstat"><b>VLESS + XHTTP</b><span>موتور اتصال زنده</span></div>
        <div class="hstat"><b>MTProto</b><span>پروکسی تلگرام</span></div>
        <div class="hstat"><b>۹ اپراتور</b><span>پریست آماده</span></div>
        <div class="hstat"><b>رمزنگاری‌شده</b><span>نشست امن</span></div>
      </div>
      <div class="chips">
        <span class="chip"><span class="ti ti-heartbeat"></span> مانیتور زنده</span>
        <span class="chip"><span class="ti ti-antenna-bars-5"></span> پریست اپراتورها</span>
        <span class="chip"><span class="ti ti-brand-telegram"></span> پروکسی تلگرام</span>
        <span class="chip"><span class="ti ti-shield-lock"></span> نشست رمزنگاری‌شده</span>
      </div>
    </div>
  </section>
  <section class="side">
    <div>
      <span class="chip secure good"><span class="dot pulse"></span> اتصال امن TLS</span>
      <div class="card login">
        <div class="avscene">
          <div class="ring r2"></div><div class="ring r1"></div><div class="ring r3"></div>
          <div class="avhalo"></div>
          <img class="avatar" src="{AVATAR}" alt="SUKOT profile">
        </div>
        <h1>ورود به مرکز کنترل SUKOT</h1>
        <div class="sub">حساب کاربری مدیر پنل — دسترسی کامل به سرویس‌ها و زیرساخت</div>
        <div class="dtbar">
          <span class="chip gray"><span class="ti ti-calendar"></span> <span id="jdate">—</span></span>
          <span class="chip"><span class="ti ti-clock"></span> <span id="jclock">—</span></span>
        </div>
        {err_html}
        <form method="post" action="/login" id="loginForm">
          <div class="frow"><span class="ti ti-user"></span>
            <input class="inp" name="username" id="user" placeholder="نام کاربری" value="Sukot" autocomplete="username" dir="ltr"></div>
          <div class="frow"><span class="ti ti-lock"></span>
            <input class="inp" name="password" id="pw" type="password" placeholder="رمز عبور" autocomplete="current-password" dir="ltr" required>
            <span class="ti ti-eye iconbtn eye" id="eye"></span></div>
          <div class="caps" id="caps">⌨ Caps Lock روشن است</div>
          <div class="remember">
            <label class="chk"><input type="checkbox" name="remember" checked> مرا به خاطر بسپار</label>
            <span class="chip gray"><span class="ti ti-shield-check"></span> ورود امن</span>
          </div>
          <button class="btn lg block gobtn" type="submit"><span class="ti ti-login-2"></span> ورود به پنل</button>
        </form>
        <div class="req">مدیر جدید هستی؟ <a onclick="openReq()">ثبت‌نام ادمینی</a></div>
        <div class="tgstrip">
          <div class="l"><span class="ti ti-brand-telegram"></span> <span>کانال رسمی <b>SUKOT</b></span></div>
          <a class="btn sm" href="https://t.me/SUKOT1344" target="_blank" rel="noopener">عضویت</a>
        </div>
        <div class="foot">
          <span>SUKOT · v3.0</span><span class="sep">•</span>
          <span class="livedot"><span class="dot pulse"></span> آنلاین</span><span class="sep">•</span>
          <span class="ping">پینگ <b id="ping">—</b></span>
        </div>
      </div>
    </div>
  </section>
</div>
<div class="ovl" id="ovl"></div>
<div class="center-modal" id="reqModal">
  <div class="card pad-lg">
    <h3><span class="ti ti-user-shield"></span> درخواست همکاری ادمینی</h3>
    <p class="small mut">درخواستت برای مدیر پنل ارسال می‌شه؛ بعد از تایید، حساب ادمین برات ساخته می‌شه.</p>
    <form id="reqForm">
      <label class="lb">نام و نام خانوادگی</label>
      <input class="inp" name="name" required maxlength="60">
      <label class="lb">آیدی تلگرام</label>
      <input class="inp" name="tg" required maxlength="40" placeholder="@Sukot40" dir="ltr">
      <label class="lb">توضیح (اختیاری)</label>
      <textarea class="inp" name="note" rows="3" maxlength="300"></textarea>
      <div class="row" style="margin-top:16px">
        <button class="btn" type="submit">ارسال درخواست</button>
        <button class="btn ghost" type="button" onclick="closeAll()">بستن</button>
      </div>
    </form>
  </div>
</div>
<script>{js}</script>
</body>
</html>"""
    return page_head(f"{APP} | ورود مدیر", extra_css=css) + body
