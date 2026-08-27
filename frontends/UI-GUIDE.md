# UI Guide — estado actual de las interfaces

Fuente de verdad de la UI. Describe cómo ESTÁ cada vista hoy: el rediseño
que nació en `desk/drawer/tasks/seed-ui-correcciones-y-vistas.md` ya se
implementó y este documento se mantiene como descripción del estado vigente.
Los tests de `tests/ui/` validan ESTE documento sección por sección.

> Convención de IDs: cada elemento interactivo relevante lleva un
> `data-testid` estable (listados por sección). Los tests Playwright
> seleccionan SOLO por `data-testid` — nunca por texto visible ni clases CSS.

---

## 0. Sistema de diseño (todas las vistas)

Base visual: el estilo actual de `frontends/flow_editor/index.html`.

| Token | Valor |
|---|---|
| Fondo página | `#0a0a0f` |
| Panel | `#0d1526` / gradient `rgba(18,18,26,.98)→rgba(10,10,15,.98)` |
| Borde normal | `rgba(245,240,232,.08)` — con accent: `rgba(212,165,116,.18)` |
| Texto | `#f5f0e8` |
| Muted | `rgba(245,240,232,.45)` |
| Accent | `#d4a574` |
| Sans | `'Inter'` |
| Mono | `'JetBrains Mono'` |
| Card | border 1px accent-18%, radius 14px, padding 16px |
| Hover card | `border-color:#d4a574` |
| Familias | self=verde salvia, domain=azul acero, conversation=ámbar, user=magenta |

Reglas: CSS plano (tokens en `frontends/shared/theme.css`); **no** Tailwind en
markup nuevo; sin build step (CDN only); dark siempre.

## 1. Navegación global

**Una sola topbar** (patrón flow_editor), presente en todas las vistas:

```
[brand: {ui.runtime_title}]   Chat · Flow · Mindmap · Users   [kb_label] [health]
```

- `data-testid="nav-topbar"`, links: `nav-chat`, `nav-flow`, `nav-mindmap`, `nav-users`, `nav-dashboard`.
- Se elimina la sidebar de navegación duplicada del chat.
- Brand y labels vienen de `/api/config` — **cero hardcode**.
- Link activo resaltado con accent.

### Rutas

| Vista | Ruta |
|---|---|
| chat-inspector | `/` |
| flow | `/flow` |
| mindmap | `/mindmap` |
| users | `/users` |
| dashboard | `/dashboard` |

`/dashboard` sirve `frontends/dashboard/index.html`: un mock estático con el
chip "Datos de ejemplo", enlazado desde la topbar de todas las vistas
(`nav-dashboard`, label `nav_labels.dashboard`).

Los endpoints `/api/*` no cambian de ruta (solo se agregan nuevos).

---

## 2. Chat-inspector (`/`)

Layout: `[sidebar estado | timeline chat | inspector]`.

### 2.1 Sidebar izquierdo — estado global (`data-testid="chat-sidebar"`)

De arriba a abajo:
1. **Usuario activo** (`sidebar-user`): external_id/alias, traits como chips
   compactos (solo nombre, sin confidence), eventos recientes contados.
2. **Conversación** (`sidebar-conversation`): estado actual si está abierta
   (flow_node + nodo de la state machine); summary si está cerrada.
3. **Agentes** (`sidebar-agents`): config global visible — modelo LLM, KB
   activa, negocio (de `/api/config`).
4. **Agent Pulse** (`sidebar-pulse`): backend status (movido del inspector).

### 2.2 Timeline (columna central)

- Mensajes user/assistant; cada respuesta assistant es seleccionable: la
  card lleva `data-turn-id="t<n>"` (el saludo inicial es `turn-000` y el
  placeholder mientras corre el turno `ghost-*`).
- Referencias `atom-...` en el texto son links (`atom-link`).
- Input abajo: placeholder desde `/api/config.input_placeholder`
  (**prohibido** hardcodear "pizzas"). `data-testid="chat-input"`, `chat-send`.

### 2.3 Inspector derecho (`data-testid="inspector"`)

Secciones, en orden:

**A. Summary** (`inspector-summary`) — 4 datos, nada más:
| Campo | Fuente |
|---|---|
| Usuario reconocido | user_id/external_id del turno |
| Intent (kind) | `nl` / `tool_call` / `fallback` con color |
| Tool llamada | `system_turn.tool` + status, o "—" |
| Step actual | `flow_node`, o "—" |

**B. Context** (`inspector-context`):
- 1-2 frases de por qué el compilador eligió este contexto (scenario +
  conteos + is_empty).
- Atoms agrupados por **familia** (header por familia con su color).
- Cada atom = card clickeable ENTERA (`context-atom-<id>`): título humano
  visible, hover sombreado, click → modal.
- Modal (`atom-modal`): título, id, familia+tipo, summary, tags, answer,
  provenance, path. Cierre con Esc o click fuera.

**C. Razonamiento** (`inspector-reasoning`):
- Una fila por agente que participó: Ontologizador (qué compiló: N atoms,
  scenario), Conversador (qué redactó / o tool decidida), Perfilador (traits
  extraídos), Reflector (solo si aplica).
- Cada fila expandible (acordeón, `data-testid="agent-row"`; el detalle es
  el hijo `.agent-detail`, oculto hasta el click): al abrir muestra el
  detalle disponible del turno (state_trace, transiciones, system_turn
  completo).

*(Se eliminan: "Atoms del contexto" redundante, latency, model route del
summary; Agent Pulse se va al sidebar.)*

---

## 3. Flow (`/flow`)

Editor del grafo de ConversationStep. React Flow + dagre.

### 3.1 Canvas y layout
- Layout dagre `LR` default; **switch LR↔TB** (`flow-layout-toggle`),
  persistido en localStorage, re-layout animado.
- Nodos coloreados por `kind` (interaccion_simple, obtencion_datos, handout,
  llamado_tool). Hover sobre el kind → tooltip explicativo (~300ms, 1-2
  líneas, mapa léxico compartido en `frontends/shared/`).

### 3.2 Edición
- **Paleta** (`flow-palette`): 4 tipos de nodo arrastrables al canvas → crea
  step con defaults.
- **NodeToolbar** al seleccionar (`flow-node-toolbar`): borrar, renombrar,
  cambiar kind.
- Conexión por drag entre handles (habilitada).
- Inspector lateral (`flow-inspector`): edita todos los campos del
  ConversationStep visible según kind.
- **Panel tools** (`flow-tools-panel`): lista de ToolAtoms de la KB activa
  (nombre, descripción, schema). Fuente: `/api/tools` (nuevo). Arrastrar una
  tool al canvas → crea nodo `llamado_tool` con `tool_ref` seteado.

### 3.3 Subflows (XState-style)
- Agrupar nodos en contenedores colapsables (`flow-subflow-<id>`): borde
  dashed, label arriba-izquierda, fondo distinto. Colapsado = caja única con
  edges externos. Anidables. Drag & drop para entrar/salir del grupo.

### 3.4 Hotkeys
Las de la tabla global (sección 6). Overlay de ayuda con `?`.

---

## 4. Mindmap (`/mindmap`)

Vista única de la KB con **3 layouts** (fusión de taxonomía + embeddings).

### 4.1 Layouts (`mindmap-layout-tree|topdown|embeddings`, hotkeys 1/2/3)
| Layout | Disposición |
|---|---|
| árbol (default) | jerarquía familias→subpaths→atoms, dagre LR |
| top-down | misma jerarquía, dagre TB |
| embeddings | posiciones por PCA 2D, edges de similitud coseno, jerarquía oculta |

### 4.2 Sidebar filtro (`mindmap-sidebar`)
- Árbol de namespaces/ramas; click → filtra canvas a esa rama.
- Filtro textual de ramas.

### 4.3 Nodos
- **Drag handle** (única zona de arrastre; el body no mueve el nodo).
- **Collapse children** (badge `+N` al colapsar; hotkey Space).
- **NodeToolbar** (`mindmap-node-toolbar`): borrar · agregar hijo · agregar
  hermano · **link horizontal** (modo linking: click destino crea edge
  cross-family dashed violeta; Esc cancela) · comentario agente ("coming
  soon") · ir al documento.
- Tooltips explicativos en kinds/campos no obvios (mismo mapa léxico).

### 4.4 Cross-family links
- Toggle de relaciones (`mindmap-xfamily-toggle`), OFF por default.
- ON en árbol/top-down: edges horizontales dashed violeta.
- En embeddings se exploran naturalmente por proximidad.

### 4.5 Búsqueda y focus
- **Node search** (`mindmap-search`, Ctrl+F o `/`): match difuso por nombre/
  id/tag/familia; click resultado → centra con fitView.
- En embeddings: doble-click en nodo → centra + resalta vecinos, atenúa el
  resto (hotkey F).

---

## 5. Users (`/users`)

Perfilado + eventos + conversaciones.

### 5.1 Layout
- **Izquierda** (`users-list`): lista de usuarios; cada ficha
  (`user-item-<id>`) con alias, última actividad, #traits, #turnos,
  indicador activo.
- **Derecha**: panel según **selector de vista** (`users-view-selector`):
  Perfil / Eventos / Conversaciones. Info personal del usuario arriba.

### 5.2 Perfil (`users-profile`)
- Sub-columna izq — **KPIs**: cards compactas con gráficos (mood en el
  tiempo, métrica del negocio, frecuencia de respuestas) + resumen numérico
  (turnos, traits, última actividad, días desde registro).
- Sub-columna der — **Traits**: fichas compactas, nombre visible,
  confidence, histórico expandible.
- *Datos hoy inexistentes en SQL (mood, peso): el KPI se renderiza con los
  datos reales disponibles (`ChatHistory`, `UserTraits`, tools) y marca
  "sin datos" donde no haya serie. Prohibido inventar datos.*

### 5.3 Eventos (`users-events`)
- Gráfico de líneas principal con dropdown de métrica.
- Timeline de eventos (tool ejecutada, trait detectado, cambio de estado)
  como puntos.
- Fuente: `/api/events?user_id=` (nuevo endpoint que agrega ChatHistory +
  UserTraits + tablas de tools).

### 5.4 Conversaciones (`users-conversations`)
- Lista por fecha desc: fecha, primer mensaje, #turnos, resultado.
- Click (`conversation-<session_id>`) → navega a `/?session=<id>`; el chat
  carga ese historial (requiere soporte de carga por session_id en el chat
  y en backend).

### 5.5 API
`/api/profiles` ampliado: perfil + traits + eventos recientes +
conversaciones por usuario, en un solo response.

---

## 6. Hotkeys globales (flow + mindmap)

| Acción | Hotkey |
|---|---|
| Buscar nodo | `Ctrl+F` o `/` |
| Borrar selección | `Delete` / `Backspace` |
| Agregar hijo | `Tab` |
| Agregar hermano | `Enter` |
| Link horizontal | `L` |
| Collapse/expand | `Space` |
| Layouts | `1` `2` `3` |
| Centrar en nodo | `F` |
| Cancelar modo | `Esc` |
| Ayuda (overlay) | `?` |

Implementación compartida en `frontends/shared/hotkeys.js`. No capturan si
un input/textarea tiene foco. Overlay de ayuda accesible en ambas vistas.

## 7. Claridad conceptual

Todo concepto no obvio visible en la UI (handout, grounding atoms,
allowed_transitions, completion_condition, required_slots, system_turn,
kind...) tiene tooltip explicativo o label humano. Mapa léxico único en
`frontends/shared/` (glosario concepto→explicación 1-2 líneas) usado por
todas las vistas. Criterio: un usuario nuevo entiende cada sección sin abrir
documentación.

## 8. Endpoints nuevos/modificados (resumen backend)

| Endpoint | Cambio |
|---|---|
| `/api/config` | + `input_placeholder` |
| `/api/tools` | NUEVO: ToolAtoms de la KB activa |
| `/api/events` | NUEVO: serie temporal por user_id |
| `/api/profiles` | ampliado (perfil+eventos+conversaciones) |
| `/api/chat` | soporta carga de historial por session_id |
| rutas UI | `/flow`, `/mindmap`, `/users`, `/dashboard` |
