# ui/dash_css.py — dashboard styles (SUKOT ember)
def css() -> str:
    return """
/* ================= SUKOT dashboard layout ================= */
html{scroll-behavior:smooth}
body{display:flex}
/* sidebar */
#sidebar{position:fixed;top:0;bottom:0;inset-inline-start:0;width:266px;z-index:600;display:flex;flex-direction:column;
  background:linear-gradient(180deg,rgba(30,18,22,.92),rgba(16,10,12,.96));backdrop-filter:blur(16px);
  border-inline-end:1px solid var(--line);transition:transform .28s cubic-bezier(.2,.8,.2,1)}
[data-theme="light"] #sidebar{background:linear-gradient(180deg,rgba(255,255,255,.95),rgba(250,243,245,.97))}
.brand{display:flex;align-items:center;gap:12px;padding:18px 18px 14px}
.brand img{width:52px;height:52px;border-radius:50%;object-fit:cover;border:2px solid rgba(var(--accent-rgb),.55);box-shadow:var(--glow);animation:brandpulse 5s ease-in-out infinite}
@keyframes brandpulse{0%,100%{box-shadow:0 0 16px rgba(var(--accent-rgb),.25)}50%{box-shadow:0 0 26px rgba(var(--accent-rgb),.55)}}
.brand b{font-size:1.3em;letter-spacing:.18em}
.brand small{display:block;color:var(--sub2);font-size:.66em;letter-spacing:.3em;font-weight:700;margin-top:2px}
.nav{flex:1;overflow-y:auto;padding:6px 12px 12px}
.nav .sec{font-size:.68em;font-weight:800;color:var(--sub2);letter-spacing:.18em;margin:16px 8px 7px}
.nav a{display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:13px;color:var(--sub);
  font-weight:600;font-size:.92em;margin-bottom:3px;border:1px solid transparent;transition:.16s;cursor:pointer;position:relative}
.nav a .ti{font-size:19px;width:22px;text-align:center;color:var(--sub2);transition:.16s}
.nav a:hover{color:var(--text);background:rgba(255,255,255,.045)}
.nav a.on{color:#fff;background:linear-gradient(135deg,rgba(var(--accent-rgb),.95),var(--accent-d));
  box-shadow:var(--glow);border-color:transparent}
.nav a.on .ti{color:#fff}
.nav a .nb{margin-inline-start:auto;background:rgba(var(--accent-rgb),.18);color:var(--accent);font-size:.7em;
  min-width:20px;height:20px;border-radius:99px;display:inline-flex;align-items:center;justify-content:center;padding:0 6px;font-weight:800}
.nav a.on .nb{background:rgba(255,255,255,.25);color:#fff}
.sidefoot{padding:12px;border-top:1px solid var(--line)}
.uchip{display:flex;align-items:center;gap:10px;background:var(--panel2);border:1px solid var(--line);border-radius:14px;padding:9px 11px}
.uchip img{width:38px;height:38px;border-radius:50%;object-fit:cover;border:2px solid rgba(var(--accent-rgb),.5);box-shadow:0 0 14px rgba(var(--accent-rgb),.3)}
.uchip b{font-size:.9em;display:block}
.uchip small{color:var(--accent);font-size:.7em;font-weight:800;letter-spacing:.08em}
.uchip .iconbtn{margin-inline-start:auto}
/* main */
#main{flex:1;margin-inline-start:266px;min-width:0;display:flex;flex-direction:column}
#topbar{position:sticky;top:0;z-index:500;display:flex;align-items:center;gap:12px;padding:12px 22px;
  background:rgba(12,8,9,.72);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}
[data-theme="light"] #topbar{background:rgba(255,255,255,.75)}
#topbar .tt b{font-size:1.06em}
#topbar .tt small{display:block;color:var(--sub2);font-size:.78em}
.tchip{font-variant-numeric:tabular-nums}
.tchip.tver{background:rgba(var(--accent-rgb),.12);border-color:rgba(var(--accent-rgb),.35)}
.tavatar{position:relative;width:40px;height:40px;flex:none}
.tavatar img{width:40px;height:40px;border-radius:50%;object-fit:cover;border:2px solid rgba(var(--accent-rgb),.6);box-shadow:0 0 16px rgba(var(--accent-rgb),.35);display:block;cursor:pointer;transition:.2s}
.tavatar img:hover{transform:scale(1.06)}
.tavatar i{position:absolute;bottom:0;inset-inline-end:0;width:11px;height:11px;border-radius:50%;background:var(--good);border:2px solid #0c080a;box-shadow:0 0 8px rgba(47,209,140,.7);animation:skpulse 2.4s infinite}
[data-theme="light"] .tavatar i{border-color:#fff}
@media(max-width:980px){.tchip{display:none}}
#search{margin-inline-start:auto}
.sbtn{display:flex;align-items:center;gap:9px;background:var(--panel2);border:1px solid var(--line);border-radius:12px;
  padding:8px 13px;color:var(--sub);cursor:pointer;font-size:.86em;min-width:190px;transition:.18s}
.sbtn:hover{border-color:rgba(var(--accent-rgb),.5)}
.sbtn .kbd{margin-inline-start:auto}
#burger{display:none}
#content{padding:20px 22px 46px;max-width:1460px;width:100%}
@media(max-width:980px){
  #sidebar{transform:translateX(105%)}[dir="ltr"] #sidebar{transform:translateX(-105%)}
  #sidebar.open{transform:none!important}
  #main{margin-inline-start:0}
  #burger{display:inline-flex}
  .sbtn{min-width:0}.sbtn span,.sbtn .kbd{display:none}
}
#sideovl{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:590;display:none}
#sideovl.show{display:block}

/* pages */
.pg{display:none;animation:pgin .3s ease}
.pg.on{display:block}
@keyframes pgin{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
.pg-head{margin-bottom:18px}
.eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:.74em;font-weight:800;letter-spacing:.14em;
  color:var(--accent);background:rgba(var(--accent-rgb),.1);border:1px solid rgba(var(--accent-rgb),.3);
  padding:5px 13px;border-radius:99px;margin-bottom:10px}
.eyebrow .dot{width:7px;height:7px}
.pg-head h1{font-size:1.55em}
.pg-head p{color:var(--sub);margin:7px 0 0;font-size:.92em;max-width:720px;line-height:1.9}
.toolbar{display:flex;gap:9px;flex-wrap:wrap;margin-top:14px}

/* hero — 3D ring banner (no photo) */
.hero{position:relative;overflow:hidden;border-radius:var(--r-card);border:1px solid var(--line);
  background:linear-gradient(120deg,rgba(var(--accent-rgb),.2),rgba(0,0,0,0) 55%),var(--panel);padding:22px;margin-bottom:var(--density);
  transform-style:preserve-3d}
.hero3d .h-content{position:relative;z-index:3}
.hero3d h2{font-size:1.34em;margin-bottom:6px}
.hero3d p{color:var(--sub);font-size:.9em;margin:0 0 13px;max-width:640px;line-height:1.9}
.hero3d .chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:13px}
.h-ring{position:absolute;border-radius:50%;border:1.5px solid rgba(var(--accent-rgb),.35);pointer-events:none}
.h-ring.hr1{width:300px;height:300px;top:-110px;inset-inline-end:-70px;animation:hrspin 14s linear infinite}
.h-ring.hr2{width:210px;height:210px;top:-60px;inset-inline-end:-10px;border-style:dashed;border-color:rgba(var(--accent-rgb),.28);animation:hrspin 9s linear infinite reverse}
.h-ring.hr3{width:420px;height:420px;top:-190px;inset-inline-end:-180px;border-color:rgba(var(--accent-rgb),.16);animation:hrspin 22s linear infinite}
.h-ring::after{content:'';position:absolute;top:-5px;inset-inline-start:calc(50% - 5px);width:9px;height:9px;border-radius:50%;
  background:var(--accent);box-shadow:0 0 14px rgba(var(--accent-rgb),.85)}
@keyframes hrspin{from{transform:rotate(0)}to{transform:rotate(360deg)}}
.h-glow{position:absolute;width:340px;height:340px;top:-130px;inset-inline-end:-90px;border-radius:50%;
  background:radial-gradient(circle,rgba(var(--accent-rgb),.22),transparent 65%);filter:blur(10px);animation:hglow 6s ease-in-out infinite}
@keyframes hglow{0%,100%{opacity:.55;transform:scale(.92)}50%{opacity:1;transform:scale(1.06)}}

/* KPI — 3D depth cards */
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:var(--r-card);padding:15px 16px;position:relative;overflow:hidden;
  transition:transform .22s ease,box-shadow .22s ease,border-color .22s;transform-style:preserve-3d}
.kpi:hover{transform:perspective(700px) rotateX(4deg) translateY(-4px);border-color:rgba(var(--accent-rgb),.5);
  box-shadow:0 18px 40px rgba(0,0,0,.4),0 0 24px rgba(var(--accent-rgb),.14)}
.kpi .lab{color:var(--sub);font-size:.8em;font-weight:700;display:flex;align-items:center;gap:7px}
.kpi .lab .ti{color:var(--accent);font-size:17px}
.kpi .val{font-size:1.5em;font-weight:800;margin-top:7px;
  background:linear-gradient(120deg,var(--text),rgba(var(--accent-rgb),.9));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.kpi .sub{color:var(--sub2);font-size:.74em;margin-top:3px}
.kpi::after{content:'';position:absolute;inset-inline-start:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,rgba(var(--accent-rgb),1),transparent)}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(var(--accent-rgb),.55),transparent);opacity:.7}

/* resource cards */
.res .val{font-size:1.22em}
.bar{height:6px;border-radius:99px;background:var(--panel2);overflow:hidden;margin-top:9px}
.bar i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,rgba(var(--accent-rgb),1),var(--accent-d));transition:width .5s ease}
.bar.warn i{background:linear-gradient(90deg,var(--warn),#c98a10)}
.bar.bad i{background:linear-gradient(90deg,var(--bad),#b31d31)}
.spark{width:100%;height:38px;margin-top:8px}
.spark polyline{fill:none;stroke:var(--accent);stroke-width:2;stroke-linecap:round}
.spark .fill{fill:rgba(var(--accent-rgb),.14);stroke:none}

/* feed & lists */
.feed{display:flex;flex-direction:column;gap:2px;max-height:330px;overflow:auto}
.fitem{display:flex;gap:10px;padding:9px 6px;border-bottom:1px dashed var(--line);font-size:.86em;align-items:flex-start}
.fitem:last-child{border:0}
.fitem .ti{color:var(--accent);margin-top:2px}
.fitem .t{color:var(--sub2);font-size:.76em;margin-inline-start:auto;flex:none}
.fitem.kind-warn .ti{color:var(--warn)} .fitem.kind-err .ti{color:var(--bad)} .fitem.kind-act .ti{color:var(--good)}

/* usage cell */
.usage{min-width:130px}
.usage .bar{margin-top:5px}
.usage small{color:var(--sub2);font-size:.72em}

/* status badges */
.st{display:inline-flex;align-items:center;gap:6px;font-size:.78em;font-weight:800}
.st .dot{width:7px;height:7px}

/* QR drawer bits */
.qrbox{display:flex;justify-content:center;padding:10px;background:#fff;border-radius:14px;margin:12px 0}
.qrbox canvas,.qrbox img{border-radius:8px}
.linkline{display:flex;gap:8px;align-items:center;background:rgba(0,0,0,.25);border:1px solid var(--line2);
  border-radius:12px;padding:9px 12px;direction:ltr}
[data-theme="light"] .linkline{background:#fff}
.linkline code{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.8em;font-family:monospace}

/* segment control */
.seg{display:inline-flex;background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:3px;gap:3px}
.seg button{border:0;background:transparent;color:var(--sub);padding:7px 14px;border-radius:9px;cursor:pointer;font-family:var(--font);font-weight:700;font-size:.86em;transition:.15s}
.seg button.on{background:linear-gradient(135deg,rgba(var(--accent-rgb),.95),var(--accent-d));color:#fff}

/* swatches */
.swatches{display:flex;gap:9px;flex-wrap:wrap}
.swatch{width:38px;height:38px;border-radius:13px;cursor:pointer;border:2px solid transparent;position:relative;transition:.15s}
.swatch:hover{transform:scale(1.08)}
.swatch.on{border-color:var(--text)}
.swatch i{position:absolute;inset:0;border-radius:10px}

/* command palette */
#cmdk{position:fixed;inset:0;z-index:950;display:none;background:rgba(4,2,3,.6);backdrop-filter:blur(6px);padding-top:12vh}
#cmdk.show{display:block}
.cmdk-box{width:min(560px,92vw);margin:0 auto;background:var(--panel-solid);border:1px solid var(--line2);border-radius:18px;overflow:hidden;box-shadow:var(--shadow)}
.cmdk-box input{width:100%;border:0;outline:0;background:transparent;color:var(--text);padding:16px 18px;font-family:var(--font);font-size:1em;border-bottom:1px solid var(--line)}
.cmdk-list{max-height:46vh;overflow:auto;padding:6px}
.cmdk-list div{padding:10px 13px;border-radius:11px;cursor:pointer;display:flex;gap:10px;align-items:center;font-size:.92em}
.cmdk-list div:hover,.cmdk-list div.sel{background:rgba(var(--accent-rgb),.12)}
.cmdk-list .ti{color:var(--accent)}

/* empty state */
.empty{text-align:center;padding:34px 10px;color:var(--sub2)}
.empty .ti{font-size:40px;display:block;margin-bottom:10px;opacity:.5}
.empty b{color:var(--sub)}

/* gauge (health + consumption) */
.gauge{--p:0;width:112px;height:112px;border-radius:50%;flex:none;position:relative;
  background:conic-gradient(rgba(var(--accent-rgb),1) calc(var(--p)*1%),var(--line2) 0);
  display:flex;align-items:center;justify-content:center}
.gauge::before{content:'';position:absolute;inset:9px;border-radius:50%;background:var(--panel-solid)}
.gauge b{position:relative;font-size:1.25em;z-index:2}

/* online badge (connected users per config) */
.onum{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:.86em;color:var(--good);
  background:rgba(47,209,140,.1);border:1px solid rgba(47,209,140,.3);border-radius:99px;padding:3px 10px}
.onum.zero{color:var(--sub2);background:rgba(150,140,145,.08);border-color:var(--line2)}
.onum .dot{width:6px;height:6px}

/* operator tag */
.optag{font-size:.72em;font-weight:800;padding:3px 9px;border-radius:99px;background:rgba(255,255,255,.08);color:var(--sub)}
.optag.mci{color:#38bdf8;background:rgba(56,189,248,.12)}
.optag.irancell{color:#facc15;background:rgba(250,204,21,.12)}
.optag.tci{color:#a78bfa;background:rgba(167,139,250,.12)}
.optag.rightel{color:#fb7185;background:rgba(251,113,133,.12)}

/* news page heroes */
.news-hero{border-radius:var(--r-card);padding:26px;border:1px solid rgba(var(--accent-rgb),.4);
  background:linear-gradient(120deg,rgba(var(--accent-rgb),.22),transparent 70%),var(--panel);margin-bottom:var(--density)}
.news-hero h2{font-size:1.3em;margin-bottom:6px}
.news-hero p{color:var(--sub);font-size:.92em;max-width:600px;line-height:1.9}

/* responsive grid helpers */
.mt{margin-top:var(--density)}
.flexcol{display:flex;flex-direction:column;gap:var(--density)}
.wrapgap{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.rightbar{display:flex;flex-direction:column;gap:var(--density)}
@media(min-width:1100px){.ov-grid{display:grid;grid-template-columns:1fr 340px;gap:var(--density);align-items:start}}
.scroll-y{max-height:420px;overflow:auto}
.mini-stat{display:flex;justify-content:space-between;font-size:.86em;padding:7px 2px;border-bottom:1px dashed var(--line)}
.mini-stat:last-child{border:0}
.mini-stat b{font-weight:800}
"""
