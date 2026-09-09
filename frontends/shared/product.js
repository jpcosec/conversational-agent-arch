/* Chat de producto (/chat, frontends/chat/product.html). */
var cfg={},sessionId=localStorage.getItem('pc_session')||null,
    contact={nombre:localStorage.getItem('pc_nombre')||'',phone:localStorage.getItem('pc_phone')||''},
    busy=false;
var esc=function(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')};
var thread=document.getElementById('thread'),scroll=document.getElementById('scroll'),
    input=document.getElementById('input'),send=document.getElementById('send'),gate=document.getElementById('gate');
marked.setOptions({gfm:true,breaks:true});

// Logos de la cabecera: si no cargan se retiran (antes era onerror inline).
// El script corre al final del body, asi que la imagen puede haber fallado
// antes de engancharse el listener: se cubre con complete+naturalWidth.
Array.prototype.forEach.call(document.querySelectorAll('.pc-top img'),function(img){
  img.addEventListener('error',function(){img.remove()});
  if(img.complete&&img.naturalWidth===0)img.remove();
});

function toBottom(){scroll.scrollTop=scroll.scrollHeight}
function bubble(role,text){var d=document.createElement('div');d.className='msg '+(role==='me'?'me':'bot');d.setAttribute('data-testid','pc-msg-'+(role==='me'?'me':'bot'));d.innerHTML=role==='me'?esc(text):marked.parse(text||'');thread.appendChild(d);toBottom();return d}
function typing(on){var t=document.getElementById('typing');if(on){if(t)return;var d=document.createElement('div');d.className='typing';d.id='typing';d.setAttribute('data-testid','pc-typing');d.innerHTML='<i></i><i></i><i></i>';thread.appendChild(d);toBottom()}else if(t)t.remove()}
function greet(){thread.innerHTML='';bubble('bot',cfg.greeting||('Hola, soy el asistente de '+(cfg.name||'la empresa')+'. ¿En qué te ayudo?'))}
async function sendMsg(){
  var m=input.value.trim();if(!m||busy)return;
  busy=true;send.disabled=true;input.value='';input.style.height='auto';
  bubble('me',m);typing(true);
  try{
    var body={message:m,session_id:sessionId};
    if(contact.phone)body.phone=contact.phone;
    if(contact.nombre)body.nombre=contact.nombre;
    var r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    sessionId=d.session_id;localStorage.setItem('pc_session',sessionId);
    typing(false);bubble('bot',(d.turn&&d.turn.assistant_message)||'…');
  }catch(e){typing(false);bubble('bot','No pude responder en este momento. ¿Lo intentamos de nuevo?')}
  finally{busy=false;send.disabled=false;input.focus()}
}
function newConversation(){localStorage.removeItem('pc_session');sessionId=null;greet();input.focus()}
document.getElementById('pcNew').onclick=newConversation;
send.onclick=sendMsg;
input.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMsg()}});
input.addEventListener('input',function(){input.style.height='auto';input.style.height=Math.min(input.scrollHeight,120)+'px'});
function closeGate(save){
  if(save){contact.nombre=document.getElementById('gName').value.trim();contact.phone=document.getElementById('gPhone').value.trim();
    localStorage.setItem('pc_nombre',contact.nombre);localStorage.setItem('pc_phone',contact.phone)}
  localStorage.setItem('pc_gate_done','1');gate.style.display='none';input.focus();
}
document.getElementById('gateGo').onclick=function(){closeGate(true)};
document.getElementById('gateSkip').onclick=function(){closeGate(false)};
(async function(){
  try{cfg=await fetch('/api/config').then(function(r){return r.json()})}catch(e){}
  document.getElementById('bizName').textContent=cfg.name||'Agente';
  document.title=cfg.name||'Chat';
  if(cfg.input_placeholder)input.placeholder=cfg.input_placeholder;
  document.getElementById('gateTitle').textContent='Hola, soy '+(cfg.name||'el asistente');
  greet();
  if(localStorage.getItem('pc_gate_done')){gate.style.display='none'}
  else{document.getElementById('gName').value=contact.nombre;document.getElementById('gPhone').value=contact.phone}
})();
if (window.initGlossaryTooltips) initGlossaryTooltips();
