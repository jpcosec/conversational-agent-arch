/* Usuarios (/users, frontends/profiling/index.html). */
const FICHAS={},USER_DATA=[],FAM_COLORS={self:'#7cba7c',domain:'#7fb3d5',conversation:'#e6a85c',user:'#c97db9'};
let CURRENT_USER=null,CURRENT_VIEW='profile';

function emptyState(icon,text){return '<div class="empty-state"><span class="empty-state-icon">'+icon+'</span>'+text+'</div>'}
function tooltips(){if(window.initGlossaryTooltips)initGlossaryTooltips()}

async function load(){
 try{
  var resp=await fetch('/api/profiles'),data=await resp.json();
  (data.users||[]).forEach(u=>{USER_DATA.push(u)});
  Object.assign(FICHAS,data.fichas||{});
  renderUserbar();
  if(USER_DATA.length)select(0);
 }catch(e){document.getElementById('userbar').innerHTML=emptyState('⚠️','Error al cargar: '+esc(e.message))}}
load();

function renderUserbar(){
 var bar=document.getElementById('userbar');bar.innerHTML='';
 if(!USER_DATA.length){bar.innerHTML=emptyState('👤','Sin usuarios todavía');return}
 USER_DATA.forEach((u,i)=>{
  var el=document.createElement('div');el.className='user-chip'+(i===CURRENT_USER?' active':'');el.dataset.idx=i;el.setAttribute('data-testid','user-item-'+u.user_id);el.setAttribute('data-user-id',u.user_id);
  el.innerHTML='<div class="chip-main"><div class="chip-name">'+esc(u.external_id||'User #'+u.user_id)+'</div><div class="chip-id">#'+u.user_id+(u.last_active?' · '+u.last_active.slice(0,10):'')+'</div></div><div class="chip-meta">'+(u.traits_count||u.traits?.length||0)+' rasgos<br/>'+(u.total_turns||0)+' turnos</div>';
  el.onclick=()=>select(i);bar.appendChild(el)})}

function select(i){
 CURRENT_USER=i;renderUserbar();var u=USER_DATA[i];if(!u){document.getElementById('userDetailHeader').textContent='Selecciona un usuario';document.getElementById('detailPanel').innerHTML=emptyState('👤','Sin datos');return}
 // innerHTML, no textContent: la cadena lleva un <span> de markup. El
 // external_id va escapado con esc() y el resto son numeros.
 document.getElementById('userDetailHeader').innerHTML=esc(u.external_id||'User #'+u.user_id)+' <span>· '+(u.traits?.length||0)+' <em data-tooltip="trait">rasgos</em> · '+(u.conversations?.length||0)+' conversaciones</span>';
 switchView(CURRENT_VIEW)}

function switchView(view){
 CURRENT_VIEW=view;document.querySelectorAll('.users-view-selector .tab').forEach(b=>b.classList.toggle('active',b.dataset.view===view))
 // El panel es flex-row solo para el perfil (columna KPIs + columna rasgos).
 // Eventos y conversaciones inyectan una lista vertical: sin esto cada item
 // se vuelve una columna estirada a toda la altura.
 document.getElementById('detailPanel').classList.toggle('as-list',view!=='profile')
 var u=USER_DATA[CURRENT_USER];if(!u)return;
 if(view==='profile')renderProfile(u);
 else if(view==='events')renderEvents(u);
 else if(view==='conversations')renderConversations(u);
 tooltips()}

// ---- datos aleatorios pero deterministas por usuario (seed = user_id) ----
function rndSeries(u,salt,n,min,max){
 var seed=((u.user_id||1)*7+(salt||0))>>>0;
 var out=[];
 for(var i=0;i<n;i++){
  seed=(seed*9301+49297)%233280;
  var r=seed/233280;
  out.push(Math.round(min+r*(max-min)));
 }
 return out;
}
// ---- grafico de barras SVG inline ----
function svgBars(vals,opts){
 opts=opts||{};
 var W=opts.w||280,H=opts.h||110,pad=opts.pad||18,gap=opts.gap||6;
 var n=vals.length,max=Math.max.apply(null,vals.concat([1]));
 var innerW=W-pad*2,innerH=H-pad*2;
 var bw=(innerW-gap*(n-1))/n;
 var labels=opts.labels||[];
 var bars='';
 for(var i=0;i<n;i++){
  var bh=Math.max(2,Math.round(vals[i]/max*innerH));
  var x=pad+i*(bw+gap),y=pad+innerH-bh;
  bars+='<rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+bh+'" rx="2" fill="url(#barGrad)"></rect>';
  bars+='<text x="'+(x+bw/2).toFixed(1)+'" y="'+(pad+innerH+11)+'" font-size="7" font-family="JetBrains Mono,monospace" fill="rgba(245,240,232,.4)" text-anchor="middle">'+esc(labels[i]||(i+1))+'</text>';
 }
 return '<svg class="chart-svg" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet"><defs><linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e6a85c"></stop><stop offset="1" stop-color="#d4a574"></stop></linearGradient></defs>'+bars+'</svg>';
}
// ---- grafico de linea SVG inline ----
function svgLine(vals,opts){
 opts=opts||{};
 var W=opts.w||280,H=opts.h||120,pad=opts.pad||18;
 var n=vals.length,max=Math.max.apply(null,vals.concat([1])),min=Math.min.apply(null,vals.concat([0]));
 var innerW=W-pad*2,innerH=H-pad*2,rng=(max-min)||1;
 var labels=opts.labels||[];
 var pts=[];
 for(var i=0;i<n;i++){
  var x=pad+(n>1?i/(n-1):0)*innerW;
  var y=pad+innerH-((vals[i]-min)/rng)*innerH;
  pts.push([x,y]);
 }
 var poly=pts.map(function(p){return p[0].toFixed(1)+','+p[1].toFixed(1)}).join(' ');
 var area='M '+pad+' '+(pad+innerH)+' L '+pts.map(function(p){return p[0].toFixed(1)+' '+p[1].toFixed(1)}).join(' L ')+' L '+(pad+innerW)+' '+(pad+innerH)+' Z';
 var dots='',lbls='';
 for(var j=0;j<n;j++){
  dots+='<circle cx="'+pts[j][0].toFixed(1)+'" cy="'+pts[j][1].toFixed(1)+'" r="2.5" fill="#d4a574"></circle>';
  lbls+='<text x="'+pts[j][0].toFixed(1)+'" y="'+(pad+innerH+11)+'" font-size="7" font-family="JetBrains Mono,monospace" fill="rgba(245,240,232,.4)" text-anchor="middle">'+esc(labels[j]||(j+1))+'</text>';
 }
 return '<svg class="chart-svg" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet"><defs><linearGradient id="lineArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="rgba(212,165,116,.28)"></stop><stop offset="1" stop-color="rgba(212,165,116,0)"></stop></linearGradient></defs><path d="'+area+'" fill="url(#lineArea)"></path><polyline points="'+poly+'" fill="none" stroke="#d4a574" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"></polyline>'+dots+lbls+'</svg>';
}
var WK=['S1','S2','S3','S4','S5','S6'];

function renderProfile(u){
 var panel=document.getElementById('detailPanel');var traits=u.traits||[];
 var byCat={};traits.forEach(t=>{var f=FICHAS[t.trait_id];var cat=(f&&f.category)||'general';(byCat[cat]||=[]).push(t)});
 panel.innerHTML='<div class="users-profile" data-testid="users-profile"><div class="users-kpi-col" data-testid="profile-kpis"><div class="kpi"><div class="kpi-label">Turnos</div><div class="kpi-value">'+(u.total_turns||0)+'</div><div class="kpi-sub">total conversaciones</div></div><div class="kpi"><div class="kpi-label"><span data-tooltip="trait">Rasgos</span></div><div class="kpi-value">'+(traits.length)+'</div><div class="kpi-sub">rasgos aprendidos</div></div><div class="kpi"><div class="kpi-label">Última actividad</div><div class="kpi-value small">'+(u.last_active?u.last_active.slice(0,10):'—')+'</div></div><div class="block"><div class="kpi-label">Actividad semanal</div>'+svgBars(rndSeries(u,11,6,2,12),{labels:WK})+'</div><div class="block"><div class="kpi-label">Mensajes por semana</div>'+svgBars(rndSeries(u,29,6,1,9),{labels:WK})+'</div></div><div class="users-traits-col" data-testid="profile-traits">'+
 (traits.length?traits.map(t=>{var f=FICHAS[t.trait_id];var pct=Math.round((t.confidence||.5)*100);return'<div class="ficha"><div class="ficha-top"><span class="ficha-title">'+esc((f&&f.title)||t.trait_id)+'</span>'+(f&&f.category?'<span class="chip chip-accent chip-square ficha-cat">'+esc(f.category)+'</span>':'')+'</div><div class="ficha-id">'+esc(t.trait_id)+'</div><div class="conf-row"><div class="conf-bar"><div class="conf-fill" style="width:'+pct+'%"></div></div><div class="conf-val">'+(t.confidence||.5).toFixed(2)+'</div></div><div class="ficha-source">origen: '+esc(t.source||'extractor')+'</div>'+(f&&f.description?'<div class="ficha-desc">'+esc(f.description)+'</div>':'')+'</div>'}).join(''):emptyState('🧩','Sin rasgos todavía'))+'</div></div>';}

function renderEvents(u){
 var panel=document.getElementById('detailPanel');
 var adher=rndSeries(u,3,6,40,100);
 var freq=rndSeries(u,17,6,1,10);
 var mood=rndSeries(u,41,6,2,9);
 panel.innerHTML='<div class="users-events" data-testid="users-events"><div class="block"><div class="kpi-label">Adherencia semanal (%)</div>'+svgLine(adher,{labels:WK,w:600,h:150})+'</div><div class="users-chart-grid"><div class="block"><div class="kpi-label">Frecuencia de contacto</div>'+svgBars(freq,{labels:WK})+'</div><div class="block"><div class="kpi-label">Mood estimado</div>'+svgBars(mood,{labels:WK})+'</div></div></div><div class="panel-head users-subhead">Eventos recientes <span>·</span></div>'+
 ((u.conversations||[]).slice(0,5).map(c=>'<div class="conv-item conv-static"><div><div class="conv-date">'+esc(c.created_at||'')+'</div><div class="conv-summary">'+esc(c.summary||'—')+'</div></div><div class="conv-meta">chat</div></div>').join('')||emptyState('📭','Sin eventos todavía'))}

function renderConversations(u){
 var panel=document.getElementById('detailPanel');
 panel.innerHTML='<div data-testid="users-conversations"><div class="panel-head">Conversaciones <span>· '+((u.conversations||[]).length||0)+'</span></div>'+
 ((u.conversations||[]).length?u.conversations.map(c=>{
   var href=c.session_id?('/?session='+encodeURIComponent(c.session_id)):('/?user='+encodeURIComponent(u.external_id||''));
   var metaExtra=c.session_id?'':' · sin sesión';
   return '<a class="conv-item" href="'+href+'" data-testid="conversation-'+esc(c.session_id||c.legacy_group||'')+'"><div><div class="conv-date">'+esc(c.created_at||'')+'</div><div class="conv-summary">'+esc(c.summary||'—')+'</div></div><div class="conv-meta">'+(c.n_turns||0)+' turnos'+esc(metaExtra)+'<br/>'+esc(c.result||'')+'</div></a>'
 }).join(''):emptyState('💬','Sin conversaciones guardadas'))+'</div>'}

document.querySelectorAll('.users-view-selector .tab').forEach(b=>b.addEventListener('click',function(){switchView(this.dataset.view)}));
function esc(s){return String(s||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}

if (window.initGlossaryTooltips) initGlossaryTooltips();
if (window.DemoTour) DemoTour.run();
