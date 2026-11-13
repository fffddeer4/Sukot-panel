# ui/theme.py — SUKOT design system: shared CSS + base head/foot helpers
APP = "SUKOT"

FAVICON = "/assets/favicon.png"
LOGO = "/assets/logo.webp"
HERO = "/assets/hero.webp"
AVATAR = "/assets/avatar.webp"

ACCENT_PRESETS = {
    "crimson": ("255,61,84", "#ff3d54", "#ffb020"),
    "gold":    ("255,176,32", "#ffb020", "#ff3d54"),
    "purple":  ("168,85,247", "#a855f7", "#22d3ee"),
    "blue":    ("59,130,246", "#3b82f6", "#22d3ee"),
    "cyan":    ("34,211,238", "#22d3ee", "#a855f7"),
    "green":   ("16,185,129", "#10b981", "#ffb020"),
    "orange":  ("249,115,22", "#f97316", "#ffb020"),
    "pink":    ("236,72,153", "#ec4899", "#a855f7"),
    "teal":    ("20,184,166", "#14b8a6", "#ff3d54"),
}

def page_head(title: str, theme_color: str = "#0a0709", extra_css: str = "") -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="{theme_color}">
<meta name="robots" content="noindex">
<title>{title}</title>
<link rel="icon" type="image/png" href="{FAVICON}">
<style>{base_css()}</style>
<style>{extra_css}</style>
</head>
"""

GLYPHS = open("/home/z/my-project/work/sukot/app_assets/glyph_map.css", encoding="utf-8").read()

def base_css() -> str:
    return """
/* ---------------- SUKOT design system ---------------- */
@font-face{font-family:'tabler-icons';src:url(/assets/icons.woff2) format('woff2');font-weight:normal;font-style:normal;font-display:block}
@font-face{font-family:'Vazirmatn';src:url(/assets/vazir.woff2) format('woff2');font-weight:100 900;font-style:normal;font-display:swap}
""" + GLYPHS + """
:root{
  --accent-rgb:255,61,84;
  --accent:#ff3d54; --accent-d:#c21f36; --accent2:#ffb020;
  --good:#2fd18c; --warn:#ffb020; --bad:#ff4d5e;
  --bg:#0a0709; --bg2:#0f0a0c;
  --panel:rgba(26,17,20,.86); --panel-solid:#181013; --panel2:#22161a;
  --line:#2c2126; --line2:#3a2c32;
  --text:#f7eff1; --sub:#a99a9f; --sub2:#6f6268;
  --r-card:18px; --r-btn:12px; --r-inp:12px;
  --shadow:0 18px 44px rgba(0,0,0,.45);
  --glow:0 10px 30px rgba(var(--accent-rgb),.28);
  --font:'Vazirmatn','Segoe UI',system-ui,sans-serif;
  --font-scale:1; --density:14px; --anim:1;
}
[data-accent="gold"]{--accent-rgb:255,176,32;--accent:#ffb020;--accent-d:#d98f0f;--accent2:#ff3d54}
[data-accent="purple"]{--accent-rgb:168,85,247;--accent:#a855f7;--accent-d:#7c3aed;--accent2:#22d3ee}
[data-accent="blue"]{--accent-rgb:59,130,246;--accent:#3b82f6;--accent-d:#2563eb;--accent2:#22d3ee}
[data-accent="cyan"]{--accent-rgb:34,211,238;--accent:#22d3ee;--accent-d:#0891b2;--accent2:#a855f7}
[data-accent="green"]{--accent-rgb:16,185,129;--accent:#10b981;--accent-d:#059669;--accent2:#ffb020}
[data-accent="orange"]{--accent-rgb:249,115,22;--accent:#f97316;--accent-d:#c2570c;--accent2:#ffb020}
[data-accent="pink"]{--accent-rgb:236,72,153;--accent:#ec4899;--accent-d:#be2f77;--accent2:#a855f7}
[data-accent="teal"]{--accent-rgb:20,184,166;--accent:#14b8a6;--accent-d:#0f8a7d;--accent2:#ff3d54}

[data-theme="light"]{
  --bg:#f6f2f3; --bg2:#f1ebed;
  --panel:rgba(255,255,255,.92); --panel-solid:#fff; --panel2:#f6eff1;
  --line:#e7dadd; --line2:#dcc9cf;
  --text:#231519; --sub:#7d6b72; --sub2:#a5969c;
  --shadow:0 14px 34px rgba(120,40,55,.12);
}

*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:var(--font);font-size:calc(14px*var(--font-scale));
  background:
    radial-gradient(1100px 620px at 88% -10%, rgba(var(--accent-rgb),.16), transparent 60%),
    radial-gradient(900px 500px at -8% 108%, rgba(var(--accent-rgb),.10), transparent 55%),
    var(--bg);
  color:var(--text);min-height:100vh;-webkit-font-smoothing:antialiased;
}
[data-theme="light"] body{background:
  radial-gradient(1100px 620px at 88% -10%, rgba(var(--accent-rgb),.10), transparent 60%),
  var(--bg)}
a{color:var(--accent);text-decoration:none}
h1,h2,h3{margin:0;font-weight:800;letter-spacing:-.01em}
.ti{font-family:'tabler-icons'!important;speak:none;font-style:normal;font-weight:normal;line-height:1;display:inline-block;-webkit-font-smoothing:antialiased}

/* buttons — SUKOT custom family */
.btn{display:inline-flex;align-items:center;gap:8px;border:1px solid transparent;cursor:pointer;
  font-family:var(--font);font-weight:700;font-size:inherit;color:#fff;border-radius:var(--r-btn);
  padding:10px 18px;background:linear-gradient(135deg,rgba(var(--accent-rgb),1),var(--accent-d));
  box-shadow:var(--glow);transition:transform .15s ease, box-shadow .2s ease, filter .2s ease;user-select:none;white-space:nowrap}
.btn:hover{transform:translateY(-1px);filter:brightness(1.08)}
.btn:active{transform:translateY(0) scale(.985)}
.btn:disabled{opacity:.55;cursor:not-allowed;transform:none}
.btn.gold{background:linear-gradient(135deg,var(--accent2),#c98a10);box-shadow:0 10px 30px rgba(255,176,32,.25)}
.btn.ghost{background:transparent;color:var(--text);border-color:var(--line2);box-shadow:none}
.btn.ghost:hover{border-color:rgba(var(--accent-rgb),.6);color:var(--accent)}
.btn.soft{background:rgba(var(--accent-rgb),.12);color:var(--accent);box-shadow:none;border-color:rgba(var(--accent-rgb),.28)}
.btn.danger{background:linear-gradient(135deg,#ff4d5e,#b31d31);box-shadow:0 10px 26px rgba(255,77,94,.25)}
.btn.good{background:linear-gradient(135deg,#2fd18c,#149a63);box-shadow:0 10px 26px rgba(47,209,140,.22)}
.btn.sm{padding:7px 12px;font-size:.86em;border-radius:10px}
.btn.lg{padding:13px 26px;font-size:1.06em}
.btn.icon{padding:9px;border-radius:11px}
.btn .ti{font-size:1.1em}
.btn.block{width:100%;justify-content:center}
.iconbtn{width:38px;height:38px;display:inline-flex;align-items:center;justify-content:center;border-radius:11px;
  background:var(--panel2);color:var(--sub);border:1px solid var(--line);cursor:pointer;transition:.18s;font-size:17px}
.iconbtn:hover{color:var(--accent);border-color:rgba(var(--accent-rgb),.5);transform:translateY(-1px)}

.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:999px;font-size:.78em;font-weight:700;
  background:rgba(var(--accent-rgb),.12);color:var(--accent);border:1px solid rgba(var(--accent-rgb),.3)}
.chip.gray{background:rgba(150,140,145,.12);color:var(--sub);border-color:var(--line2)}
.chip.good{background:rgba(47,209,140,.13);color:var(--good);border-color:rgba(47,209,140,.35)}
.chip.warn{background:rgba(255,176,32,.13);color:var(--warn);border-color:rgba(255,176,32,.35)}
.chip.bad{background:rgba(255,77,94,.13);color:var(--bad);border-color:rgba(255,77,94,.35)}
.chip .ti{font-size:.95em}

/* inputs */
.inp,select.inp,textarea.inp{width:100%;padding:11px 14px;border-radius:var(--r-inp);border:1px solid var(--line2);
  background:rgba(0,0,0,.22);color:var(--text);font-family:var(--font);font-size:inherit;outline:none;transition:.2s}
[data-theme="light"] .inp{background:#fff}
.inp:focus{border-color:rgba(var(--accent-rgb),.7);box-shadow:0 0 0 3px rgba(var(--accent-rgb),.16)}
.inp::placeholder{color:var(--sub2)}
label.lb{display:block;font-size:.82em;font-weight:700;color:var(--sub);margin:12px 0 6px}
.chk{display:inline-flex;align-items:center;gap:8px;cursor:pointer;font-size:.9em;color:var(--sub)}
.chk input{accent-color:var(--accent);width:16px;height:16px}

/* cards & layout */
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r-card);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);box-shadow:var(--shadow);padding:var(--density)}
.card.pad-lg{padding:calc(var(--density)*1.4)}
.card h3{font-size:1.02em;display:flex;align-items:center;gap:8px;margin-bottom:12px}
.card h3 .ti{color:var(--accent)}
.grid{display:grid;gap:var(--density)}
.g2{grid-template-columns:repeat(2,1fr)}.g3{grid-template-columns:repeat(3,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}.g6{grid-template-columns:repeat(6,1fr)}
@media(max-width:980px){.g4,.g6{grid-template-columns:repeat(2,1fr)}.g3{grid-template-columns:repeat(2,1fr)}}
@media(max-width:620px){.g2,.g3,.g4,.g6{grid-template-columns:1fr}}

/* table */
.tbl{width:100%;border-collapse:collapse;font-size:.92em}
.tbl th{position:sticky;top:0;text-align:right;font-size:.78em;color:var(--sub);padding:10px 12px;
  border-bottom:1px solid var(--line2);background:var(--panel-solid);z-index:2}
.tbl td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:middle}
.tbl tr:hover td{background:rgba(var(--accent-rgb),.045)}
.tbl .acts{display:flex;gap:6px;flex-wrap:wrap}

/* toggle switch */
.sw{position:relative;width:42px;height:24px;border-radius:999px;background:var(--line2);cursor:pointer;transition:.2s;flex:none;border:none;padding:0}
.sw::after{content:'';position:absolute;top:3px;inset-inline-start:3px;width:18px;height:18px;border-radius:50%;background:#fff;transition:.2s}
.sw.on{background:linear-gradient(135deg,rgba(var(--accent-rgb),1),var(--accent-d))}
.sw.on::after{transform:translateX(-18px)}
[dir="ltr"] .sw.on::after{transform:translateX(18px)}

/* status dot */
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;background:var(--good);box-shadow:0 0 0 4px rgba(47,209,140,.18)}
.dot.bad{background:var(--bad);box-shadow:0 0 0 4px rgba(255,77,94,.16)}
.dot.warn{background:var(--warn);box-shadow:0 0 0 4px rgba(255,176,32,.16)}
.dot.pulse{animation:skpulse 1.8s infinite}
@keyframes skpulse{0%{box-shadow:0 0 0 0 rgba(47,209,140,.35)}70%{box-shadow:0 0 0 9px rgba(47,209,140,0)}100%{box-shadow:0 0 0 0 rgba(47,209,140,0)}}

/* toast */
#toasts{position:fixed;bottom:18px;inset-inline-start:18px;z-index:9999;display:flex;flex-direction:column;gap:9px}
.toast{background:var(--panel-solid);border:1px solid var(--line2);border-inline-start:3px solid var(--accent);
  border-radius:12px;padding:12px 16px;min-width:230px;max-width:340px;box-shadow:var(--shadow);font-size:.9em;
  animation:tin .25s ease;display:flex;gap:9px;align-items:center}
.toast.ok{border-inline-start-color:var(--good)}
.toast.err{border-inline-start-color:var(--bad)}
@keyframes tin{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}

/* modal / drawer */
.ovl{position:fixed;inset:0;background:rgba(4,2,3,.62);backdrop-filter:blur(6px);z-index:900;display:none;
  opacity:0;transition:opacity .2s}
.ovl.show{display:block;opacity:1}
.drawer{position:fixed;top:0;bottom:0;inset-inline-end:0;width:min(480px,94vw);background:var(--panel-solid);
  border-inline-start:1px solid var(--line2);z-index:910;transform:translateX(-105%);transition:transform .28s cubic-bezier(.2,.8,.2,1);
  overflow-y:auto;padding:20px}
[dir="ltr"] .drawer{transform:translateX(105%)}
.drawer.show{transform:none!important}
.drawer h3{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.center-modal{position:fixed;inset:0;z-index:910;display:none;align-items:center;justify-content:center;padding:18px}
.center-modal.show{display:flex}
.center-modal .card{width:min(460px,94vw);max-height:88vh;overflow:auto}

/* misc */
.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.spread{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.mut{color:var(--sub)} .mut2{color:var(--sub2)} .small{font-size:.82em}
.mono{font-family:'Vazirmatn',monospace;direction:ltr;unicode-bidi:embed}
.hr{height:1px;background:var(--line);border:0;margin:14px 0}
.kbd{font-family:monospace;font-size:.8em;border:1px solid var(--line2);border-radius:6px;padding:2px 7px;background:var(--panel2);color:var(--sub)}
::selection{background:rgba(var(--accent-rgb),.4)}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-thumb{background:var(--line2);border-radius:99px;border:2px solid transparent;background-clip:content-box}
::-webkit-scrollbar-track{background:transparent}
.ltr{direction:ltr;unicode-bidi:isolate}
.num{font-variant-numeric:tabular-nums}
[data-anim="0"] *{animation:none!important;transition:none!important}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

def toast_js() -> str:
    return """
function toast(msg, kind){
  let w = document.getElementById('toasts');
  if(!w){ w=document.createElement('div'); w.id='toasts'; document.body.appendChild(w); }
  const t=document.createElement('div'); t.className='toast '+(kind||''); 
  t.innerHTML='<span class="ti '+(kind==='ok'?'ti-circle-check':kind==='err'?'ti-alert-circle':'ti-info-circle')+'"></span><span></span>';
  t.lastElementChild.textContent=msg; w.appendChild(t);
  setTimeout(()=>{t.style.opacity='0';t.style.transform='translateY(6px)';setTimeout(()=>t.remove(),250)},3200);
}
"""
