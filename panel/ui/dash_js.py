# ui/dash_js.py — dashboard SPA logic
def js() -> str:
    return r"""
/* ================= SUKOT dashboard app ================= */
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const faN=s=>String(s).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]);
function hb(n){n=Number(n)||0;if(!n)return '۰ B';const u=['B','KB','MB','GB','TB','PB'];let i=0;while(Math.abs(n)>=1024&&i<u.length-1){n/=1024;i++}
 return faN((i?n.toFixed(1):n.toFixed(0)))+' '+u[i];}
async function api(path,opts={}){
  const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});
  if(r.status===401){location.href='/login';throw 0}
  let j={};try{j=await r.json()}catch(_){}
  if(!r.ok||j.ok===false)throw new Error(j.error||('HTTP '+r.status));
  return j;}
function copyText(t){navigator.clipboard.writeText(t).then(()=>toast('کپی شد ✔','ok'),()=>toast('کپی نشد','err'))}
async function confirmBox(msg){return window.confirm(msg)}
let ME={role:'owner'};

/* ---------- prefs ---------- */
const PRESETS={crimson:'#ff3d54',gold:'#ffb020',purple:'#a855f7',blue:'#3b82f6',cyan:'#22d3ee',green:'#10b981',orange:'#f97316',pink:'#ec4899',teal:'#14b8a6'};
let PREFS=JSON.parse(localStorage.getItem('sk_prefs')||'{}');
function savePrefs(){localStorage.setItem('sk_prefs',JSON.stringify(PREFS))}
function applyPrefs(){
  const h=document.documentElement;
  h.dataset.theme=PREFS.theme||'dark';
  h.dataset.accent=PREFS.accent||'crimson';
  h.dataset.anim=PREFS.anim??'1';
  h.style.setProperty('--font-scale',PREFS.font||'1');
  h.style.setProperty('--r-card',(PREFS.radius||'18')+'px');
  h.style.setProperty('--r-btn',Math.max(8,(PREFS.radius||'18')-6)+'px');
  if(PREFS.glow==='0'){h.style.setProperty('--glow','none');h.style.setProperty('--shadow','0 10px 26px rgba(0,0,0,.35)')}
  else{h.style.removeProperty('--glow');h.style.removeProperty('--shadow')}
  const btn=$('#themeBtn');if(btn)btn.querySelector('i,span').className='ti '+(PREFS.theme==='light'?'ti-moon':'ti-sun');
}
function setPref(k,v,el){
  PREFS[k]=v;savePrefs();applyPrefs();
  if(el&&el.closest('.seg')){[...el.closest('.seg').children].forEach(b=>b.classList.toggle('on',b===el))}
  if(el&&el.type==='checkbox')toast('ذخیره شد','ok');
}
function toggleTheme(){PREFS.theme=(PREFS.theme==='light'?'dark':'light');savePrefs();applyPrefs()}
function initSwatches(){
  const w=$('#swatches');if(!w)return;w.innerHTML='';
  for(const[k,c]of Object.entries(PRESETS)){
    const d=document.createElement('div');d.className='swatch'+((PREFS.accent||'crimson')===k?' on':'');
    d.title=k;d.innerHTML=`<i style="background:${c}"></i>`;
    d.onclick=()=>{PREFS.accent=k;savePrefs();applyPrefs();initSwatches();toast('رنگ اصلی: '+k,'ok')};
    w.appendChild(d);}
}

/* ---------- routing ---------- */
const TITLES=__TITLES__;
function go(pid,skipHash){
  $$('.pg').forEach(p=>p.classList.toggle('on',p.dataset.pg===pid));
  $$('#nav a').forEach(a=>a.classList.toggle('on',a.dataset.pg===pid));
  const t=TITLES[pid]||['SUKOT',''];
  $('#pageTitle').textContent=t[0];$('#pageSub').textContent=t[1];
  if(!skipHash)location.hash=pid;
  toggleSide(false);
  ({overview:loadOverview,links:loadLinks,clientmgr:loadClientMgr,categories:loadCats,subgroups:loadSubs,
    reports:()=>loadReports(REP_RANGE),nodes:loadNodes,vps:loadVps,tgproxy:loadTg,admins:loadAdmins,
    activity:loadActivity,messages:loadErrors,settings:loadSettings}[pid]||(()=>{}))();
}
window.addEventListener('hashchange',()=>{const p=location.hash.slice(1);if(TITLES[p])go(p,true)});

/* ---------- drawer ---------- */
function drawer(html,title){
  const d=$('#drawer');d.innerHTML=`<h3><span class="ti ti-pencil"></span> ${esc(title||'')}</h3>${html}`;
  $('#ovl').classList.add('show');d.classList.add('show');
}
function closeDrawer(){$('#ovl').classList.remove('show');$('#drawer').classList.remove('show')}
function closeModal(){document.querySelectorAll('.center-modal.show,.ovl.show').forEach(x=>{if(!x.id.includes('ovl')||true)x.classList.remove('show')});}
$('#ovl')?.addEventListener('click',()=>{closeDrawer();closeCmd()});

/* ---------- overview ---------- */
let OVT=null;
async function loadOverview(){
  clearTimeout(OVT);
  try{
    const[tel,st,con,act]=await Promise.all([api('/api/telemetry'),api('/stats'),api('/api/connections'),api('/api/activity')]);
    renderBiz(st);renderRes(tel);
    const health=Math.max(0,100-(tel.cpu*0.4+tel.ram*0.35+tel.disk*0.25));
    $('#healthGauge').style.setProperty('--p',health.toFixed(0));
    $('#healthVal').textContent=faN(health.toFixed(0))+'٪';
    $('#uptimeTxt').textContent=fmtUptime(tel.uptime_s);
    $('#platTxt').textContent=tel.platform||'—';
    $('#pubUrl').textContent=tel.public_url||'تنظیم نشده';
    $('#botState').innerHTML=st.bot_running?'<span class="st"><span class="dot pulse"></span> در حال اجرا</span>':'<span class="st"><span class="dot bad"></span> متوقف</span>';
    $('#tunnelsNow').textContent=faN(con.total||0);
    $('#ipsNow').textContent=faN(con.ips||0);
    $('#connList').innerHTML=(con.items||[]).slice(0,8).map(c=>
      `<div class="fitem"><span class="ti ti-plug-connected"></span><span>${esc(c.label)}</span><span class="t">${esc(c.ip||'—')} · ${hb(c.bytes)}</span></div>`).join('')||'<div class="empty small">اتصال فعالی نیست</div>';
    renderFeed($('#ovFeed'),act.items||[]);
    renderTopConfigs();
    OVT=setTimeout(()=>{if($('#pg-overview').classList.contains('on'))loadOverview()},8000);
  }catch(e){}
}
function renderBiz(st){
  const k=[['کل اینباندها','ti-link',st.links_total],['اینباند فعال','ti-circle-check',st.links_active],
   ['مجموع ترافیک','ti-arrows-exchange',hb(st.traffic_bytes)],['اتصال آنلاین','ti-plug-connected',st.online],
   ['گروه‌های ساب','ti-folders',st.subs],['ادمین‌ها','ti-users-group',st.admins]];
  $('#ovBiz').innerHTML=k.map(x=>`<div class="kpi"><div class="lab"><span class="ti ${x[1]}"></span>${x[0]}</div><div class="val">${faN(x[2]??0)}</div></div>`).join('');
}
function sparkHist(h){if(!h||!h.length)return '';const max=Math.max(...h,1);const pts=h.map((v,i)=>`${i*(100/(h.length-1||1))},${30-((v/max)*28).toFixed(1)}`).join(' ');
  return `<svg class="spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polygon class="fill" points="0,30 ${pts} 100,30"></polygon><polyline points="${pts}"/></svg>`;}
function renderRes(tel){
  const r=[['پردازنده','ti-cpu',tel.cpu,'%',tel.cpu_h],['حافظه RAM','ti-device-ram',tel.ram,'%',tel.ram_h],
    ['فضای ذخیره‌سازی','ti-database',tel.disk,'%',null],['شبکه','ti-network',tel.net_rate??0,'%',null]];
  $('#ovRes').innerHTML=r.map(x=>{
    const v=x[2]??0;const cls=v>=85?'bad':v>=60?'warn':'';
    const sub=(x[0]==='شبکه'&&tel.net_rate_s)?`<div class="small mut2 mt" style="margin-top:4px">${esc(tel.net_rate_s)}</div>`:'';
    return `<div class="kpi res"><div class="lab"><span class="ti ${x[1]}"></span>${x[0]}</div>
    <div class="val">${x[3]?faN(v.toFixed(0))+x[3]:x[2]}</div>
    <div class="bar ${cls}"><i style="width:${Math.min(100,v)}%"></i></div>${sub}${x[4]?sparkHist(x[4]):''}</div>`}).join('');
}
function fmtUptime(s){s=Math.floor(s||0);const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
  return faN((d?d+' روز ':'')+(h?h+' ساعت ':'')+m+' دقیقه')}
function renderFeed(el,items){
  el.innerHTML=items.slice(0,14).map(a=>{
    const ic=a.kind==='err'?'ti-alert-circle':a.kind==='act'?'ti-user':'ti-info-circle';
    return `<div class="fitem kind-${a.kind||''}"><span class="ti ${ic}"></span><span>${esc(a.text)}</span><span class="t">${esc((a.t||'').slice(11,16))}</span></div>`}).join('')
    ||'<div class="empty small">هنوز رویدادی ثبت نشده</div>';
}
async function renderTopConfigs(){
  try{const j=await api('/api/links');
    const top=j.items.sort((a,b)=>(b.used_bytes||0)-(a.used_bytes||0)).slice(0,6);
    $('#topConfigs').innerHTML=top.map(c=>`<div class="fitem"><span class="ti ti-trending-up"></span>
      <span>${esc(c.label)}</span><span class="t">${hb(c.used_bytes)} / ${c.limit_bytes?hb(c.limit_bytes):'♾'}</span></div>`).join('')
      ||'<div class="empty small">هنوز کانفیگی ساخته نشده — از «ساخت کلاینت» شروع کن</div>';
  }catch(e){}
}
async function botAction(a){try{await api('/api/bot/'+a,{method:'POST'});toast(a==='start'?'ربات شروع شد':'ربات متوقف شد','ok');loadOverview()}catch(e){toast(String(e.message||e),'err')}}

/* ---------- links ---------- */
let LINKS=[];
async function loadLinks(){
  try{const j=await api('/api/links');LINKS=j.items||[];renderLinks();
    const nb=$('#nb-links');if(nb)nb.textContent=faN(LINKS.length);
  }catch(e){toast(String(e.message||e),'err')}
}
function usageBar(c){const lim=c.limit_bytes||0,used=c.used_bytes||0;const p=lim?Math.min(100,used*100/lim):0;
  const cls=p>=90?'bad':p>=70?'warn':'';return `<div class="usage"><small>${hb(used)} / ${lim?hb(lim):'∞'}</small><div class="bar ${cls}"><i style="width:${p}%"></i></div></div>`}
function statusSt(c){
  if(c.status==='active')return '<span class="st"><span class="dot"></span> فعال</span>';
  if(c.status==='expired')return '<span class="st"><span class="dot bad"></span> منقضی</span>';
  if(c.status==='exhausted')return '<span class="st"><span class="dot warn"></span> حجم تمام</span>';
  return '<span class="st"><span class="dot warn"></span> غیرفعال</span>';
}
function onlineBadge(c){
  const n=c.online||0, ips=c.ips_online||0;
  return `<span class="onum ${n?'':'zero'}"><span class="dot ${n?'pulse':''}"></span>${faN(n)} نفر${ips?` · ${faN(ips)} IP`:''}</span>`;
}
function renderLinks(){
  const t=$('#linksTbl');
  if(!LINKS.length){t.innerHTML='<tr><td><div class="empty"><span class="ti ti-link"></span><b>هیچ اینباندی نیست</b><br>اولین کانفیگ اصلی‌ات را بساز</div></td></tr>';return}
  t.innerHTML='<thead><tr><th>نام</th><th>پروتکل</th><th>وضعیت</th><th>متصل‌شده‌ها</th><th>مصرف</th><th>انقضا</th><th>کلاینت</th><th>عملیات</th></tr></thead><tbody>'+
  LINKS.map(c=>`<tr>
    <td><b>${esc(c.label)}</b>${c.operator?`<br><span class="optag ${esc(c.operator)}">${esc(OPNAMES[c.operator]||c.operator)}</span>`:''}<br><small class="mut2 mono">${c.uuid.slice(0,8)}</small></td>
    <td><span class="chip gray">${esc(c.protocol)}</span>${c.live?'':'<br><small class="mut2">فقط لینک</small>'}</td>
    <td>${statusSt(c)}</td>
    <td>${onlineBadge(c)}</td>
    <td>${usageBar(c)}</td>
    <td class="small">${c.expires_at?esc(c.expires_at.slice(0,10)):'∞'}</td>
    <td class="num">${faN(c.clients_count||0)}</td>
    <td><div class="acts">
      <button class="btn sm soft" onclick="showSub('${c.uuid}')"><span class="ti ti-qrcode"></span> ساب و QR</button>
      <button class="btn sm ghost" onclick="showClients('${c.uuid}')"><span class="ti ti-users"></span> کلاینت‌ها</button>
      <button class="btn sm ghost" onclick="editLink('${c.uuid}')"><span class="ti ti-edit"></span></button>
      <button class="btn sm ghost" onclick="regen('${c.uuid}')" title="تعویض UUID"><span class="ti ti-replace"></span></button>
      <button class="btn sm ghost" onclick="resetUsage('${c.uuid}')" title="ریست حجم"><span class="ti ti-reload"></span></button>
      <button class="btn sm ghost" onclick="toggleLink('${c.uuid}')">${c.active?'<span class="ti ti-player-pause"></span>':'<span class="ti ti-player-play"></span>'}</button>
      <button class="btn sm danger" onclick="delLink('${c.uuid}')"><span class="ti ti-trash"></span></button>
    </div></td></tr>`).join('')+'</tbody>';
}
const OPNAMES={mci:'همراه اول',irancell:'ایرانسل',tci:'مخابرات',rightel:'رایتل',all:'همه'};
async function openLinkDrawer(){
  const[cats,ops]=await Promise.all([api('/api/categories').catch(()=>({items:[]})),api('/api/operators').catch(()=>({items:{}}))]);
  drawer(`
  <label class="lb">نام اینباند</label>
  <input class="inp" id="fLabel" placeholder="مثلاً SUKOT-پرو" maxlength="48">
  <label class="lb">پروتکل</label>
  <select class="inp" id="fProto">
    ${Object.entries(__PROTOS__).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}
  </select>
  <label class="lb">حجم (گیگ) — ۰ = نامحدود</label>
  <input class="inp" id="fVol" type="number" min="0" value="30" dir="ltr">
  <label class="lb">مدت (روز) — ۰ = بی‌نهایت</label>
  <input class="inp" id="fDays" type="number" min="0" value="30" dir="ltr">
  <label class="lb">سقف IP هم‌زمان — ۰ = بی‌مرز</label>
  <input class="inp" id="fIp" type="number" min="0" value="0" dir="ltr">
  <label class="lb">محدودیت سرعت (مگابیت) — ۰ = بی‌مرز</label>
  <input class="inp" id="fSpd" type="number" min="0" value="0" dir="ltr">
  <label class="lb">اپراتور</label>
  <select class="inp" id="fOp">${Object.entries(OPNAMES).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select>
  <label class="lb">دسته‌بندی</label>
  <select class="inp" id="fCat"><option value="">بدون دسته</option>${(cats.items||[]).map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('')}</select>
  <label class="lb">تعداد کانفیگ داخل ساب (۱ تا ۴۰)</label>
  <input class="inp" id="fCnt" type="number" min="1" max="40" value="1" dir="ltr">
  <label class="lb">یادداشت</label>
  <input class="inp" id="fNote" maxlength="120">
  <div class="row mt"><button class="btn" onclick="createLink()"><span class="ti ti-plus"></span> ساخت اینباند</button>
  <button class="btn ghost" onclick="closeDrawer()">انصراف</button></div>`,'اینباند جدید');
}
async function createLink(){
  const b={label:$('#fLabel').value,protocol:$('#fProto').value,limit_gb:Number($('#fVol').value||0),
    days:Number($('#fDays').value||0),ip_limit:Number($('#fIp').value||0),speed_mbit:Number($('#fSpd').value||0),
    operator:$('#fOp').value,category_id:$('#fCat').value,config_count:Number($('#fCnt').value||1),note:$('#fNote').value};
  try{const j=await api('/api/links',{method:'POST',body:JSON.stringify(b)});closeDrawer();toast('اینباند ساخته شد ✔','ok');
    if(j.sub_url)showSub(j.uuid);else loadLinks()}catch(e){toast(String(e.message||e),'err')}
}
async function editLink(uid){
  const j=await api(`/api/links/${uid}/info`);const c=j.item;
  drawer(`
  <label class="lb">نام</label><input class="inp" id="eLabel" value="${esc(c.label)}" maxlength="48">
  <label class="lb">حجم اضافه / تغییر (گیگ — خالی = بدون تغییر)</label>
  <input class="inp" id="eVol" type="number" min="0" placeholder="حجم جدید" dir="ltr">
  <label class="lb">تمدید (روز اضافه)</label>
  <input class="inp" id="eExt" type="number" min="0" placeholder="۰" dir="ltr">
  <label class="lb">انقضای مطلق (خالی = بدون تغییر)</label>
  <input class="inp" id="eExp" type="datetime-local" dir="ltr">
  <label class="lb">سقف IP</label><input class="inp" id="eIp" type="number" min="0" value="${c.ip_limit||0}" dir="ltr">
  <label class="lb">سرعت (مگابیت — ۰ بی‌مرز)</label><input class="inp" id="eSpd" type="number" min="0" value="${c.speed_mbit||0}" dir="ltr">
  <label class="chk mt"><input type="checkbox" id="eReset"> ریست مصرف در ذخیره</label>
  <div class="row mt"><button class="btn" onclick="saveLink('${uid}')"><span class="ti ti-device-floppy"></span> ذخیره</button>
  <button class="btn ghost" onclick="closeDrawer()">انصراف</button></div>`,'ویرایش اینباند');
}
async function saveLink(uid){
  const b={label:$('#eLabel').value,ip_limit:Number($('#eIp').value||0),speed_mbit:Number($('#eSpd').value||0)};
  if($('#eVol').value!==''&&$('#eVol').value!==null)b.set_limit_gb=Number($('#eVol').value);
  if(Number($('#eExt').value||0)>0)b.extend_days=Number($('#eExt').value);
  if($('#eExp').value)b.expires_at=new Date($('#eExp').value).toISOString();
  if($('#eReset').checked)b.reset_usage=true;
  try{await api(`/api/links/${uid}`,{method:'PATCH',body:JSON.stringify(b)});closeDrawer();toast('ذخیره شد ✔','ok');loadLinks()}catch(e){toast(String(e.message||e),'err')}
}
async function showSub(uid){
  const j=await api(`/api/links/${uid}/info`);const c=j.item;
  const link=c.link_uri||'';
  const sub=c.sub_url||'';
  drawer(`
  <div class="row" style="justify-content:space-between"><b>${esc(c.label)}</b><span class="chip ${c.status==='active'?'good':'bad'}">${c.status==='active'?'فعال':'غیرفعال'}</span></div>
  <div class="row mt" style="gap:7px">
    ${onlineBadge(c)}
    <span class="chip gray"><span class="ti ti-users"></span> ${faN(c.clients_count||0)} کلاینت</span>
    ${c.speed_mbit?`<span class="chip gray"><span class="ti ti-gauge"></span> ${faN(c.speed_mbit)}Mbps</span>`:''}
  </div>
  <div class="qrbox" id="qrBox"></div>
  <label class="lb">لینک اشتراک (برای اپ)</label>
  <div class="linkline"><code>${esc(sub)}</code><button class="btn sm" onclick="copyText('${esc(sub)}')"><span class="ti ti-copy"></span></button></div>
  <label class="lb">لینک اتصال</label>
  <div class="linkline"><code>${esc(link)}</code><button class="btn sm" onclick="copyText(this.previousElementSibling.textContent)"><span class="ti ti-copy"></span></button></div>
  <div class="row mt">
    <button class="btn soft" onclick="window.open('${esc(sub)}?web=1')"><span class="ti ti-external-link"></span> صفحه اشتراک</button>
    <button class="btn ghost" onclick="closeDrawer()">بستن</button>
  </div>`,'اشتراک و QR');
  $('#qrBox').innerHTML='<img src="'+qrSrc(sub)+'" width="210" alt="QR">';
}
function qrSrc(text){
  try{
    if(typeof qrcode==='function'){
      const q=qrcode(0,'M');q.addData(String(text||''));q.make();
      return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(q.createSvgTag(4,4));
    }
  }catch(e){}
  return 'https://api.qrserver.com/v1/create-qr-code/?size=210x210&data='+encodeURIComponent(String(text||''));
}
async function regen(uid){if(!await confirmBox('لینک (UUID) عوض شود؟ کلاینت‌ها هم آپدیت می‌شوند.'))return;
  try{await api(`/api/links/${uid}/regenerate`,{method:'POST'});toast('UUID جدید ساخته شد ✔','ok');loadLinks()}catch(e){toast(String(e.message||e),'err')}}
async function resetUsage(uid){try{await api(`/api/links/${uid}/action`,{method:'POST',body:JSON.stringify({action:'reset'})});toast('حجم مصرفی ریست شد ✔','ok');loadLinks()}catch(e){toast(String(e.message||e),'err')}}
async function toggleLink(uid){try{await api(`/api/links/${uid}/action`,{method:'POST',body:JSON.stringify({action:'toggle'})});loadLinks()}catch(e){toast(String(e.message||e),'err')}}
async function delLink(uid){if(!await confirmBox('این کانفیگ و کلاینت‌هایش حذف شوند؟'))return;
  try{await api(`/api/links/${uid}`,{method:'DELETE'});toast('حذف شد ✔','ok');loadLinks()}catch(e){toast(String(e.message||e),'err')}}

/* ---------- clients ---------- */
async function loadClientMgr(){
  try{const j=await api('/api/links');LINKS=j.items||[];
    const sel=$('#cmParent');sel.innerHTML=LINKS.map(c=>`<option value="${c.uuid}">${esc(c.label)}</option>`).join('')||'<option>اول یک اینباند بساز</option>';
    sel.onchange=()=>renderClients(sel.value);if(LINKS.length)renderClients(sel.value);
  }catch(e){}
}
async function renderClients(uid){
  if(!uid){$('#cmTbl').innerHTML='';return}
  try{const j=await api(`/api/links/${uid}/clients`);const items=j.items||[];
    $('#cmTbl').innerHTML=!items.length?'<tr><td><div class="empty small">بدون کلاینت</div></td></tr>':
    '<thead><tr><th>نام</th><th>مصرف</th><th>انقضا</th><th>عملیات</th></tr></thead><tbody>'+
    items.map(c=>`<tr><td><b>${esc(c.label)}</b></td><td>${usageBar(c)}</td>
      <td class="small">${c.expires_at?esc(c.expires_at.slice(0,10)):'∞'}</td>
      <td><div class="acts">
        <button class="btn sm soft" onclick="showSub('${c.uuid}')"><span class="ti ti-qrcode"></span></button>
        <button class="btn sm ghost" onclick="resetUsage('${c.uuid}')"><span class="ti ti-reload"></span></button>
        <button class="btn sm ghost" onclick="toggleLink('${c.uuid}')">${c.active?'<span class="ti ti-player-pause"></span>':'<span class="ti ti-player-play"></span>'}</button>
        <button class="btn sm danger" onclick="delClient('${uid}','${c.uuid}')"><span class="ti ti-trash"></span></button>
      </div></td></tr>`).join('')+'</tbody>';
  }catch(e){}
}
async function addClient(){
  const uid=$('#cmParent').value;if(!uid)return toast('اول اینباند انتخاب کن','err');
  const b={label:$('#cmName').value,limit_gb:Number($('#cmVol').value||0),days:Number($('#cmDays').value||0),ip_limit:Number($('#cmIp').value||0)};
  try{const j=await api(`/api/links/${uid}/clients`,{method:'POST',body:JSON.stringify(b)});
    toast('کلاینت ساخته شد ✔','ok');renderClients(uid);
    if(j.item)showSub(j.item.uuid);
  }catch(e){toast(String(e.message||e),'err')}
}
async function delClient(uid,cid){if(!await confirmBox('کلاینت حذف شود؟'))return;
  try{await api(`/api/links/${uid}/clients/${cid}`,{method:'DELETE'});toast('حذف شد ✔','ok');renderClients(uid)}catch(e){toast(String(e.message||e),'err')}}
function showClients(uid){go('clientmgr');setTimeout(()=>{$('#cmParent').value=uid;renderClients(uid)},350)}

/* ---------- categories ---------- */
async function loadCats(){
  try{const j=await api('/api/categories');const t=$('#catTbl');const items=j.items||[];
    t.innerHTML=!items.length?'<tr><td><div class="empty small">بدون دسته — یکی اضافه کن</div></td></tr>':
    '<thead><tr><th>نام</th><th>#</th><th></th></tr></thead><tbody>'+
    items.map(c=>`<tr><td><b>${esc(c.name)}</b></td><td class="num">${faN(c.number||0)}</td>
    <td><div class="acts"><button class="btn sm danger" onclick="delCat('${c.id}')"><span class="ti ti-trash"></span></button></div></td></tr>`).join('')+'</tbody>';
  }catch(e){}
}
async function addCat(){
  try{await api('/api/categories',{method:'POST',body:JSON.stringify({name:$('#catName').value})});
    $('#catName').value='';toast('دسته اضافه شد ✔','ok');loadCats()}catch(e){toast(String(e.message||e),'err')}}
async function delCat(id){if(!await confirmBox('دسته حذف شود؟'))return;
  try{await api(`/api/categories/${id}`,{method:'DELETE'});loadCats()}catch(e){toast(String(e.message||e),'err')}}

/* ---------- sub groups ---------- */
async function loadSubs(){
  try{const j=await api('/api/subs');const t=$('#subTbl');const items=j.items||[];
    const nb=$('#nb-subs');if(nb)nb.textContent=faN(items.length);
    t.innerHTML=!items.length?'<tr><td><div class="empty"><span class="ti ti-folders"></span><b>گروهی نیست</b><br>چند کانفیگ را در یک لینک ترکیب کن</div></td></tr>':
    '<thead><tr><th>نام</th><th>اعضا</th><th>رمز</th><th>لینک عمومی</th><th></th></tr></thead><tbody>'+
    items.map(s=>`<tr><td><b>${esc(s.name)}</b></td><td class="num">${faN(s.count||0)}</td>
    <td>${s.has_password?'<span class="chip warn">قفل</span>':'<span class="chip gray">آزاد</span>'}</td>
    <td><div class="linkline" style="min-width:220px"><code>${esc(s.public_url||'')}</code><button class="btn sm" onclick="copyText('${esc(s.public_url||'')}')"><span class="ti ti-copy"></span></button></div></td>
    <td><div class="acts"><button class="btn sm soft" onclick="window.open('${esc(s.public_url||'')}')"><span class="ti ti-external-link"></span></button>
    <button class="btn sm danger" onclick="delSub('${s.id}')"><span class="ti ti-trash"></span></button></div></td></tr>`).join('')+'</tbody>';
  }catch(e){}
}
async function openSubDrawer(){
  const j=await api('/api/links');LINKS=j.items||[];
  drawer(`
  <label class="lb">نام گروه</label><input class="inp" id="gName" placeholder="مثلاً بسته طلایی">
  <label class="lb">رمز (اختیاری)</label><input class="inp" id="gPw" dir="ltr" placeholder="خالی = بدون رمز">
  <label class="lb">انتخاب کانفیگ‌ها (۲ تا ۴۰)</label>
  <div style="max-height:250px;overflow:auto;border:1px solid var(--line);border-radius:12px;padding:9px">
  ${LINKS.map(c=>`<label class="chk" style="display:flex;padding:6px 4px"><input type="checkbox" class="gL" value="${c.uuid}"> ${esc(c.label)}</label>`).join('')||'<span class="mut small">کافی نیست</span>'}
  </div>
  <div class="row mt"><button class="btn" onclick="createSub()"><span class="ti ti-plus"></span> ساخت گروه</button>
  <button class="btn ghost" onclick="closeDrawer()">انصراف</button></div>`,'گروه ساب جدید');
}
async function createSub(){
  const ids=$$('.gL').filter(x=>x.checked).map(x=>x.value);
  if(ids.length<2)return toast('حداقل دو کانفیگ انتخاب کن','err');
  try{const j=await api('/api/subs',{method:'POST',body:JSON.stringify({name:$('#gName').value,password:$('#gPw').value,link_ids:ids})});
    closeDrawer();toast('گروه ساخته شد ✔','ok');copyText(j.item.public_url||'');loadSubs()}catch(e){toast(String(e.message||e),'err')}}
async function delSub(id){if(!await confirmBox('گروه حذف شود؟'))return;
  try{await api(`/api/subs/${id}`,{method:'DELETE'});loadSubs()}catch(e){toast(String(e.message||e),'err')}}

/* ---------- reports ---------- */
let REP_RANGE=7;
async function loadReports(days){
  try{const j=await api(`/api/reports/summary?days=${days||REP_RANGE}`);
    $('#repStats').innerHTML=[['کل کانفیگ‌ها','ti-link',j.total],['فعال','ti-circle-check',j.active],['گروه‌های ساب','ti-folders',j.subs],['ترافیک بازه','ti-arrows-exchange',hb(j.traffic)]]
      .map(x=>`<div class="kpi"><div class="lab"><span class="ti ${x[1]}"></span>${x[0]}</div><div class="val">${faN(x[2]??0)}</div></div>`).join('');
    const days_=(j.daily||[]);const max=Math.max(...days_.map(d=>d.traffic_bytes),1);
    $('#repChart').innerHTML=`<div class="row" style="align-items:flex-end;gap:6px;height:150px;padding-top:8px">`+
      days_.map(d=>`<div style="flex:1;min-width:9px;display:flex;flex-direction:column;justify-content:flex-end;height:100%" title="${d.day}: ${hb(d.traffic_bytes)}">
        <div style="background:linear-gradient(180deg,rgba(var(--accent-rgb),1),var(--accent-d));border-radius:6px 6px 2px 2px;height:${Math.max(3,(d.traffic_bytes/max*100)).toFixed(0)}%"></div></div>`).join('')+'</div>'+
      `<div class="row small mut2" style="justify-content:space-between"><span>${esc(days_[0]?.day||'')}</span><span>${esc(days_[days_.length-1]?.day||'')}</span></div>`;
    const top=j.top||[];
    $('#repTop').innerHTML=!top.length?'<tr><td><div class="empty small">داده‌ای نیست</div></td></tr>':
    '<thead><tr><th>نام</th><th>مصرف</th><th>سهم</th></tr></thead><tbody>'+top.map((c,i)=>`<tr>
      <td><b>${faN(i+1)}. ${esc(c.label)}</b></td><td>${hb(c.used_bytes)}</td>
      <td class="num">${faN(((c.used_bytes/(j.traffic||1))*100).toFixed(1))}٪</td></tr>`).join('')+'</tbody>';
  }catch(e){}
}
function repRange(d,el){REP_RANGE=d;[...$('#repRange').children].forEach(b=>b.classList.toggle('on',b===el));loadReports(d)}

/* ---------- nodes ---------- */
async function loadNodes(){
  try{const[j,tk]=await Promise.all([api('/api/nodes'),api('/api/node/token')]);
    $('#nodeToken').textContent=tk.token||'—';
    const t=$('#nodeTbl');const items=j.items||[];
    t.innerHTML=!items.length?'<tr><td><div class="empty small">نودی متصل نیست</div></td></tr>':
    '<thead><tr><th>نام</th><th>آدرس</th><th>وضعیت</th><th>تاخیر</th><th></th></tr></thead><tbody>'+
    items.map(n=>`<tr><td><b>${esc(n.name)}</b></td><td class="mono small">${esc(n.url)}</td>
    <td>${n.status==='online'?'<span class="st"><span class="dot pulse"></span> آنلاین</span>':'<span class="st"><span class="dot bad"></span> قطع</span>'}</td>
    <td class="num">${n.latency_ms?faN(n.latency_ms)+'ms':'—'}</td>
    <td><div class="acts"><button class="btn sm ghost" onclick="checkNode('${n.id}')"><span class="ti ti-heartbeat"></span></button>
    <button class="btn sm danger" onclick="delNode('${n.id}')"><span class="ti ti-trash"></span></button></div></td></tr>`).join('')+'</tbody>';
  }catch(e){}
}
async function addNode(){
  try{await api('/api/nodes',{method:'POST',body:JSON.stringify({name:$('#ndName').value,url:$('#ndUrl').value,token:$('#ndTok').value})});
    toast('نود اضافه شد ✔','ok');loadNodes()}catch(e){toast(String(e.message||e),'err')}}
async function checkNode(id){try{const j=await api(`/api/nodes/${id}/check`,{method:'POST'});toast(j.status==='online'?'آنلاین ✔':'قطع — '+String(j.error||''),'ok')}catch(e){toast(String(e.message||e),'err')}loadNodes()}
async function delNode(id){if(!await confirmBox('نود حذف شود؟'))return;try{await api(`/api/nodes/${id}`,{method:'DELETE'});loadNodes()}catch(e){}}

/* ---------- vps ---------- */
async function loadVps(){
  try{const j=await api('/api/vps');const items=j.items||[];
    $('#vpsList').innerHTML=!items.length?'<div class="card" style="grid-column:1/-1"><div class="empty"><span class="ti ti-server-cog"></span><b>سروری ثبت نشده</b><br>اولین سرور VPS‌ات را اضافه کن</div></div>':
    items.map(s=>`<div class="card">
      <div class="spread"><h3 style="margin:0"><span class="ti ti-server"></span> ${esc(s.name)}</h3>
        <span class="chip gray">${s.mode==='single'?'🎯 پورت تکی':'🌐 چندپورتی'}</span></div>
      <div class="mini-stat mt"><span class="mut">هاست</span><b class="mono">${esc(s.host)}</b></div>
      <div class="mini-stat"><span class="mut">SNI</span><b class="mono">${esc(s.sni||'—')}</b></div>
      <div class="mini-stat"><span class="mut">پورت‌ها</span><b class="mono small">${esc(Object.entries(s.ports||{}).map(([k,v])=>k+':'+v).join(' · ')||'—')}</b></div>
      <div class="wrapgap mt">
        <button class="btn sm" onclick="vpsScan('${s.id}')"><span class="ti ti-scan"></span> اسکن پورت</button>
        <button class="btn sm soft" onclick="vpsSni('${s.id}')"><span class="ti ti-radar-2"></span> اسکن SNI</button>
        <button class="btn sm ghost" onclick="vpsCheck('${s.id}')"><span class="ti ti-heartbeat"></span> تست</button>
        <button class="btn sm ghost" onclick="vpsFiles('${s.id}')"><span class="ti ti-download"></span> نصب و کانفیگ</button>
        <button class="btn sm danger" onclick="vpsDel('${s.id}')"><span class="ti ti-trash"></span></button>
      </div>
      <div id="vpsout-${s.id}" class="small mut mt"></div>
    </div>`).join('');
  }catch(e){}
}
async function openVpsDrawer(){
  drawer(`
  <label class="lb">نام سرور</label><input class="inp" id="vName" placeholder="مثلاً آلمان-۱">
  <label class="lb">هاست / IP</label><input class="inp" id="vHost" dir="ltr" placeholder="1.2.3.4">
  <label class="lb">حالت</label><div class="seg"><button class="on" id="vSingle" onclick="this.classList.add('on');$('#vMulti').classList.remove('on')">🎯 پورت تکی</button>
  <button id="vMulti" onclick="this.classList.add('on');$('#vSingle').classList.remove('on')">🌐 چندپورتی</button></div>
  <label class="lb">پورت‌ها (با کاما)</label><input class="inp" id="vPorts" dir="ltr" placeholder="443, 8443">
  <label class="lb">SNI پیش‌فرض</label><input class="inp" id="vSni" dir="ltr" value="www.speedtest.net">
  <div class="row mt"><button class="btn" onclick="vpsAdd()"><span class="ti ti-plus"></span> ثبت سرور</button>
  <button class="btn ghost" onclick="closeDrawer()">انصراف</button></div>`,'ثبت سرور VPS');
}
async function vpsAdd(){
  const mode=$('#vSingle').classList.contains('on')?'single':'multi';
  const ports={};$('#vPorts').value.split(',').map(x=>x.trim()).filter(x=>x).forEach((p,i)=>ports['vless-reality-'+(i+1)]=Number(p)||443);
  try{await api('/api/vps',{method:'POST',body:JSON.stringify({name:$('#vName').value,host:$('#vHost').value,mode,ports,sni:$('#vSni').value})});
    closeDrawer();toast('سرور ثبت شد — کلید Reality ساخته شد ✔','ok');loadVps()}catch(e){toast(String(e.message||e),'err')}
}
async function vpsScan(id){try{const j=await api('/api/vps/scan',{method:'POST',body:JSON.stringify({sid:id})});
  $('#vpsout-'+id).innerHTML='🔍 باز: <b>'+j.open.map(x=>faN(x)).join('، ')+'</b> — '+Object.entries(j.results).map(([p,st])=>faN(p)+':'+({open:'✅',closed:'⛔',filtered:'🜁',skipped:'—'})[st]||st).join(' · ');}catch(e){toast(String(e.message||e),'err')}}
async function vpsSni(id){try{const j=await api('/api/vps/sni-scan',{method:'POST',body:JSON.stringify({sid:id})});
  $('#vpsout-'+id).innerHTML='📡 بهترین SNI‌ها: '+j.ranked.slice(0,4).map(r=>`<b>${esc(r.sni)}</b> (${faN(r.score)})`).join(' · ');}catch(e){toast(String(e.message||e),'err')}}
async function vpsCheck(id){try{const j=await api(`/api/vps/${id}/check`,{method:'POST'});toast(j.ok?'سرور پاسخ داد ✔':'بی‌پاسخ — '+String(j.error||''),'ok')}catch(e){toast(String(e.message||e),'err')}}
async function vpsDel(id){if(!await confirmBox('سرور حذف شود؟'))return;try{await api(`/api/vps/${id}`,{method:'DELETE'});loadVps()}catch(e){}}
async function vpsFiles(id){
  try{const j=await api(`/api/vps/${id}`);const s=j.item;
  drawer(`
  <p class="small mut">این سه فایل برای سرور <b>${esc(s.name)}</b> آماده است. روی VPS فقط اسکریپت نصب را اجرا کن؛ بقیه‌اش خودکار است.</p>
  <label class="lb">۱) اسکریپت نصب</label>
  <div class="linkline"><code>${esc(j.install_url)}</code><button class="btn sm" onclick="copyText(this.previousElementSibling.textContent)"><span class="ti ti-copy"></span></button></div>
  <label class="lb">۲) کانفیگ Xray (Reality)</label>
  <div class="linkline"><code>${esc(j.xray_url)}</code><button class="btn sm" onclick="copyText(this.previousElementSibling.textContent)"><span class="ti ti-copy"></span></button></div>
  ${s.wg_enabled?`<label class="lb">۳) WireGuard</label><div class="linkline"><code>${esc(j.wg_url)}</code><button class="btn sm" onclick="copyText(this.previousElementSibling.textContent)"><span class="ti ti-copy"></span></button></div>`:''}
  <div class="hr"></div>
  <label class="lb">دستور نصب روی سرور</label>
  <div class="linkline"><code>bash <(curl -fsSL ${esc(j.install_url)})</code><button class="btn sm" onclick="copyText(this.previousElementSibling.textContent)"><span class="ti ti-copy"></span></button></div>
  `,'نصب روی VPS');
  }catch(e){toast(String(e.message||e),'err')}}

/* ---------- tgproxy ---------- */
async function loadTg(){
  try{const j=await api('/api/tgproxy');
    const s=j.stats||{};
    $('#tgStats').innerHTML=[['کل پروکسی‌ها','ti-box',s.total],['فعال','ti-circle-check',s.active],['اتصال زنده','ti-plug-connected',s.live]]
      .map(x=>`<div class="kpi"><div class="lab"><span class="ti ${x[1]}"></span>${x[0]}</div><div class="val">${faN(x[2]??0)}</div></div>`).join('');
    $('#tgMode').textContent=(j.running&&j.running.shared)?'تک‌پورت · روی پورت پنل':(j.running&&j.running.mtproto)?'پورت مستقل':'خاموش';
    $('#tgTips').textContent=(j.errors&&Object.keys(j.errors).length)?Object.values(j.errors).join(' · '):'';
    $('#tgList').innerHTML=(j.items||[]).map(p=>`
    <div class="card">
      <div class="spread"><h3 style="margin:0"><span class="ti ti-brand-telegram"></span> ${esc(p.label)}</h3>
      <span class="chip ${p.usable?'good':'bad'}">${p.usable?'فعال':'غیرفعال'}</span></div>
      <div class="mini-stat mt"><span class="mut">حجم مصرفی</span><b>${hb(p.used_bytes)} / ${p.limit_bytes?hb(p.limit_bytes):'∞'}</b></div>
      <div class="mini-stat"><span class="mut">اتصال</span><b>${faN(p.live||0)}${p.max_conn?' / '+faN(p.max_conn):''}</b></div>
      <div class="qrbox" style="padding:8px"><img src="https://api.qrserver.com/v1/create-qr-code/?size=170x170&data=${encodeURIComponent(p.links.web||p.links.tg)}" width="170"></div>
      <div class="wrapgap">
        <a class="btn sm" href="${esc(p.links.tg)}"><span class="ti ti-send"></span> اتصال در تلگرام</a>
        <button class="btn sm ghost" onclick="copyText('${esc(p.links.tg)}')"><span class="ti ti-copy"></span></button>
        <button class="btn sm ghost" onclick="tgPatch('${p.id}','enabled',${!p.enabled})">${p.enabled?'⛔ خاموش':'✅ روشن'}</button>
        <button class="btn sm ghost" onclick="tgRegen('${p.id}')"><span class="ti ti-replace"></span> secret جدید</button>
        <button class="btn sm ghost" onclick="tgReset('${p.id}')"><span class="ti ti-reload"></span> ریست</button>
        <button class="btn sm danger" onclick="tgDel('${p.id}')"><span class="ti ti-trash"></span></button>
      </div>
    </div>`).join('')||'<div class="card" style="grid-column:1/-1"><div class="empty small">پروکسی‌ای نیست — «خودکار» را بزن</div></div>';
  }catch(e){}
}
async function tgAuto(){try{const j=await api('/api/tgproxy/auto',{method:'POST',body:'{}'});
  toast(j.healthy?'پروکسی خودکار آماده است ✔':'با هشدار انجام شد — تست سلامت را ببین',j.healthy?'ok':'err');
  if(j.px)copyText(j.px.links.tg);loadTg()}catch(e){toast(String(e.message||e),'err')}}
async function tgCreate(){try{const j=await api('/api/tgproxy',{method:'POST',body:JSON.stringify({kind:'mtproto',label:'پروکسی '+new Date().toLocaleTimeString('fa-IR')})});
  toast('پروکسی ساخته شد ✔','ok');loadTg()}catch(e){toast(String(e.message||e),'err')}}
async function tgPatch(id,k,v){try{await api(`/api/tgproxy/${id}`,{method:'PATCH',body:JSON.stringify({[k]:v})});loadTg()}catch(e){toast(String(e.message||e),'err')}}
async function tgRegen(id){try{const j=await api(`/api/tgproxy/${id}/regenerate`,{method:'POST'});copyText(j.item.links.tg);toast('secret جدید کپی شد ✔','ok');loadTg()}catch(e){toast(String(e.message||e),'err')}}
async function tgReset(id){try{await api(`/api/tgproxy/${id}/reset`,{method:'POST'});toast('ریست شد ✔','ok');loadTg()}catch(e){toast(String(e.message||e),'err')}}
async function tgDel(id){if(!await confirmBox('پروکسی حذف شود؟'))return;try{await api(`/api/tgproxy/${id}`,{method:'DELETE'});loadTg()}catch(e){}}
async function tgSelftest(){try{const j=await api('/api/tgproxy-selftest');
  $('#tgTips').textContent=j.tips&&j.tips.length?j.tips.join(' · '):'سلامت ✓ — دیتاسنترها در دسترس‌اند و سرور در حال اجراست.';toast('تست انجام شد','ok')}catch(e){toast(String(e.message||e),'err')}}

/* ---------- admins ---------- */
const PERMS=[['dashboard','داشبورد'],['inbound_create','ساخت اینباند'],['inbound_edit','ویرایش اینباند'],['inbound_delete','حذف اینباند'],
['client_create','ساخت کلاینت'],['client_edit','ویرایش کلاینت'],['client_delete','حذف کلاینت'],['client_reset','ریست کلاینت'],
['subscription','اشتراک‌ها'],['categories','دسته‌بندی'],['subgroups','گروه‌های ساب'],['reports','گزارش‌ها'],['nodes','نودها'],['vps','سرورها'],['tgproxy','پروکسی تلگرام'],['activity','فعالیت‌ها'],['messages','پیام‌ها']];
async function loadAdmins(){
  if(ME.role!=='owner'){$('#pg-admins').innerHTML='<div class="card"><div class="empty"><span class="ti ti-lock"></span><b>فقط مالک پنل</b> به این بخش دسترسی دارد</div></div>';return}
  try{const[j,reqs]=await Promise.all([api('/api/admins'),api('/api/admin-requests')]);
    const items=j.items||[];
    $('#admStats').innerHTML=[['حساب مدیریتی','ti-crown',1],['حساب فعال','ti-user-shield',items.length],['درخواست باز','ti-inbox',(reqs.items||[]).length]]
      .map(x=>`<div class="kpi"><div class="lab"><span class="ti ${x[1]}"></span>${x[0]}</div><div class="val">${faN(x[2]??0)}</div></div>`).join('');
    $('#admTbl').innerHTML=items.map(a=>`<tr>
      <td><b>${esc(a.admin_id)}</b>${a.role==='owner'?' <span class="chip">مالک</span>':''}</td>
      <td>${a.active?'<span class="st"><span class="dot"></span> فعال</span>':'<span class="st"><span class="dot warn"></span> غیرفعال</span>'}</td>
      <td class="small">${faN((a.permissions||[]).length)} مجوز</td>
      <td><div class="acts">
        ${a.role!=='owner'?`<button class="btn sm ghost" onclick="editAdmin('${esc(a.admin_id)}')"><span class="ti ti-edit"></span></button>
        <button class="btn sm danger" onclick="delAdmin('${esc(a.admin_id)}')"><span class="ti ti-trash"></span></button>`:'<span class="mut2 small">—</span>'}
      </div></td></tr>`).join('')||'<tr><td><div class="empty small">فقط شما هستید — ادمین بسازید</div></td></tr>';
    $('#admReqs').innerHTML=(reqs.items||[]).map(r=>`<div class="fitem"><span class="ti ti-user-plus"></span>
      <span><b>${esc(r.name)}</b> — <span class="mono small">${esc(r.tg)}</span>${r.note?`<br><small class="mut">${esc(r.note)}</small>`:''}</span>
      <span class="row" style="margin-inline-start:auto">
        <button class="btn sm good" onclick="reqAct('${r.id}','approve')">تایید و ساخت ادمین</button>
        <button class="btn sm danger" onclick="reqAct('${r.id}','reject')">رد</button></span></div>`).join('')
      ||'<div class="empty small">درخواستی نیست</div>';
  }catch(e){}
}
function editAdmin(id){
  const chips=PERMS.map(([k,l])=>`<label class="chk" style="display:flex;padding:5px 3px"><input type="checkbox" class="pChk" value="${k}" ${k==='dashboard'?'checked':''}> ${l}</label>`).join('');
  drawer(`<label class="lb">نام کاربری</label><input class="inp" id="aUser" value="${esc(id)}" dir="ltr" ${id?'disabled':''}>
  ${id?'':'<label class="lb">رمز عبور</label><input class="inp" id="aPass" dir="ltr" type="password">'}
  <label class="lb">مجوزها</label>
  <div style="max-height:230px;overflow:auto;border:1px solid var(--line);border-radius:12px;padding:9px">${chips}</div>
  <div class="row mt"><button class="btn" onclick="saveAdmin('${esc(id)}')"><span class="ti ti-device-floppy"></span> ذخیره</button>
  <button class="btn ghost" onclick="closeDrawer()">انصراف</button></div>`,'ادمین');
}
async function saveAdmin(id){
  const perms=$$('.pChk').filter(x=>x.checked).map(x=>x.value);
  try{
    if(id)await api(`/api/admins/${encodeURIComponent(id)}`,{method:'PATCH',body:JSON.stringify({permissions:perms})});
    else await api('/api/admins',{method:'POST',body:JSON.stringify({admin_id:$('#aUser').value,password:$('#aPass').value,permissions:perms})});
    closeDrawer();toast('ذخیره شد ✔','ok');loadAdmins()}catch(e){toast(String(e.message||e),'err')}
}
async function delAdmin(id){if(!await confirmBox('حساب ادمین حذف شود؟'))return;
  try{await api(`/api/admins/${encodeURIComponent(id)}`,{method:'DELETE'});loadAdmins()}catch(e){toast(String(e.message||e),'err')}}
async function reqAct(id,act){try{await api(`/api/admin-requests/${id}/${act}`,{method:'POST'});toast(act==='approve'?'ادمین ساخته شد ✔':'رد شد','ok');loadAdmins()}catch(e){toast(String(e.message||e),'err')}}

/* ---------- activity / messages ---------- */
async function loadActivity(){try{const j=await api('/api/activity');renderFeed($('#actFeed'),j.items||[])}catch(e){}}
async function loadErrors(){try{const j=await api('/api/errors');const items=j.items||[];
  const nb=$('#nb-errors');if(nb)nb.textContent=faN(items.length);
  $('#errFeed').innerHTML=items.slice(0,60).map(e=>`<div class="fitem kind-err"><span class="ti ti-alert-circle"></span>
    <span>${esc(e.text)}<br><small class="mut2">${esc(e.source||'')} · ${esc((e.t||'').slice(0,19).replace('T',' '))}</small></span></div>`).join('')
    ||'<div class="empty"><span class="ti ti-circle-check"></span><b>بدون خطا</b></div>';}catch(e){}}
async function clearErrors(){try{await api('/api/errors/clear',{method:'POST'});toast('پاک شد ✔','ok');loadErrors()}catch(e){}}

/* ---------- settings ---------- */
async function loadSettings(){
  try{const j=await api('/api/settings');const s=j.settings||{};
    $('#setPubUrl').value=s.public_base_url||'';$('#setSup').value=s.support_username||'@SUKOT1344';
    $('#setChan').value=s.channel_username||'SUKOT1344';$('#setBotTok').value=s.bot_token||'';$('#setBotIds').value=s.bot_admin_ids||'';
    $('#secUser').placeholder='نام کاربری فعلی: '+(ME.username||'');
    initSwatches();
    $$('#setTheme button').forEach(b=>b.classList.toggle('on',(b.dataset.t)===(PREFS.theme||'dark')));
    $$('#setRadius button').forEach(b=>b.classList.toggle('on',(b.dataset.r)===(PREFS.radius||'18')));
    $('#setFont').value=PREFS.font||'1';$('#setAnim').checked=(PREFS.anim??'1')==='1';$('#setGlow').checked=(PREFS.glow??'1')==='1';
  }catch(e){}
}
async function saveGeneral(){
  try{await api('/api/settings',{method:'POST',body:JSON.stringify({public_base_url:$('#setPubUrl').value,
    support_username:$('#setSup').value,channel_username:$('#setChan').value})});
    toast('ذخیره شد ✔','ok')}catch(e){toast(String(e.message||e),'err')}}
async function saveBot(){
  try{await api('/api/settings',{method:'POST',body:JSON.stringify({bot_token:$('#setBotTok').value,bot_admin_ids:$('#setBotIds').value})});
    await api('/api/bot/start',{method:'POST'});toast('ربات ذخیره و شروع شد ✔','ok')}catch(e){toast(String(e.message||e),'err')}}
async function changeUsername(){
  try{await api('/api/change-username',{method:'POST',body:JSON.stringify({username:$('#secUser').value})});
    toast('نام کاربری عوض شد ✔','ok')}catch(e){toast(String(e.message||e),'err')}}
async function changePassword(){
  try{await api('/api/change-password',{method:'POST',body:JSON.stringify({old_password:$('#secOld').value,new_password:$('#secNew').value})});
    $('#secOld').value='';$('#secNew').value='';toast('رمز عوض شد ✔','ok')}catch(e){toast(String(e.message||e),'err')}}
async function revokeSessions(){
  try{const j=await api('/api/security/revoke-other-sessions',{method:'POST'});
    toast(faN(j.revoked||0)+' نشست دیگر لغو شد ✔','ok')}catch(e){toast(String(e.message||e),'err')}}
async function testSupport(){const u=$('#setSup').value||'@SUKOT1344';window.open('https://t.me/'+u.replace('@',''),'_blank')}

/* ---------- command palette ---------- */
function openCmd(){$('#cmdk').classList.add('show');$('#cmdkInp').value='';renderCmd('');$('#cmdkInp').focus()}
function closeCmd(){$('#cmdk').classList.remove('show')}
$('#cmdk')?.addEventListener('click',e=>{if(e.target.id==='cmdk')closeCmd()});
$('#cmdkInp')?.addEventListener('input',e=>renderCmd(e.target.value));
function renderCmd(q){
  q=(q||'').trim().toLowerCase();
  const pages=Object.entries(TITLES).map(([k,v])=>({t:'صفحه · '+v[0],ic:'ti-layout-dashboard',go:()=>go(k)}));
  const links_=LINKS.map(c=>({t:'کانفیگ · '+c.label,ic:'ti-link',go:()=>showSub(c.uuid)}));
  const all=[...pages,...links_].filter(x=>!q||x.t.toLowerCase().includes(q));
  $('#cmdkList').innerHTML=all.slice(0,12).map((x,i)=>`<div onclick="(${x.go.toString()})();closeCmd()"><span class="ti ${x.ic}"></span> ${esc(x.t)}</div>`).join('')
    ||'<div class="mut small" style="padding:12px">چیزی پیدا نشد</div>';
}
document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCmd()}
  if(e.key==='Escape'){closeCmd();closeDrawer()}
});

/* ---------- boot ---------- */
function logout(){fetch('/logout').then(()=>location.href='/login')}
function toggleSide(force){const sb=$('#sidebar');const open=force!==undefined?force:!sb.classList.contains('open');
  sb.classList.toggle('open',open);$('#sideovl').classList.toggle('show',open)}
/* topbar Persian clock */
(function(){
  const el=document.getElementById('tbClock'); if(!el) return;
  const df=new Intl.DateTimeFormat('fa-IR-u-ca-persian',{weekday:'long',day:'numeric',month:'long'});
  function tick(){const n=new Date();
    el.querySelector('span:last-child').textContent=df.format(n)+' · '+n.toLocaleTimeString('fa-IR',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});}
  tick();setInterval(tick,1000);
})();
async function boot(){
  applyPrefs();
  try{ME=await api('/api/me')}catch(e){location.href='/login';return}
  $('#whoName').textContent=ME.username||'مدیر';
  $('#whoRole').textContent=ME.role==='owner'?'مالک پنل':'ادمین';
  if(ME.role!=='owner'){['admins','settings','nodes'].forEach(p=>{const a=$(`#nav a[data-pg="${p}"]`);if(a)a.style.display='none'})}
  const h=location.hash.slice(1)||'overview';
  go(TITLES[h]?h:'overview',true);
}
boot();
"""
