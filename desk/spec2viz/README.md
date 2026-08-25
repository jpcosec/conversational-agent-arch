# KB Agent Runtime · Documentación de arquitectura (spec2viz)

Documentación backend/frontend generada con `spec2viz`.

Catálogo navegable: `build/architecture.html`.

## Estructura

```
desk/spec2viz/
├── catalog.yml                     # registro de vistas → build/architecture.html
├── template.html                   # plantilla HTML (mermaid.js)
├── deployment.backend-frontend.yml # separación backend vs frontend
├── backend/                        # specs backend (semánticos + AST real)
├── frontend/                       # specs frontend
└── build/                          # artefactos renderizados (.mmd/.puml/.html)
```

## Backend vs Frontend

- **Backend** = Python: agentes ADK (`kb_agent`), pipeline Ontologizador/Conversador, wrapper CLI `sldb`.
- **Frontend** = HTML/JS estático sin build: `kb_chat_ui/index.html` (chat + inspector) y `kb_agent_ui/index.html` (visor de átomos).
- La frontera se ve en `deployment.backend-frontend.yml` (`artifacts.kind: frontend|backend`).

## Vistas (15)

### Global
| Spec | Tipo |
|---|---|
| `deployment.backend-frontend.yml` | deployment |

### Backend · semántico
| Spec | Tipo |
|---|---|
| `backend/component.backend.yml` | component |
| `backend/sequence.chat-turn.yml` | sequence |
| `backend/sequence.agent-retrieval.yml` | sequence |
| `backend/state.chat-session.yml` | state |

### Backend · AST real (código)
Generados con `spec2viz diagram generate` (módulos/clases/imports reales).

| Spec | Fuente |
|---|---|
| `backend/ast.kb_agent.yml` | `kb_agent/` |

### Frontend
| Spec | Tipo |
|---|---|
| `frontend/component.frontend.yml` | component |
| `frontend/state.chat-ui.yml` | state |
| `frontend/activity.atom-viewer.yml` | activity |

## Regenerar

### AST real de código (documentación real)
```bash
spec2viz diagram generate kb_agent           --out desk/spec2viz/backend/ast.kb_agent.yml       --id ast-kb-agent
```
Nota: no usar `--package` (filtra por ruta y da 0 nodos aquí).

### Validar + renderizar
```bash
spec2viz diagram validate desk/spec2viz/**/*.yml
spec2viz diagram render desk/spec2viz/backend/component.backend.yml --backend mermaid --out desk/spec2viz/build
```
Renderers: `plantuml, mermaid, vega, d2, antonia-html, tree, graph, json`.

### Catálogo HTML
```bash
spec2viz catalog build --config desk/spec2viz/catalog.yml \
  --out desk/spec2viz/build/architecture.html --base-dir desk/spec2viz
```

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
