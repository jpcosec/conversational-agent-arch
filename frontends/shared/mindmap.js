// Mindmap (/mindmap): la KB como arbol por familias (vista read-only). ES
// module; los imports desnudos resuelven por el <script type="importmap">.
import React,{useState,useCallback,useEffect,useRef,useMemo}from'react'
import{createRoot}from'react-dom/client'
import{ReactFlow,ReactFlowProvider,Background,Controls,MiniMap,Handle,Position,useNodesState,useEdgesState,useReactFlow,useNodesInitialized,NodeToolbar}from'@xyflow/react'
import htm from'htm';const html=htm.bind(React.createElement)
import dagre from'dagre'

const FAM={self:{color:'#7cba7c',icon:'🧬',label:'self'},domain:{color:'#7fb3d5',icon:'📖',label:'domain'},conversation:{color:'#e6a85c',icon:'💬',label:'conversation'},user:{color:'#c97db9',icon:'👤',label:'user'},gate:{color:'#d46a8c',icon:'🚦',label:'gate'}}
// Eje de agente (independiente de la familia): qué agente "toca" cada atom_type.
// Mapeo verificado contra docs/AGENT-CONTRACTS.md §2.0 y §5 de docs/KNOWLEDGE-MODEL.md
// (tabla "Documentos ↔ agentes"; F=carga base y D=selección dinámica cuentan igual acá,
// porque lo que importa para el filtro es si el agente lo ve, no cuándo).
// El perfilador es post-turno (no participa del camino de respuesta) — marcado aparte.
const AGENTS={
 conversador:{color:'#4fc3d9',icon:'🗣️',label:'Conversador'},
 ruteador:{color:'#e0c341',icon:'🧭',label:'Ruteador'},
 orquestador:{color:'#9b7fd4',icon:'🎚️',label:'Orquestador'},
 gate:{color:'#ff6b6b',icon:'🛂',label:'Gate'},
 perfilador:{color:'#8a94a6',icon:'🪞',label:'Perfilador',postTurn:true},
}
const AGENT_OF={
 self:['conversador'],style:['conversador'],boundary:['conversador'],strategy:['conversador'],
 fallback:['conversador','orquestador'],
 domain:['conversador','ruteador'],
 rule:['conversador','ruteador','orquestador'],
 step:['conversador','ruteador','orquestador'],
 tool:['orquestador'],
 gate:['gate'],
 trait:['conversador','ruteador','perfilador'],
}
const FIVEWH={what:'❓',when:'📅',where:'📍',who:'👤',how:'🔧',why:'🤔'}
let NID=0
// Puente de acciones del NodeToolbar -> estado de App (poblado en App via useEffect)
const MM_ACTIONS={del(){},child(){},sibling(){},link(){},comment(){},goto(){}}

function MindNode({id,data,selected}){
 const fam=FAM[data.family]||FAM.domain;const isRoot=data.kind==='root';const isAtom=data.kind==='atom'
 const bg=isRoot?fam.color:isAtom?'rgba(18,18,26,.95)':`${fam.color}18`
 const border=selected?'#d4a574':isRoot?fam.color:`${fam.color}66`
 // Solo los colores (familia / seleccion) van inline; la geometria es .mm-node*
 return html`<div class=${'mm-node'+(isRoot?' mm-node-root':'')} data-kind=${data.kind} data-atom-type=${isAtom?data.atom_type:undefined} style=${{border:`2px solid ${border}`,borderLeft:isAtom?`4px solid ${fam.color}`:`2px solid ${border}`,background:bg,boxShadow:selected?'0 0 18px rgba(212,165,116,.25)':'none'}}>
   <${NodeToolbar} isVisible=${!!selected} position=${Position.Top}>
     <!-- UI read-only (decision del owner): el mindmap VISUALIZA la KB, no la
          edita. Las mutaciones locales (borrar / +hijo / +hermano / link) se
          removieron porque prometian una persistencia que no existe: la KB se
          edita via comandos SLDB sobre el store, no desde aca. Ver
          frontends/UI-GUIDE.md. El editor persistido queda como task diferida
          (task-modo-editor-de-atoms-en-la-ui). Solo queda navegar al documento. -->
     <div data-testid="mindmap-node-toolbar" class="rf-node-toolbar">
       <button class="btn btn-sm" title="Ir al documento" onClick=${()=>MM_ACTIONS.goto(id)}>↗doc</button>
     </div>
   </${NodeToolbar}>
   <${Handle} type="target" position=${Position.Left} className="mm-handle" style=${{background:fam.color,opacity:isRoot?0:1}}/>
   ${isRoot&&html`<span class="mm-node-icon-root">${fam.icon}</span>`}
   ${isAtom&&html`<span class="mm-node-icon">${FIVEWH[data.five_wh]||'📄'}</span>`}
   <div class="mm-node-body"><div class=${'mm-node-title'+(isRoot?' mm-node-title-root':'')}>${data.label}</div>
     ${isAtom&&html`<div class="mm-node-type" style=${{color:fam.color}}>${data.atom_type}</div>`}</div>
   <div class="rf-drag-handle" data-testid="mindmap-drag-handle">⠿</div>
   <${Handle} type="source" position=${Position.Right} className="mm-handle" style=${{background:fam.color}}/>
 </div>`}
const nodeTypes={mind:MindNode}

function buildGraph(tax){const nodes=[],edges=[];Object.keys(tax).forEach(fam=>{
 const rootId=`root-${fam}`;nodes.push({id:rootId,type:'mind',position:{x:0,y:0},data:{label:fam,family:fam,kind:'root'}})
 const pushAtom=(a,parentId)=>{const aid=`a-${NID++}`;nodes.push({id:aid,type:'mind',position:{x:0,y:0},data:{label:a.title,family:fam,kind:'atom',atom_id:a.id,atom_type:a.atom_type,five_wh:a.five_wh_one_plus,summary:a.summary,tags:a.tags}});edges.push({id:`e-${parentId}-${aid}`,source:parentId,target:aid,type:'bezier',style:{stroke:`${FAM[fam].color}55`,strokeWidth:1.8}})};
 const mkEdge=(s,t)=>({id:`e-${s}-${t}`,source:s,target:t,type:'bezier',style:{stroke:`${FAM[fam].color}55`,strokeWidth:1.8}})
 function walk(children,parentId){children.forEach(node=>{const bid=`b-${NID++}`;nodes.push({id:bid,type:'mind',position:{x:0,y:0},data:{label:node.name,family:fam,kind:'branch',path:node.path}});edges.push(mkEdge(parentId,bid));node.atoms.forEach(a=>pushAtom(a,bid));if(node.children?.length)walk(node.children,bid)})}
 walk(tax[fam].children,rootId);(tax[fam].orphans||[]).forEach(a=>pushAtom(a,rootId))
});return{nodes,edges}}

function layoutTree(nodes,edges,rankdir){
 const byFam={};nodes.forEach(n=>{(byFam[n.data.family]||=[]).push(n)})
 const order=['self','domain','conversation','user','gate'];let yOffset=0;const pos={}
 order.forEach(fam=>{const fn=byFam[fam]||[];if(!fn.length)return
  const ids=new Set(fn.map(n=>n.id));const fe=edges.filter(e=>ids.has(e.source)&&ids.has(e.target))
  const g=new dagre.graphlib.Graph;g.setDefaultEdgeLabel(()=>({}))
  g.setGraph({rankdir:rankdir||'LR',nodesep:22,ranksep:90,marginx:20,marginy:20})
  const W=n=>n.data.kind==='root'?150:n.data.kind==='atom'?200:110
  fn.forEach(n=>g.setNode(n.id,{width:W(n),height:40}));fe.forEach(e=>g.setEdge(e.source,e.target));dagre.layout(g)
  let maxY=0;fn.forEach(n=>{maxY=Math.max(maxY,g.node(n.id).y)})
  fn.forEach(n=>{const p=g.node(n.id);pos[n.id]={x:p.x-W(n)/2,y:p.y-20+yOffset}})
  yOffset+=maxY+120
 });return nodes.map(n=>({...n,position:pos[n.id]||{x:0,y:0}}))
}

function Tooltip({atom,pos}){if(!atom)return null;const tags=(atom.tags||[]).filter(t=>t.includes(':'))
 return html`<div class="mm-tooltip" style=${{left:pos.x,top:pos.y}}>
   <div class="mm-tooltip-id">${atom.atom_id}</div>
   <div class="mm-tooltip-title">${atom.label}</div>
   <div class="mm-tooltip-meta">Esto es un <b>${atom.atom_type||atom.kind||'nodo'}</b> de la familia <b>${atom.family}</b>.</div>
   ${atom.five_wh&&html`<span class="mm-tooltip-wh">${FIVEWH[atom.five_wh]||''} ${atom.five_wh}</span>`}
   ${atom.summary&&html`<div class="mm-tooltip-summary">${atom.summary}</div>`}
   ${tags.length>0&&html`<div class="mm-tooltip-tags">${tags.map(t=>html`<span key=${t} class="mm-tooltip-tag">${t}</span>`)}</div>`}</div>`}

function App(){
 const [nodes,setNodes,onNodesChange]=useNodesState([]);const[edges,setEdges,onEdgesChange]=useEdgesState([])
 const [hover,setHover]=useState(null)
 const [layoutMode,setLayoutMode]=useState('tree');const [xfamily,setXfamily]=useState(false);const [searchText,setSearchText]=useState('')
 const [filterRama,setFilterRama]=useState(null);const [collapsed,setCollapsed]=useState(new Set())
 const [filterAgents,setFilterAgents]=useState(new Set())
 const toggleAgent=useCallback(id=>setFilterAgents(prev=>{const n=new Set(prev);n.has(id)?n.delete(id):n.add(id);return n}),[])
 const [selectedNode,setSelectedNode]=useState(null);const [linking,setLinking]=useState(false);const [taxData,setTaxData]=useState(null)
 const {fitView}=useReactFlow()
 const [viewport,setViewport]=useState({x:0,y:0,zoom:1})
 const fitted=useRef(false)

 useEffect(()=>{fetch('/api/taxonomy').then(r=>r.json()).then(tax=>{setTaxData(tax);NID=0;const{nodes:rn,edges:re}=buildGraph(tax);setNodes(layoutTree(rn,re,'LR'));setEdges(re)}).catch(e=>console.error('tax err',e))},[setNodes,setEdges])

 // Tooltips del glosario: cada render puede inyectar [data-tooltip] nuevos
 // (initGlossaryTooltips es idempotente).
 useEffect(()=>{if(window.initGlossaryTooltips)window.initGlossaryTooltips()})

 // Encuadre inicial con viewport CONTROLADO por props.
 // La via imperativa (fitView() del hook, y tambien setViewport()) no surte
 // efecto en este montaje: se la puede llamar con los 76 nodos ya medidos en
 // el DOM y el transform del viewport se queda en la identidad, dejando el
 // arbol (~2800px de alto) desbordando la pantalla. Controlando el viewport
 // por prop no dependemos de esa API; onViewportChange conserva pan y zoom.
 useEffect(()=>{
  if(!nodes.length||fitted.current)return
  const t=setTimeout(()=>{
   const wrap=document.querySelector('.mm-canvas')
   if(!wrap||!wrap.clientWidth||!wrap.clientHeight)return
   let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity
   nodes.forEach(n=>{
    const el=document.querySelector('.react-flow__node[data-id="'+n.id+'"]')
    const w=el?el.offsetWidth:160,h=el?el.offsetHeight:34
    minX=Math.min(minX,n.position.x);minY=Math.min(minY,n.position.y)
    maxX=Math.max(maxX,n.position.x+w);maxY=Math.max(maxY,n.position.y+h)
   })
   if(!isFinite(minX))return
   const PAD=1.12
   const zoom=Math.max(0.1,Math.min(wrap.clientWidth/((maxX-minX)*PAD),wrap.clientHeight/((maxY-minY)*PAD),1.2))
   setViewport({x:(wrap.clientWidth-(maxX+minX)*zoom)/2,y:(wrap.clientHeight-(maxY+minY)*zoom)/2,zoom})
   fitted.current=true
  },400)
  return()=>clearTimeout(t)
 },[nodes])

 const applyLayout=useCallback((lay)=>{setLayoutMode(lay);if(!nodes.length||!taxData)return;if(lay==='embeddings'){fetch('/api/viz/graph').then(r=>r.json()).then(g=>{if(!g.nodes)return;const em=nodes.map(n=>{const e=g.nodes.find(gn=>gn.id===n.data.atom_id||gn.id===n.data.label);return e?{...n,position:{x:e.position?.x||0,y:e.position?.y||0}}:n});setNodes(em);setEdges(prev=>prev)}).catch(()=>{});return}
  const n=layoutTree(nodes,edges,lay==='topdown'?'TB':'LR');setNodes(n);fitView({padding:0.1,duration:400})},[nodes,edges,taxData])

 // UI read-only (decision del owner): las hotkeys de MUTACION (Delete/Tab/
 // Enter/L) se neutralizan -- borrar/agregar/linkear no persisten en la KB.
 // Solo quedan las de NAVEGACION/VISTA: buscar, collapse, centrar, layout.
 useEffect(()=>{if(typeof initHotkeys==='function'){initHotkeys({element:document.querySelector('.react-flow'),onSearch:()=>document.querySelector('[data-testid="mindmap-search"]')?.focus(),onDelete:()=>{},onAddChild:()=>{},onAddSibling:()=>{},onLinkHorizontal:()=>{},onCollapse:()=>{if(selectedNode){setCollapsed(c=>{const n=new Set(c);if(n.has(selectedNode))n.delete(selectedNode);else n.add(selectedNode);return n})}},onFocus:()=>{if(selectedNode){const n=document.querySelector(`[data-id="${selectedNode}"]`);if(n)n.scrollIntoView({behavior:'smooth',block:'center'})}},onLayout:l=>applyLayout(['tree','topdown','embeddings'][l-1]),onHelp:()=>alert('Ctrl+F Buscar · Space Collapse · 1/2/3 Layout · F Centrar · ? Ayuda · (vista read-only: la KB se edita por SLDB)'),onCancel:()=>setLinking(false)})}})

 // Puente NodeToolbar -> acciones sobre estado de App. UI read-only: solo
 // navegar al documento. Las mutaciones (del/child/sibling/link) quedan como
 // no-op -- se removieron del toolbar y de las hotkeys (ver UI-GUIDE.md).
 useEffect(()=>{
  MM_ACTIONS.del=()=>{}
  MM_ACTIONS.child=()=>{}
  MM_ACTIONS.sibling=()=>{}
  MM_ACTIONS.link=()=>{}
  MM_ACTIONS.goto=(nid)=>{const n=nodes.find(x=>x.id===nid);if(n&&n.data.atom_id)window.open('/api/atom/'+encodeURIComponent(n.data.atom_id),'_blank')}
 })

 const onNodeMouseEnter=useCallback((e,node)=>{if(node.data.kind!=='atom')return;setHover({atom:node.data,pos:{x:e.clientX+16,y:e.clientY+8}})},[])
 const onNodeMouseLeave=useCallback(()=>setHover(null),[])
 // UI read-only: seleccionar resalta el nodo; ya no se crean edges por click.
 const onNodeClick=useCallback((e,node)=>{setSelectedNode(node.id);if(node.data.kind==='atom')setHover(null)},[])
 const onPaneClick=useCallback(()=>{setHover(null);setSelectedNode(null);setLinking(false)},[])

 const ramas=useMemo(()=>{if(!taxData)return[];const r=[];Object.keys(taxData).forEach(fam=>{r.push({id:fam,label:fam,children:[]})});return r},[taxData])

 const filtered=useMemo(()=>{
  let out=nodes
  if(filterRama&&taxData){const fam=filterRama;out=out.filter(n=>n.data.family===fam||n.data.label===fam)}
  if(filterAgents.size){
   // El eje de agente solo aplica a hojas (atoms): raíz y ramas quedan
   // visibles como esqueleto del árbol aunque ninguno de sus atoms matchee.
   out=out.filter(n=>{if(n.data.kind!=='atom')return true;const ag=AGENT_OF[n.data.atom_type]||[];return ag.some(a=>filterAgents.has(a))})
  }
  return out
 },[nodes,filterRama,taxData,filterAgents])
 const searched=useMemo(()=>{if(!searchText)return filtered;const t=searchText.toLowerCase();return filtered.filter(n=>(n.data.label||'').toLowerCase().includes(t)||(n.data.atom_id||'').toLowerCase().includes(t))},[filtered,searchText])

 return html`<div class="app-main">
   <aside class="sidebar mm-sidebar" data-testid="mindmap-sidebar"><div class="sidebar-label">Filtrar rama</div>
    <input class="input mm-filter" placeholder="buscar rama…" onInput=${e=>setFilterRama(e.target.value||null)}/>
    ${ramas.map(r=>html`<div class="mm-rama ${filterRama===r.id?'active':''}" data-testid="mindmap-rama-${r.id}" onClick=${()=>setFilterRama(r.id===filterRama?null:r.id)}>${FAM[r.id]?.icon||''} ${r.label}</div>`)}
    <div class="sidebar-label mm-sidebar-label-gap" data-testid="mindmap-agent-filter">Filtrar agente</div>
    ${Object.entries(AGENTS).map(([id,a])=>{const active=filterAgents.has(id);return html`<div class="mm-rama ${active?'active':''}" data-testid="mindmap-agent-${id}" style=${{borderLeft:`3px solid ${active?a.color:'transparent'}`,color:active?a.color:'rgba(245,240,232,.6)'}} onClick=${()=>toggleAgent(id)}><span class="mm-agent-dot" style=${{background:a.color}}></span>${a.icon} <span data-tooltip=${id}>${a.label}</span>${a.postTurn?' · post-turno':''}</div>`})}
    <div class="mm-layout-block">
     <div class="sidebar-label">Layout</div>
     ${[{id:'tree',label:'Árbol LR'},{id:'topdown',label:'Top-Down'},{id:'embeddings',label:'Embeddings'}].map(l=>html`<div class="mm-rama ${layoutMode===l.id?'active':''}" data-testid="mindmap-layout-${l.id}" onClick=${()=>applyLayout(l.id)}>${l.id==='embeddings'?html`<span data-tooltip="embeddings">${l.label}</span>`:l.label}</div>`)}
     <label class="mm-check">
      <input type="checkbox" checked=${xfamily} onChange=${()=>setXfamily(!xfamily)} data-testid="mindmap-xfamily-toggle"/>
      <span>Links horizontales</span></label>
    </div>
   </aside>
   <div class="rf-canvas mm-canvas">
    <div class="mm-topbar">
     <input class="input mm-search" data-testid="mindmap-search" placeholder="Buscar nodo (Ctrl+F)…" value=${searchText} onInput=${e=>setSearchText(e.target.value)}/>
     <span class="mm-topbar-hint">sólo lectura · hover muestra el detalle</span>
    </div>
    <${ReactFlow} nodes=${searched} edges=${edges} onNodesChange=${onNodesChange} onEdgesChange=${onEdgesChange} nodeTypes=${nodeTypes}
     onNodeMouseEnter=${onNodeMouseEnter} onNodeMouseLeave=${onNodeMouseLeave} onNodeClick=${onNodeClick} onPaneClick=${onPaneClick}
     viewport=${viewport} onViewportChange=${setViewport} minZoom=${0.1} maxZoom=${2} proOptions=${{hideAttribution:true}} selectionOnDrag>
     <${Background} color="rgba(212,165,116,.06)" gap=${28}/>
     <${Controls} showInteractive=${false}/>
     <${MiniMap} nodeColor=${n=>FAM[n.data?.family]?.color||'#555'} maskColor="rgba(10,10,15,.7)"/>
    </${ReactFlow}>
    <div class="mm-legend">${Object.entries(FAM).map(([k,v])=>html`<div class="mm-legend-item"><span class="mm-legend-dot" style=${{background:v.color}}></span>${v.icon} ${k}</div>`)}</div>
    ${hover&&html`<${Tooltip} atom=${hover.atom} pos=${hover.pos}/>`}
   </div>
 </div>`
}
createRoot(document.getElementById('root')).render(html`<${ReactFlowProvider}><${App}/></${ReactFlowProvider}>`)

if (window.initGlossaryTooltips) initGlossaryTooltips();
if (window.DemoTour) DemoTour.run();
