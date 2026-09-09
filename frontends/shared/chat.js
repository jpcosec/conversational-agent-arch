/* Chat con inspector (/, frontends/chat/index.html).
 * Logica de la pagina: timeline de turnos, ficha del lead + stepper del flujo,
 * inspector del turno (resumen / contexto / razonamiento) y modal de documento.
 * Estilos en /static/chat.css; tooltips de jerga via glossary.js + tooltip.js.
 */
const messagesEl=document.getElementById('messages'),inputEl=document.getElementById('input'),sendBtn=document.getElementById('send'),inspectorEl=document.getElementById('inspectorBody'),modalBackdrop=document.getElementById('modalBackdrop'),modalTitle=document.getElementById('modalTitle'),modalBody=document.getElementById('modalBody'),modalClose=document.getElementById('modalClose');
let sessionId=localStorage.getItem('kb_chat_session')||null,turns=[],selectedTurnId=null,health={model:'—',status:'unknown'},cfg={};
const atomRegex=/\b(atom-[a-z0-9-]+)\b/g;marked.setOptions({gfm:true,breaks:true});

// Jerga -> negocio SOLO en labels de UI. El valor crudo (nl / tool_call /
// fallback) sigue visible en un .chip mono al lado del label humano; nunca
// se reescribe nada que venga del backend (motivo, family, ids, tools).
const KIND_LABELS={nl:'respuesta libre',tool_call:'ejecutar tool',fallback:'no supe responder'};
const kindLabel=k=>KIND_LABELS[k]||String(k||'—');
const kindHtml=k=>'<span class="chat-kind chat-kind-'+esc(k)+'"><span data-tooltip="kind">'+esc(kindLabel(k))+'</span></span><span class="chip chip-muted">'+esc(k)+'</span>';
const refreshTooltips=()=>{if(window.initGlossaryTooltips)initGlossaryTooltips()};

// Flujo de negocio (stepper) y ficha del lead: /api/lead ordena los steps
// (raiz primero) y trae paso activo, perfil y datos capturados.
let flowSteps=[],leadState=null;
const stepTitle=tag=>{const st=flowSteps.find(x=>x.tag===tag);return st?st.title:(tag||'');};
function renderStepper(activeTag){const el=document.getElementById('flowStepper');if(!el)return;if(!flowSteps.length){el.innerHTML='';el.classList.add('hidden');return}el.classList.remove('hidden');const ai=flowSteps.findIndex(x=>x.tag===activeTag);el.innerHTML=flowSteps.map((st,i)=>{const cls=ai<0?'':i<ai?'done':i===ai?'active':'';return '<div class="chat-step '+cls+'" data-testid="flow-step" data-step-tag="'+esc(st.tag||'')+'" data-state="'+(cls||'pending')+'"><span class="chat-step-n">'+(i+1)+(cls==='active'?' · ahora':cls==='done'?' · listo':'')+'</span><span>'+esc(st.title)+'</span></div>'}).join('')}
function renderLead(lead){const el=document.getElementById('leadCard');if(!el)return;leadState=lead;if(!lead){el.innerHTML='<div class="empty-state empty-state-inline">Sin conversación todavía.</div>';return}const c=lead.collected||{},traits=lead.traits||[];const row=(k,label,v)=>'<div class="lead-row" data-testid="lead-field-'+k+'"><span class="lead-key">'+label+'</span><span class="lead-val'+(v?'':' empty')+'">'+(v?esc(v):'pendiente')+'</span></div>';el.innerHTML=[row('nombre','Nombre',c.nombre||''),row('paso','Paso',lead.step?lead.step.title:''),'<div class="lead-row" data-testid="lead-field-perfil"><span class="lead-key">Perfil</span><span class="lead-val'+(traits.length?'':' empty')+'">'+(traits.length?traits.map(t=>'<span class="lead-chip" title="'+esc(t.trait_id)+'">'+esc(t.title)+'</span>').join(''):'pendiente')+'</span></div>',row('preferencia_visita','Visita',c.preferencia_visita||''),row('modalidad','Modalidad',c.modalidad||''),row('email','Email',c.email||''),row('telefono','Teléfono',c.telefono||'')].join('')}
async function loadFlow(){try{const f=await fetch('/api/flow').then(r=>r.json());const nodes=f.nodes||[],edges=f.edges||[];const byId={};nodes.forEach(n=>byId[n.id]=n);const incoming=new Set(edges.map(e=>e.target)),out={};edges.forEach(e=>{(out[e.source]||=[]).push(e.target)});const order=[],q=nodes.filter(n=>!incoming.has(n.id)).map(n=>n.id);while(q.length){const cur=q.shift();if(order.includes(cur))continue;order.push(cur);(out[cur]||[]).forEach(t=>{if(!order.includes(t))q.push(t)})}nodes.forEach(n=>{if(!order.includes(n.id))order.push(n.id)});flowSteps=order.map(id=>({id:id,tag:byId[id].step_tag,title:byId[id].title||id,kind:byId[id].kind}))}catch(e){flowSteps=[]}}
async function refreshLead(key){if(!key){renderLead(null);return}try{const lead=await fetch('/api/lead?'+key).then(r=>r.json());renderLead(lead);if(lead.step)renderStepper(lead.step.tag)}catch(e){}}
function newSession(){localStorage.removeItem('kb_chat_session');sessionId=null;selectedTurnId=null;turns=turns.filter(t=>t.turn_id==='turn-000');document.getElementById('sessionBadge').textContent='ID: —';document.getElementById('sessionTitle').textContent='Conversación: '+(cfg.name||'Agente');var sc=document.getElementById('sidebarConvState');if(sc)sc.textContent='Esperando mensaje…';renderLead(null);renderStepper(null);renderTurns();renderInspector(null);inputEl.focus()}
const esc=(s='')=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
const enhanceAtoms=(html)=>html.replace(atomRegex,'<a class="atom-link" data-atom="$1">$1</a>');
const atomIds=(ctx)=>(ctx?.atom_ids||[]);
// El modal se abre/cierra toggleando .hidden (theme.css); el backdrop ya es
// display:flex por .chat-modal-backdrop.
function openModal(title,html){modalTitle.textContent=title;modalBody.innerHTML=html;modalBackdrop.classList.remove('hidden')}
function closeModal(){modalBackdrop.classList.add('hidden')}

// domain pasa de #7fb3d5 (celeste) a un neutro calido: es la familia mas
// frecuente (43 de 71 documentos), asi domina sin tirar la paleta al azul
// y las otras familias siguen destacando. Son colores dinamicos por familia,
// se aplican via style desde JS (todo lo estatico va a clases en chat.css).
const FAM_COLORS={self:'#7cba7c',domain:'#c9bda6',conversation:'#e6a85c',user:'#c97db9',gate:'#d46a8c'};
function familiaDe(atom){if(atom.family)return atom.family;const tags=atom.tags||[];for(const f of Object.keys(FAM_COLORS)){if(tags.some(t=>t.startsWith(f+':')))return f}return null}

function renderTurns(){
 messagesEl.innerHTML='';
 turns.forEach(turn=>{const sel=turn.turn_id===selectedTurnId;const wrap=document.createElement('div');wrap.className='chat-turn-wrap';
  if(turn.user_message){wrap.innerHTML+='<div class="chat-msg chat-msg-user"><div class="chat-avatar">👤</div><div class="chat-bubble prose-chat">'+enhanceAtoms(marked.parse(turn.user_message))+'</div></div>'}
  var kind=turn.kind||'nl',na=atomIds(turn.context).length,nt=(turn.context?.include_tags||[]).length;
  var pulse=turn.pending?'<span class="chat-pending"><span class="spinner"></span>Pensando…</span>':'<span class="chat-kind chat-kind-'+esc(kind)+'">⚡ <span data-tooltip="kind">'+esc(kindLabel(kind))+'</span><span class="chip chip-muted">'+esc(kind)+'</span></span>';
  wrap.innerHTML+='<div class="chat-msg chat-msg-bot"><div class="chat-avatar chat-avatar-bot">🤖</div><div class="chat-turn'+(sel?' selected':'')+'" data-turn-id="'+turn.turn_id+'"><div class="prose-chat">'+enhanceAtoms(marked.parse(turn.assistant_message||''))+'</div><div class="chat-turn-meta"><div class="chat-turn-badges"><span class="chip chip-accent">🧠 <span data-tooltip="step">'+esc(turn.flow_node?(stepTitle(turn.flow_node)||turn.flow_node):'contexto')+'</span></span><span class="chip chip-info">📄 <span data-tooltip="atoms">documentos</span>: '+na+'</span><span class="chip chip-muted" title="tags incluidos">🏷 '+nt+'</span></div>'+pulse+'</div></div></div>';messagesEl.appendChild(wrap)});messagesEl.scrollTop=messagesEl.scrollHeight;
 refreshTooltips()}

function contextDiff(turn){const idx=turns.findIndex(t=>t.turn_id===turn.turn_id),prev=idx>0?turns[idx-1]:null;const cur=new Set(atomIds(turn.context)),before=new Set(prev?atomIds(prev.context):[]);const items=turn.context?.items||[];const titleOf=id=>(items.find(i=>i.atom_id===id)?.title)||id;return{retained:[...cur].filter(id=>before.has(id)),added:[...cur].filter(id=>!before.has(id)),removed:[...before].filter(id=>!cur.has(id)),titleOf,prevItems:(prev?.context?.items||[])}}

function renderInspector(turn){
 if(!turn){inspectorEl.innerHTML='<div class="empty-state"><span class="empty-state-icon">🔍</span>Selecciona una respuesta del agente para ver cómo se armó.</div>';return}
 const ctx=turn.context||{},kind=turn.kind||'nl',diff=contextDiff(turn),items=ctx.items||[];
 // agrupar documentos por familia
 const famGroups={};items.forEach(it=>{const f=familiaDe(it)||'domain';(famGroups[f]||=[]).push(it)});
 const famColor=f=>FAM_COLORS[f]||'#c9bda6';
 const motivoLine=it=>{const hasScore=typeof it.score==='number';const scoreTxt=hasScore?' · score '+it.score.toFixed(2):'';return '<div class="ctx-motivo" data-testid="context-motivo-'+esc(it.atom_id)+'">'+esc(it.motivo||'—')+scoreTxt+'</div>'};
 const ctxByFam=Object.keys(famGroups).map(f=>'<div class="family-group"><div class="fg-header" style="color:'+famColor(f)+'">'+f+'</div>'+famGroups[f].map(it=>'<div class="ctx-card" style="background:'+famColor(f)+'14;border-color:'+famColor(f)+'40" data-testid="context-atom-'+esc(it.atom_id)+'" data-atom="'+esc(it.atom_id)+'"><div class="ctx-head"><span class="ctx-title">'+esc(it.title||it.atom_id)+'</span><span class="ctx-fam" style="color:'+famColor(f)+';border-color:'+famColor(f)+'59">'+esc(f)+'</span><span class="ctx-hint">↗</span></div><div class="ctx-id">'+esc(it.atom_id)+' · '+esc(it.role||'-')+(it.grounds_step?' · <span data-tooltip="grounding">fuente del paso</span>':'')+'</div>'+motivoLine(it)+'</div>').join('')+'</div>').join('');

 // Razonamiento: los 4 agentes REALES del pipeline, en orden de ejecución,
 // con datos reales de `turn.decisions` (lo que arma Orchestrator.handle_turn
 // -- ver kb_agent/orchestrator.py). Antes esta lista era hardcodeada con
 // nombres viejos (Ontologizador/Reflector) y descripciones inventadas.
 const dec=turn.decisions||{};
 const rBundle=(dec.ruteador&&dec.ruteador.bundle)||ctx.bundle||[];
 const motivoCounts=bundle=>{const c={piso:0,grounding:0,similitud:0,traits:0};bundle.forEach(b=>{const m=b.motivo||'';if(m.indexOf('piso de seguridad')>-1)c.piso++;if(m.indexOf('grounding')>-1)c.grounding++;if(m.indexOf('similitud')>-1)c.similitud++;if(m.indexOf('trait')>-1)c.traits++});return c};
 const mCounts=motivoCounts(rBundle);
 const ruteadorDesc=rBundle.length+' documentos · <span data-tooltip="piso">base</span> '+mCounts.piso+' · <span data-tooltip="grounding">fuente</span> '+mCounts.grounding+' · <span data-tooltip="score">similitud</span> '+mCounts.similitud+' · <span data-tooltip="trait">perfil</span> '+mCounts.traits;
 const ruteadorDetail=rBundle.length?rBundle.map(b=>{const hasScore=typeof b.score==='number';return '<div class="chat-doc"><span class="chat-doc-id">'+esc(b.doc_id)+'</span> <span style="color:'+famColor(b.family||'domain')+'">· '+esc(b.family||'-')+'</span><div class="chat-doc-motivo">'+esc(b.motivo||'—')+(hasScore?' · score '+b.score.toFixed(2):'')+'</div></div>'}).join(''):'<div class="chat-empty">Sin documentos.</div>';

 const orq=dec.orquestador||{};
 const stepInfo=dec.step||{};
 const orqKind=orq.kind||kind;
 const orqDesc='<span data-tooltip="kind">tipo</span>: '+kindHtml(orqKind)+' · '+(orq.reason?esc(orq.reason):'—');
 const vetoHtml=orq.step_target_vetado?'<div class="chat-veto">El orquestador quiso saltar al paso '+esc(orq.step_target_vetado)+', pero ese paso no está entre las <span data-tooltip="allowed_transitions">transiciones permitidas</span> del paso activo: el salto se bloqueó y la conversación se quedó donde estaba.</div>':'';
 const orqDetail='<div class="chat-detail-line"><span data-tooltip="step">Paso</span>: '+esc(stepInfo.before||'—')+' → '+esc(stepInfo.after||'—')+'</div><div class="chat-detail-line"><span data-tooltip="allowed_transitions">Transiciones permitidas</span>: '+((stepInfo.allowed_transitions||[]).map(esc).join(', ')||'—')+'</div>'+vetoHtml;

 const conv=dec.conversador||{};
 const draftText=conv.draft||'';
 const finalText=turn.assistant_message||'';
 const replaced=!!(draftText&&finalText&&draftText!==finalText);
 const convDesc=replaced?'La <span data-tooltip="gate">validación</span> reemplazó el borrador por el mensaje de derivación':'Redactó: '+esc(kindLabel(orqKind))+' <span class="chip chip-muted">'+esc(orqKind)+'</span>';
 const convDetail='<div class="chat-detail-label">Borrador (antes de validar)</div><div class="chat-detail-text">'+esc(draftText||'—')+'</div>'+(replaced?'<div class="chat-detail-label">Texto final (después de validar)</div><div class="chat-detail-text final">'+esc(finalText)+'</div>':'');

 const gate=dec.gate||{};
 const gateSkipped=Object.prototype.hasOwnProperty.call(gate,'skipped');
 const gateDesc=gateSkipped?'omitido ('+esc(String(gate.skipped))+')':'aprobado: '+(gate.approved===true?'sí':gate.approved===false?'no':'—')+' · acción: '+esc(gate.action||'—');
 const gateReasons=gate.reasons||[];
 const gateCriteria=gate.criterion_ids||[];
 const gateDetail=gateSkipped?'<div class="chat-empty">La validación solo revisa respuestas libres; este turno fue '+esc(kindLabel(String(gate.skipped)))+' <span class="chip chip-muted">'+esc(String(gate.skipped))+'</span>.</div>':('<div class="chat-detail-label">Motivos</div>'+(gateReasons.length?'<ul class="chat-detail-list">'+gateReasons.map(r=>'<li>'+esc(r)+'</li>').join('')+'</ul>':'<div class="chat-empty">—</div>')+'<div class="chat-detail-label">Criterios</div>'+(gateCriteria.length?'<div class="chat-chips">'+gateCriteria.map(c=>'<span class="chip chip-muted chip-square">'+esc(c)+'</span>').join('')+'</div>':'<div class="chat-empty">—</div>'));

 const traitsAfter=turn.traits_after||[];
 const profDesc=traitsAfter.length+' <span data-tooltip="trait">rasgos</span> · corre después de responder, no bloquea la respuesta';
 const profDetail=traitsAfter.length?'<div class="chat-chips">'+traitsAfter.map(t=>'<span class="chip chip-ok">'+esc(t)+'</span>').join('')+'</div>':'<div class="chat-empty">Sin rasgos nuevos en este turno.</div>';

 const agents=[
  {name:'Ruteador de contexto',key:'ruteador',icon:'🧭',desc:ruteadorDesc,detail:ruteadorDetail},
  {name:'Orquestador',key:'orquestador',icon:'🧠',desc:orqDesc,detail:orqDetail},
  {name:'Conversador',key:'conversador',icon:'💬',desc:convDesc,detail:convDetail},
  {name:'Validación',key:'gate',icon:'🛡️',desc:gateDesc,detail:gateDetail},
  {name:'Perfilador · después de responder',key:'perfilador',icon:'👤',desc:profDesc,detail:profDetail}
 ];
 // El click en la fila se delega desde el listener global (sin onclick inline).
 const agentHtml=agents.map(a=>'<div class="agent-row" data-testid="agent-row"><div class="agent-head"><span>'+a.icon+'</span><span class="agent-name"><span data-tooltip="'+a.key+'">'+esc(a.name)+'</span></span><span class="expand-icon">›</span></div><div class="agent-desc">'+a.desc+'</div><div class="agent-detail hidden">'+a.detail+'</div></div>');

 inspectorEl.innerHTML = [
  '<div class="chat-section" data-testid="inspector-summary">',
  '  <h4 class="section-title">🧾 Resumen</h4>',
  '  <div class="chat-summary">',
  '    <div class="chat-summary-item"><span class="label">Persona</span><span class="chat-summary-val">'+(turn.user_message?'Atendido':'—')+'</span></div>',
  '    <div class="chat-summary-item"><span class="label">Intención</span><span class="chat-summary-val">'+kindHtml(kind)+'</span></div>',
  '    <div class="chat-summary-item"><span class="label"><span data-tooltip="tool">Tool ejecutada</span></span><span class="chat-summary-val">'+(turn.system_turn?esc(turn.system_turn.tool):'—')+'</span></div>',
  '    <div class="chat-summary-item"><span class="label"><span data-tooltip="step">Paso</span></span><span class="chat-summary-val">'+esc(turn.flow_node||'—')+'</span></div>',
  '  </div>',
  '</div>',
  '<div class="chat-section" data-testid="inspector-context">',
  '  <h4 class="section-title">🗂 <span data-tooltip="ctx">Contexto</span> ('+esc(ctx.scenario||'—')+')</h4>',
  '  <div class="chat-section-sub">'+items.length+' <span data-tooltip="atoms">documentos en contexto</span>'+(ctx.is_empty?' · <span class="chat-bad">vacío</span>':'')+'. Retenidos: '+diff.retained.length+' · Nuevos: '+diff.added.length+' · Desertados: '+diff.removed.length+'.</div>',
  '  '+(ctxByFam||'<div class="empty-state empty-state-inline">Sin documentos.</div>'),
  '</div>',
  '<div class="chat-section" data-testid="inspector-reasoning">',
  '  <h4 class="section-title">🧠 Razonamiento</h4>',
  '  <div class="chat-agents">'+agentHtml.join('')+'</div>',
  '</div>'
].join('\n');
 refreshTooltips();
}

function selectTurn(turnId){selectedTurnId=turnId;renderTurns();renderInspector(turns.find(t=>t.turn_id===turnId))}
async function openAtomModal(atomId){try{var r=await fetch('/api/atom/'+atomId);if(!r.ok){openModal('Documento','<div class="chat-empty">No se pudo cargar el documento.</div>');return}var a=await r.json();openModal(a.atom_id,'<div class="chat-modal-meta"><div><span class="muted">Título:</span> '+esc(a.title||'')+'</div><div><span class="muted">Familia:</span> <code>'+(a.tags?Object.keys(FAM_COLORS).find(k=>a.tags.some(t=>t.startsWith(k+':')))||'—':'—')+'</code></div><div><span class="muted">Path:</span> <code>'+esc(a.path||'')+'</code></div><div><span class="muted">Tags:</span><div class="chips">'+((a.tags||[]).map(t=>'<span class="chip chip-muted chip-square">'+esc(t)+'</span>').join(''))+'</div></div><div class="chat-modal-content">'+marked.parse(a.body||'_Sin contenido_')+'</div></div>')}catch(e){openModal('Documento','<div class="error-state">'+esc(e.message||e)+'</div>')}}

async function sendMessage(){var m=inputEl.value.trim();if(!m)return;inputEl.value='';sendBtn.disabled=true;var ghostId='ghost-'+Date.now();turns.push({turn_id:ghostId,user_message:m,assistant_message:'_Compilando contexto…_',context:{atom_ids:[],include_tags:[],items:[]},pending:true});selectedTurnId=ghostId;renderTurns();var t0=performance.now();try{var r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m,session_id:sessionId})});var d=await r.json();sessionId=d.session_id;localStorage.setItem('kb_chat_session',sessionId);document.getElementById('sessionBadge').textContent='ID: '+sessionId;d.turn.latency_ms=Math.round(performance.now()-t0);turns=turns.filter(t=>t.turn_id!==ghostId);turns.push(d.turn);selectTurn(d.turn.turn_id);updateSidebarConversation(d.turn);renderStepper(d.turn.flow_node);refreshLead('session_id='+encodeURIComponent(sessionId))}catch(e){turns=turns.filter(t=>t.turn_id!==ghostId);turns.push({turn_id:'err-'+Date.now(),user_message:m,assistant_message:'**Error:** '+(e.message||e),kind:'fallback',context:{atom_ids:[],include_tags:[],items:[]}});renderTurns()}finally{sendBtn.disabled=false;inputEl.focus()}}

function updateSidebarConversation(turn){var sc=document.getElementById('sidebarConvState');if(sc)sc.textContent='Último: '+(turn.flow_node?(stepTitle(turn.flow_node)||turn.flow_node):kindLabel('nl'))+' · '+kindLabel(turn.kind||'—')+((turn.traits_after||[]).length?' · +rasgos':'');var su=document.getElementById('sidebarUserId');if(su)su.textContent=turn.external_id||health.model||'—';var st=document.getElementById('sidebarTraits');if(st&&turn.traits_after?.length)st.innerHTML=turn.traits_after.map(t=>'<span class="chip chip-ok">'+esc(t)+'</span>').join('');var se=document.getElementById('sidebarEvents');if(se)se.textContent=(turn.traits_after||[]).length+' rasgos · 1 turno'}

sendBtn.addEventListener('click',sendMessage);inputEl.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage()}});
modalClose.addEventListener('click',closeModal);modalBackdrop.addEventListener('click',e=>{if(e.target===modalBackdrop)closeModal()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!modalBackdrop.classList.contains('hidden'))closeModal()});
document.getElementById('newSession').addEventListener('click',newSession);
document.getElementById('inspectorClear').addEventListener('click',()=>{selectedTurnId=null;renderTurns();renderInspector(null)});
document.addEventListener('click',e=>{
 var card=e.target.closest('[data-turn-id]');if(card&&card.getAttribute('data-turn-id')){selectTurn(card.getAttribute('data-turn-id'));return}
 var row=e.target.closest('.agent-row');if(row){row.classList.toggle('open');var det=row.querySelector('.agent-detail');if(det)det.classList.toggle('hidden');return}
 var atom=e.target.closest('[data-open-atom]');if(atom){openAtomModal(atom.getAttribute('data-open-atom'));return}
 var ref=e.target.closest('[data-atom]');if(ref){openAtomModal(ref.getAttribute('data-atom'));return}});

(async function(){try{cfg=await fetch('/api/config').then(r=>r.json())}catch(e){}try{health=await fetch('/api/health').then(r=>r.json())}catch(e){}
 var bizName=cfg.name||'Agente';document.getElementById('sessionTitle').textContent='Conversación: '+bizName;if(sessionId)document.getElementById('sessionBadge').textContent='ID: '+sessionId;
 // Sidebar de configuracion y estado del servicio: antes vivia en el IIFE de
 // la topbar, que ahora es /static/nav.js (comun a todas las vistas). Aca ya
 // estan cfg y health.
 (function(){var sm=document.getElementById('sidebarModel'),sk=document.getElementById('sidebarKB'),sb=document.getElementById('sidebarBusiness'),sp=document.getElementById('sidebarPulse');
  if(sm)sm.textContent='Modelo: '+(cfg.model||'—');
  if(sk)sk.textContent='KB: '+(cfg.kb_label||'—');
  if(sb)sb.textContent='Negocio: '+(cfg.name||'—');
  if(sp&&health.status){var ok=health.status==='ok';sp.innerHTML='<span class="chat-pulse-dot'+(ok?' on':'')+'"></span><span class="chat-pulse-text'+(ok?' on':'')+'">'+esc(ok?'En línea':health.status)+'</span>'}
 })();
 await loadFlow();renderStepper(null);
 turns.push({turn_id:'turn-000',user_message:'',assistant_message:cfg.greeting||'Hola. Soy el asistente de **'+bizName+'**. ¿En qué te puedo ayudar?',kind:'nl',context:{atom_ids:[],include_tags:[],items:[],tools:[],grounding_atoms:[]}});
 var qs=new URLSearchParams(location.search),loadSession=qs.get('session'),loadUser=qs.get('user');
 if(loadSession||loadUser){try{
  var histUrl=loadSession?('/api/history?session_id='+encodeURIComponent(loadSession)):('/api/history?external_id='+encodeURIComponent(loadUser));
  var hist=await fetch(histUrl).then(r=>r.json());
  var msgs=hist.messages||[],turnRows=hist.turns||[];
  // Empareja mensajes user/assistant en turnos y, si hay rastro real en
  // `turns` (siempre que la conversacion se cargue por ?session=), le pega
  // el rastro (bundle/decision/gate/draft) al turno correspondiente por
  // orden cronologico -- ambas listas vienen ordenadas asc por created_at,
  // y cada turno real persiste exactamente 1 fila user + 1 fila assistant.
  var pairedTurns=[],pending=null;
  msgs.forEach(function(m,i){
   if(m.role==='user'){pending={turn_id:'h'+i,user_message:m.content,assistant_message:'',kind:'nl',context:{atom_ids:[],include_tags:[],items:[],tools:[],grounding_atoms:[]},decisions:{}};pairedTurns.push(pending)}
   else if(m.role==='assistant'){if(pending&&!pending.assistant_message){pending.assistant_message=m.content}else{pending={turn_id:'h'+i,user_message:'',assistant_message:m.content,kind:'nl',context:{atom_ids:[],include_tags:[],items:[],tools:[],grounding_atoms:[]},decisions:{}};pairedTurns.push(pending)}}
   else{pending=null}
  });
  pairedTurns.forEach(function(t,idx){
   var row=turnRows[idx];if(!row)return;
   var bundle=row.bundle||[];
   var items=bundle.map(function(b){return {atom_id:b.doc_id,title:b.doc_id,role:b.family,family:b.family,score:b.score,motivo:b.motivo,tags:[],grounds_step:(b.motivo||'').indexOf('grounding')>-1}});
   t.context={atom_ids:bundle.map(function(b){return b.doc_id}),include_tags:[],items:items,tools:[],grounding_atoms:[],bundle:bundle,is_empty:bundle.length===0};
   t.kind=(row.decision&&row.decision.kind)||'nl';
   t.flow_node=row.step_after;
   t.decisions={
    step:{before:row.step_before,after:row.step_after,target:row.decision&&row.decision.step_target,allowed_transitions:[],missing_slots:[]},
    ruteador:{bundle:bundle,atoms:bundle.length,grounding_atoms:[],user_traits:[],is_empty:bundle.length===0},
    orquestador:{kind:t.kind,decision:row.decision,state_trace:[],reason:row.decision&&row.decision.reason,step_target_vetado:row.decision&&row.decision.step_target_vetado},
    conversador:{draft:row.draft},
    gate:row.gate||{approved:null,skipped:t.kind},
    tool:row.tool||{called:false}
   }
  });
  turns=turns.concat(pairedTurns);
  var titleSuffix=loadSession?('sesión '+loadSession):loadUser;
  document.getElementById('sessionTitle').textContent='Conversación: '+bizName+' · '+titleSuffix;
  if(loadSession){sessionId=null;document.getElementById('sessionBadge').textContent='ID: (histórico) '+loadSession}
 }catch(e){}}
 renderTurns();
 var leadKey=loadSession?('session_id='+encodeURIComponent(loadSession)):loadUser?('external_id='+encodeURIComponent(loadUser)):sessionId?('session_id='+encodeURIComponent(sessionId)):null;
 refreshLead(leadKey);
 var lastTurn=turns.filter(t=>t.flow_node).slice(-1)[0];if(lastTurn)renderStepper(lastTurn.flow_node)})();

if (window.initGlossaryTooltips) initGlossaryTooltips();
if (window.DemoTour) DemoTour.run();
