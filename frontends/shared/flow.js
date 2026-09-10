// Flow (/flow): editor de pasos del flujo conversacional. ES module; los
// imports desnudos resuelven por el <script type="importmap"> del HTML.
import React,{useState,useCallback,useMemo,useRef,useEffect}from'react'
import{createRoot}from'react-dom/client'
import{ReactFlow,ReactFlowProvider,Background,Controls,MiniMap,useNodesState,useEdgesState,addEdge,Handle,Position,MarkerType,useReactFlow,NodeToolbar,NodeResizer,}from'@xyflow/react'
import htm from'htm';const html=htm.bind(React.createElement)
import dagre from'dagre'

const STEP_KINDS={interaccion_simple:{label:'Interacción simple',dot:'#e6a85c',border:'rgba(230,168,92,.5)',bg:'rgba(230,168,92,.07)',icon:'💬'},obtencion_datos:{label:'Obtención de datos',dot:'#c97db9',border:'rgba(201,125,185,.5)',bg:'rgba(201,125,185,.07)',icon:'📝'},handout:{label:'Handout',dot:'#7fb3d5',border:'rgba(127,179,213,.5)',bg:'rgba(127,179,213,.07)',icon:'🤝'},llamado_tool:{label:'Llamado a tool',dot:'#7cba7c',border:'rgba(124,186,124,.5)',bg:'rgba(124,186,124,.07)',icon:'⚙️'}}
const KIND_FIELDS={interaccion_simple:['instructions'],obtencion_datos:['instructions','required_slots'],handout:['instructions','handout_target'],llamado_tool:['instructions','tool_ref','tool_params']}
const PALETTE_ITEMS=Object.entries(STEP_KINDS).map(([k,v])=>({kind:k,label:v.label,color:v.dot,icon:v.icon}))
// Acciones del NodeToolbar; App las cablea en un useEffect (evita re-threadear cada node.data)
const FLOW_ACTIONS={onDelete:null,onRename:null,onChangeKind:null}

function layoutGraph(nodes,edges,rankdir){
 const g=new dagre.graphlib.Graph;g.setDefaultEdgeLabel(()=>({}))
 g.setGraph({rankdir:rankdir||'LR',nodesep:45,ranksep:110,marginx:30,marginy:30})
 const W=200,H=64;nodes.forEach(n=>g.setNode(n.id,{width:W,height:H}))
 edges.forEach(e=>g.setEdge(e.source,e.target));dagre.layout(g)
 return nodes.map(n=>{const p=g.node(n.id);return{...n,position:{x:p.x-W/2,y:p.y-H/2}}})
}

function StepNode({data,selected}){
 const c=STEP_KINDS[data.stepKind]||STEP_KINDS.interaccion_simple
 // Solo los valores que dependen del kind / seleccion van inline; el resto es .flow-node
 return html`<div class="flow-node" style=${{border:`2px solid ${selected?c.border:'rgba(212,165,116,.12)'}`,borderLeft:`4px solid ${c.border}`,background:c.bg,boxShadow:selected?'0 0 20px rgba(212,165,116,.12)':'none'}}>
   <${NodeToolbar} isVisible=${!!selected} position=${Position.Top} className="flow-node-toolbar">
     <div data-testid="flow-node-toolbar" class="rf-node-toolbar">
       <button class="btn btn-sm" data-testid="flow-node-rename" title="Renombrar" onClick=${()=>FLOW_ACTIONS.onRename&&FLOW_ACTIONS.onRename(data.stepId)}>✎ Renombrar</button>
       <button class="btn btn-sm" data-testid="flow-node-kind" title="Cambiar tipo" onClick=${()=>FLOW_ACTIONS.onChangeKind&&FLOW_ACTIONS.onChangeKind(data.stepId)}>⇄ Tipo</button>
       <button class="btn btn-sm btn-danger" data-testid="flow-node-delete" title="Borrar" onClick=${()=>FLOW_ACTIONS.onDelete&&FLOW_ACTIONS.onDelete(data.stepId)}>🗑 Borrar</button>
     </div>
   </${NodeToolbar}>
   <${Handle} type="target" position=${Position.Left} className="flow-handle" style=${{background:c.border}}/>
   <div class="flow-node-head"><span class="flow-node-icon">${c.icon}</span><span class="flow-node-label">${data.label}</span></div>
   <div class="flow-node-kind" style=${{color:c.dot}}>${c.label}</div>
   <div class="rf-drag-handle" data-testid="flow-drag-handle">⠿</div>
   <${Handle} type="source" position=${Position.Right} className="flow-handle" style=${{background:c.border}}/></div>`
}
const nodeTypes={step:StepNode}

function App(){
 const [steps,setSteps]=useState({})
 const [selectedStepId,setSelectedStepId]=useState(null)
 const [nodes,setNodes,onNodesChange]=useNodesState([])
 const [edges,setEdges,onEdgesChange]=useEdgesState([])
 const [rankdir,setRankdir]=useState(localStorage.getItem('flow_rankdir')||'LR')
 const [tools,setTools]=useState([])
 const [subflows,setSubflows]=useState([])
 const [linking,setLinking]=useState(null)
 const {fitView}=useReactFlow()
 const [viewport,setViewport]=useState({x:0,y:0,zoom:1})
 const fitted=useRef(false)

 // Encuadre inicial con viewport CONTROLADO por props: la via imperativa
 // (fitView() del hook) no surte efecto en este montaje --se la puede llamar
 // con los nodos ya medidos en el DOM y el transform se queda en la
 // identidad--, y el grafo aparecia desbordado por la derecha al cargar.
 // onViewportChange conserva pan y zoom.
 const fitGraph=useCallback((nds)=>{
  const wrap=document.querySelector('.flow-canvas')
  if(!wrap||!wrap.clientWidth||!wrap.clientHeight)return
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity
  nds.forEach(n=>{
   const el=document.querySelector('.react-flow__node[data-id="'+n.id+'"]')
   const w=el?el.offsetWidth:190,h=el?el.offsetHeight:55
   minX=Math.min(minX,n.position.x);minY=Math.min(minY,n.position.y)
   maxX=Math.max(maxX,n.position.x+w);maxY=Math.max(maxY,n.position.y+h)
  })
  if(!isFinite(minX))return
  const PAD=1.18
  const zoom=Math.max(0.1,Math.min(wrap.clientWidth/((maxX-minX)*PAD),wrap.clientHeight/((maxY-minY)*PAD),1.3))
  setViewport({x:(wrap.clientWidth-(maxX+minX)*zoom)/2,y:(wrap.clientHeight-(maxY+minY)*zoom)/2,zoom})
 },[])

 useEffect(()=>{fetch('/api/tools').then(r=>r.json()).then(setTools).catch(()=>{})},[])

 // Tooltips del glosario: cada render puede inyectar [data-tooltip] nuevos
 // (initGlossaryTooltips es idempotente).
 useEffect(()=>{if(window.initGlossaryTooltips)window.initGlossaryTooltips()})

 // Cablear acciones del NodeToolbar (borrar / renombrar / cambiar kind)
 useEffect(()=>{
  FLOW_ACTIONS.onDelete=(id)=>{setNodes(nds=>nds.filter(n=>n.id!==id));setEdges(eds=>eds.filter(e=>e.source!==id&&e.target!==id));setSteps(prev=>{const c={...prev};delete c[id];return c});setSelectedStepId(cur=>cur===id?null:cur)}
  FLOW_ACTIONS.onRename=(id)=>{const nn=window.prompt('Nuevo nombre del paso:');if(nn&&nn.trim()){const t=nn.trim();setSteps(prev=>({...prev,[id]:{...prev[id],title:t}}));setNodes(nds=>nds.map(n=>n.id===id?{...n,data:{...n.data,label:t}}:n))}}
  FLOW_ACTIONS.onChangeKind=(id)=>{const keys=Object.keys(STEP_KINDS);setSteps(prev=>{const cur=prev[id];if(!cur)return prev;const nk=keys[(keys.indexOf(cur.kind)+1)%keys.length];return{...prev,[id]:{...cur,kind:nk}}});setNodes(nds=>nds.map(n=>{if(n.id!==id)return n;const nk=keys[(keys.indexOf(n.data.stepKind)+1)%keys.length];return{...n,data:{...n.data,stepKind:nk}}}))}
  return()=>{FLOW_ACTIONS.onDelete=null;FLOW_ACTIONS.onRename=null;FLOW_ACTIONS.onChangeKind=null}
 },[setNodes,setEdges])
 useEffect(()=>{localStorage.setItem('flow_rankdir',rankdir)},[rankdir])

 useEffect(()=>{fetch('/api/flow').then(r=>r.json()).then(flow=>{const m={};flow.nodes.forEach(s=>{m[s.id]=s});setSteps(m);const rn=flow.nodes.map(s=>({id:s.id,type:'step',position:{x:0,y:0},data:{label:(s.title||'').replace(/ —.*$/,'').slice(0,28),stepKind:s.kind||'interaccion_simple',stepId:s.id}}));const re=flow.edges.map((e,i)=>({id:`e-${i}`,source:e.source,target:e.target,animated:true,style:{stroke:'rgba(212,165,116,.3)',strokeWidth:2},markerEnd:{type:MarkerType.ArrowClosed,color:'rgba(212,165,116,.5)'}}));setNodes(layoutGraph(rn,re,rankdir));setEdges(re)}).catch(e=>console.error('flow err',e))},[setNodes,setEdges])

 // nodes.length en las deps: los nodos llegan por fetch, asi que en el primer
 // render el grafo esta vacio y `nodesInitialized` ya es true (cero nodos estan
 useEffect(()=>{if(!nodes.length||fitted.current)return;const t=setTimeout(()=>{fitGraph(nodes);fitted.current=true},400);return()=>clearTimeout(t)},[nodes,fitGraph])

 useEffect(()=>{if(!nodes.length)return;const n=layoutGraph(nodes,edges,rankdir);setNodes(n);requestAnimationFrame(()=>fitGraph(n))},[rankdir])

 const onConnect=useCallback((params)=>{setEdges(eds=>addEdge({...params,animated:true,style:{stroke:'rgba(212,165,116,.3)',strokeWidth:2},markerEnd:{type:MarkerType.ArrowClosed,color:'rgba(212,165,116,.5'}},eds))},[setEdges])
 const onNodeClick=useCallback((_,node)=>{setSelectedStepId(id=>id===node.data.stepId?null:node.data.stepId);if(linking){setEdges(eds=>[...eds,{id:`e-x-${Date.now()}`,source:linking,target:node.id,animated:true,style:{stroke:'#c97db9',strokeWidth:2,strokeDasharray:'5,5'},markerEnd:{type:MarkerType.ArrowClosed,color:'#c97db9'}}]);setLinking(null)}},[linking])
 const onPaneClick=useCallback(()=>{setSelectedStepId(null);setLinking(null)},[])
 const selectedStep=selectedStepId?steps[selectedStepId]:null

 const updateStep=useCallback((patch)=>{if(!selectedStepId)return;setSteps(prev=>({...prev,[selectedStepId]:{...prev[selectedStepId],...patch}}));if('title'in patch||'kind'in patch){setNodes(nds=>nds.map(n=>n.id===selectedStepId?{...n,data:{...n.data,...(patch.title!=null?{label:patch.title}:{}),...(patch.kind!=null?{stepKind:patch.kind}:{})}}:n))}},[selectedStepId])

 const onDragStart=useCallback((e,kind)=>{e.dataTransfer.setData('application/reactflow','step');e.dataTransfer.setData('application/reactflow/kind',kind);e.dataTransfer.effectAllowed='move'},[])
 const onToolDragStart=useCallback((e,tool)=>{e.dataTransfer.setData('application/reactflow','step');e.dataTransfer.setData('application/reactflow/kind','llamado_tool');e.dataTransfer.setData('application/reactflow/tool',JSON.stringify(tool));e.dataTransfer.effectAllowed='move'},[])
 const onDrop=useCallback((event)=>{event.preventDefault();const bounds=event.target.closest('.react-flow').getBoundingClientRect();const type=event.dataTransfer.getData('application/reactflow');const kind=event.dataTransfer.getData('application/reactflow/kind');if(!type)return;const toolData=event.dataTransfer.getData('application/reactflow/tool');const pos={x:event.clientX-bounds.left-100,y:event.clientY-bounds.top-30};const id=`n-${Date.now()}`;const label=`nuevo-paso-${Math.ceil(Math.random()*99)}`;const newStep={id,title:label,kind,instructions:'',required_slots:[],handout_target:'',tool_ref:'',tool_params:[],allowed_transitions:[],grounding_atoms:[],completion_condition:''};if(toolData){try{const t=JSON.parse(toolData);newStep.tool_ref=t.name||t.tool_id||'';newStep.title=label+'-'+newStep.tool_ref.slice(0,12)}catch(e){}}setSteps(prev=>({...prev,[id]:newStep}));setNodes(nds=>[...nds,{id,type:'step',position:pos,data:{label:newStep.title,stepKind:kind,stepId:id}}]);setSelectedStepId(id)},[])
 const onDragOver=useCallback((e)=>{e.preventDefault();e.dataTransfer.dropEffect='move'},[])

 const addSubflow=useCallback(()=>{const id=`sf-${Date.now()}`;setSubflows(s=>[...s,{id,label:'nuevo-subflow',nodes:[],collapsed:false}])},[])
 const toggleSubflow=useCallback((id)=>{setSubflows(s=>s.map(f=>f.id===id?{...f,collapsed:!f.collapsed}:f))},[])

 const selectedStepEl=selectedStep?html`<div>${(()=>{const kf=KIND_FIELDS[selectedStep.kind]||['instructions'];const kc=STEP_KINDS[selectedStep.kind]||STEP_KINDS.interaccion_simple;return html`<div><div class="flow-field"><div class="label label-accent flow-field-label">Nombre</div><input class="input" value=${selectedStep.title}onInput=${e=>updateStep({title:e.target.value})}/></div><div class="flow-field"><div class="label label-accent flow-field-label">Tipo</div><select class="input" title="Tipo de paso del flujo" value=${selectedStep.kind}onChange=${e=>updateStep({kind:e.target.value})}>${Object.entries(STEP_KINDS).map(([k,v])=>html`<option value=${k}>${v.icon} ${v.label}</option>`)}</select></div><div class="flow-field"><div class="label label-accent flow-field-label">Instrucciones</div><textarea class="input" value=${selectedStep.instructions}onInput=${e=>updateStep({instructions:e.target.value})}placeholder="Qué hace el agente aquí..."></textarea></div>${kf.includes('required_slots')?html`<div class="flow-field"><div class="label label-accent flow-field-label"><span data-tooltip="required_slots">Datos requeridos</span></div><div class="flow-field-value chips">${(selectedStep.required_slots||[]).map(s=>html`<span class="chip flow-chip-slot" title="Dato que falta para completar el paso">${s}</span>`)}</div></div>`:''}${kf.includes('handout_target')?html`<div class="flow-field"><div class="label label-accent flow-field-label"><span data-tooltip="handout">A quién deriva</span></div><input class="input" value=${selectedStep.handout_target||''}onInput=${e=>updateStep({handout_target:e.target.value})}placeholder="humano / equipo"/></div>`:''}${kf.includes('tool_ref')?html`<div class="flow-field"><div class="label label-accent flow-field-label"><span data-tooltip="tool">Tool</span></div><input class="input" value=${selectedStep.tool_ref||''}onInput=${e=>updateStep({tool_ref:e.target.value})}placeholder="ID ToolAtom"/></div>`:''}<div class="flow-field"><div class="label label-accent flow-field-label"><span data-tooltip="allowed_transitions">Transiciones</span></div><div class="flow-field-value chips">${(selectedStep.allowed_transitions||[]).map(t=>html`<span class="chip chip-ok flow-chip-transition" title="Siguiente paso permitido">${t}</span>`)}</div></div><div class="flow-field"><div class="label label-accent flow-field-label"><span data-tooltip="grounding_atoms">Fuentes</span></div><div class="flow-field-value chips">${(selectedStep.grounding_atoms||[]).map(a=>html`<span class="chip chip-info flow-chip-atom" title="Documento que da soporte a este paso">${a}</span>`)}</div></div><div class="flow-field"><div class="label label-accent flow-field-label"><span data-tooltip="completion_condition">Condición de cierre</span></div><textarea class="input" value=${selectedStep.completion_condition||''}onInput=${e=>updateStep({completion_condition:e.target.value})}placeholder="Cuándo se completa..."></textarea></div><div class="flow-field"><div class="label label-accent flow-field-label">ID</div><div class="flow-field-value flow-field-id">${selectedStep.id}</div></div></div>`})()}</div>`:html`<div class="empty-state empty-state-inline"><span class="empty-state-icon">👆</span>Selecciona un paso del grafo</div>`

 return html`<div class="app-main"><aside class="sidebar flow-sidebar"><div class="flow-brand"><div class="flow-brand-kicker">Flujo conversacional</div><div class="flow-brand-title"><em>Editor</em> de pasos</div></div>
   <div class="flow-palette" data-testid="flow-palette"><div class="sidebar-label flow-palette-label">Tipos de paso</div>${PALETTE_ITEMS.map(i=>html`<div class="chip flow-palette-item" data-testid="flow-palette-item" draggable title=${i.kind==='interaccion_simple'?'Paso de respuesta normal':i.kind==='obtencion_datos'?'Paso para pedir datos faltantes':i.kind==='handout'?'Paso de cierre o derivación':i.kind==='llamado_tool'?'Paso que dispara una acción del backend':''} onDragStart=${e=>onDragStart(e,i.kind)}><span class="flow-palette-icon">${i.icon}</span><span class="flow-palette-dot" style=${{background:i.color}}></span>${i.label}</div>`)}
   <div class="sidebar-label flow-palette-label flow-palette-label-gap">Subflows</div><button class="btn btn-sm flow-subflow-add" data-testid="flow-add-subflow" onClick=${addSubflow}>+ Añadir subflow</button>
   ${subflows.map(f=>html`<div class="flow-subflow" data-testid="flow-subflow-${f.id}">
     <span class="flow-subflow-name">📁 ${f.label}</span>
     <button class="btn btn-ghost btn-sm ml-auto flow-subflow-toggle" onClick=${()=>toggleSubflow(f.id)}>${f.collapsed?'▶':'▼'}</button></div>`)}
   </div>
   <div class="flow-tools" data-testid="flow-tools-panel"><div class="sidebar-label"><span data-tooltip="tool">Tools (KB)</span></div>${tools.map(t=>html`<div class="flow-tool" data-testid="flow-tool-item" draggable onDragStart=${e=>onToolDragStart(e,t)}><span class="flow-tool-name">${t.name}</span><span class="flow-tool-desc">${(t.description||'').slice(0,50)}</span></div>`)}${!tools.length?html`<div class="empty-state empty-state-inline"><span class="empty-state-icon">🧰</span>Esta KB no tiene tools</div>`:''}</div>
 </aside>
 <div class="rf-canvas flow-canvas" onDrop=${onDrop} onDragOver=${onDragOver}>
   <${ReactFlow} nodes=${nodes} edges=${edges} onNodesChange=${onNodesChange} onEdgesChange=${onEdgesChange} onConnect=${onConnect} onNodeClick=${onNodeClick} onPaneClick=${onPaneClick} nodeTypes=${nodeTypes} viewport=${viewport} onViewportChange=${setViewport} colorMode="dark" defaultEdgeOptions=${{style:{stroke:'rgba(212,165,116,.2)',strokeWidth:2},markerEnd:{type:MarkerType.ArrowClosed,color:'rgba(212,165,116,.4'}}}>
     <${Background} color="rgba(212,165,116,.04)" gap=${24}/>
     <${Controls} showInteractive=${false}/>
     <${MiniMap} nodeColor=${()=>'rgba(212,165,116,.2)'} maskColor="rgba(10,10,15,.7)"/>
   </${ReactFlow}>
   <div class="rf-toolbar">
     <button class="btn" onClick=${()=>{const d=rankdir==='LR'?'TB':'LR';setRankdir(d)}} data-testid="flow-layout-toggle">⟲ ${rankdir==='LR'?'↓ Top-Down':'→ Left-Right'}</button>
     <button class=${'btn'+(linking?' active':'')} onClick=${()=>{setLinking(selectedStepId)}} data-testid="flow-link-horizontal">🔗 Link (L)</button>
     <button class="btn btn-primary">💾 Guardar</button>
   </div>
 </div>
 <aside class="sidebar sidebar-right flow-inspector"><div class="flow-inspector-header" data-testid="flow-inspector">${selectedStep?'Detalle del paso':'Detalle'}</div><div class="flow-inspector-body">${selectedStepEl}</div></aside></div>`
}
createRoot(document.getElementById('root')).render(html`<${ReactFlowProvider}><${App}/></${ReactFlowProvider}>`)

if (window.initGlossaryTooltips) initGlossaryTooltips();
if (window.DemoTour) DemoTour.run();
