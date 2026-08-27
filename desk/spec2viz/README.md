# KB Agent Runtime · Documentación de arquitectura (spec2viz)

Documentación backend/frontend generada con `spec2viz`.

Catálogo navegable: `build/architecture.html`.

## Estructura

```
desk/spec2viz/
├── catalog.yml                     # registro de vistas → build/architecture.html
├── wrap_vega.py                    # envuelve matrices Vega en .html embebible
├── current-system-overview.md      # explicación del sistema y de cada vista
├── deployment.backend-frontend.yml # separación backend vs frontend
├── backend/                        # specs backend (semánticos + AST real)
├── frontend/                       # specs frontend
└── build/                          # artefactos renderizados (.mmd/.puml/.html)
```

## Backend vs Frontend

- **Backend** = Python: `kb_agent` (los 4 agentes LLM de `kb_agent/agents/` — Ruteador,
  Orquestador, Gate sobre `agents.base.Agent`, más el Conversador en `llm.py`; `decide_turn` en
  `agent.py` queda como fallback determinístico —, `Orchestrator` que cablea
  SLDBReader/KGDBReader/ContextCompiler/RouterStateMachine/tool registry/Perfilador/Reflector),
  desplegado en Modal (`deploy/modal_app.py`) o local vía uvicorn.
- **Frontend** = HTML/JS estático sin build bajo `frontends/`: seis vistas servidas por el mismo
  FastAPI app factory (`frontends/chat/app.py create_app`, entrypoint `frontends/chat/server.py`):
  `frontends/chat` (chat + Turn Inspector, `/`), `frontends/flow_editor` (editor de flujo, `/flow`),
  `frontends/taxonomy` (mindmap con layout Embeddings, `/mindmap`), `frontends/profiling`
  (perfilado, `/users`), `frontends/dashboard` (mock estático, `/dashboard`) y el tour guiado
  `frontends/shared/demo-tour.js` que cruza las cuatro primeras. `frontends/viz` es sólo backend
  (`export_graph` → `/api/viz/graph`). `DEMO_MODE=1` sirve datos fabricados sin orquestador.
- La frontera se ve en `deployment.backend-frontend.yml` (`artifacts.kind: frontend|backend`).

## Vistas (14)
Registro activo: `catalog.yml`. Explicación de cada una y del sistema completo:
**[`current-system-overview.md`](current-system-overview.md)**.

Tres secciones (una área grande por categoría; backend dividido por concern):

### Backend · Runtime (el motor conversacional)
| Spec | Tipo |
|---|---|
| `backend/logical.agent-ecosystem.yml` | component (modelo lógico, cableado verificado) |
| `backend/current-kb-agent.yml` | component (código real) |
| `backend/state.conversation-flow.yml` | state |
| `backend/sequence.extended-turn.yml` | sequence |
| `backend/matrix.component-turn-lifecycle.yml` | component_view_matrix |
| `backend/current-deploy.yml` | component (código real) |
| `backend/current-tests.yml` | component (código real) |
| `deployment.backend-frontend.yml` | deployment |
| `backend/activity.simulation-harness.yml` | activity |

### Backend · Knowledge (el subsistema de conocimiento)
| Spec | Tipo |
|---|---|
| `backend/current-knowledge-base.yml` | component (código real) |
| `backend/matrix.agents-kb-consumption.yml` | component_view_matrix |

### Frontend (las UIs)
| Spec | Tipo |
|---|---|
| `backend/current-frontends.yml` | component (código real) |
| `frontend/state.chat-ui.yml` | state |
| `backend/matrix.ui-semantic-surface.yml` | component_view_matrix |

Los specs `current-*` reflejan el código HOY (generados con
`spec2viz diagram generate` desde el AST y luego curados a jerarquía
`contains:` + imports reales).

## Regenerar

### Specs de código real (`current-*`)
```bash
spec2viz diagram generate kb_agent --out /tmp/ast.yml --id current-kb-agent
```
Genera el AST crudo (módulos/clases/imports); luego se cura a mano a jerarquía
`contains:` + edges. No usar `--package` (filtra por ruta y da 0 nodos aquí).

### Validar + renderizar
```bash
spec2viz diagram validate desk/spec2viz/backend/*.yml desk/spec2viz/frontend/*.yml desk/spec2viz/deployment.backend-frontend.yml
# todos los mermaid del catálogo de una vez (component/state/sequence/activity/deployment)
spec2viz diagram render desk/spec2viz/backend/{logical,current,sequence,state,activity}.*.yml \
  desk/spec2viz/frontend/state.chat-ui.yml desk/spec2viz/deployment.backend-frontend.yml \
  --renderer mermaid --out desk/spec2viz/build
spec2viz diagram render desk/spec2viz/backend/logical.agent-ecosystem.yml --renderer mermaid --out desk/spec2viz/build
```
Renderers: `plantuml, mermaid, vega, d2, antonia-html, tree, graph, json`.

### Matriz vistas×stages (`component_view_matrix`)
spec2viz la renderiza a Vega JSON, pero el catálogo builtin solo embebe
mermaid/`.svg`/`.html`. El wrapper `wrap_vega.py` envuelve el Vega en un
fragmento `.html` (vega-embed por CDN + leyenda derivada del spec) que sí se
embebe. Flujo:
```bash
for m in component-turn-lifecycle agents-kb-consumption ui-semantic-surface; do
  spec2viz diagram render desk/spec2viz/backend/matrix.$m.yml --out desk/spec2viz/build
  python desk/spec2viz/wrap_vega.py desk/spec2viz/build/matrix.$m.vega.json desk/spec2viz/build/matrix.$m.html
done
```
El `catalog.yml` referencia el `.html` (no el `.vega.json`).

### Catálogo HTML
```bash
spec2viz catalog build --config desk/spec2viz/catalog.yml \
  --out desk/spec2viz/build/architecture.html --base-dir desk/spec2viz --atoms-dir desk/atoms
```
`template: __builtin_default__.html` en `catalog.yml` usa la plantilla builtin de spec2viz (no
hay `template.html` en el repo). El `src` de cada vista es `build/<stem del spec>.mmd|.html`: el
renderer nombra la salida por el stem del archivo del spec, no por su `id`.

## Tipos de diagrama del spec (referencia)

| type | semántica | renderer default |
|---|---|---|
| `sequence` | secuencia | plantuml |
| `state` | máquina de estados | plantuml |
| `component` | componentes/deps | graph (html) |
| `activity` | flujo con decisiones | plantuml |
| `deployment` | despliegue (backend/frontend) | plantuml |
| `component_view_matrix` | matriz vistas×stages | vega |
| `reflection`/enforcement | artefacto semántico 6D | json |

## Limitaciones conocidas

- `diagram generate` solo escanea Python; el frontend (HTML/JS) no tiene escáner AST → sus specs son manuales.
- Mermaid rompe con `<...>` en labels; escapar como `&lt;...&gt;`.
- `activity` requiere campo top-level `end:` (no un step `end`).
- En `deployment`, las `connections` referencian **artifacts**, no nodes, y usan `protocol` (no `label`).
