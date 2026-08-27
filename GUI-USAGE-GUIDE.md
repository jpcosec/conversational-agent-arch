# GUI Usage Guide — Puntos de Control y Selectores

Guía visual detallada de las 4 vistas del sistema. Cada sección describe qué se ve en pantalla, los selectores `data-testid` para identificar elementos (útiles para screenshots/test), y los puntos de control que definen el estado de cada vista.

---

## 0.0 Modo Demo

La app corre en **modo demo** solo si se pide explícitamente (`DEMO_MODE=1`; el flag queda en `app.demo_mode`). Sin la variable arranca el runtime real con orquestador + LLM. En demo:

- **No se llama al LLM real**: un state machine determinista (`DemoStateMachineConversador` en `frontends/chat/demo_data.py`) redacta las respuestas y avanza el `flow_node` según palabras clave.
- **Todos los `/api/*` devuelven datos prefabricados** desde `frontends/chat/demo_data.py` (KB de Antonia sintética).
- `/api/config` devuelve `runtime_title: "Demo Agent"` e `input_placeholder: "Escribe algo…"`.

### Tour guiado (`frontends/shared/demo-tour.js`)

Un único recorrido con cuadros flotantes que apuntan a elementos de las 4 vistas (anillo + flecha). Se carga en cada `index.html` con `<script src="/static/demo-tour.js"></script><script>DemoTour.run()</script>`; el progreso vive en `localStorage` (`demo-tour-idx`, `demo-tour-done`) para sobrevivir el cambio de página. Al agotar los cuadros de una vista navega solo a la siguiente (Chat → Flow → Mindmap → Users).

| Selector | Qué es |
|---|---|
| `data-testid="demo-tour"` | Cuadro flotante del paso actual (`.dt-title`, `.dt-text`) |
| `.dt-ring` / `.dt-arrow` | Anillo de resaltado y flecha que apuntan al elemento |
| `data-testid="demo-tour-next"` / `-prev` / `-close` | Botones; también `Enter`/`→`, `←`, `Esc` |
| `data-testid="demo-tour-launch"` | Botón flotante «❓ Guía demo» para reiniciar el tour |

Para tests que no prueban el tour: `localStorage.setItem('demo-tour-done','1')` antes de interactuar (helper `_open` en `tests/ui/test_demo_e2e.py`).

### Máquina de estados del chat demo

Palabras clave → intención → `flow_node`:

| Frase de ejemplo | Intención | `flow_node` resultante | `kind` |
|---|---|---|---|
| "hola" | saludo | `consulta` | `nl` |
| "me da miedo la aguja" | ansiedad | `consulta` | `nl` |
| "cómo me aplico Selfix" | aplicacion | `consulta` | `nl` |
| "quiero un recordatorio" | recordatorio | `obtencion_datos` | `nl` |
| "el lunes a las 20" (con día+hora) | recordatorio | `tool` | `tool_call` |
| "me mareé después de aplicarlo" | evento_adverso | `despedida` | `nl` |

Cuando `kind == tool_call`, el turno trae `system_turn` con la tool `agendar_recordatorio` y sus args (`dia`, `hora`, `nombre`).

---

## 0. Sistema de diseño común

Todas las vistas comparten estos elementos visuales:

- **Fondo**: `#0a0a0f` (negro muy oscuro)
- **Paneles**: gradient `rgba(18,18,26,.98)→rgba(10,10,15,.98)`
- **Bordes**: `rgba(212,165,116,.18)` (ámbar con 18% opacidad)
- **Texto**: `#f5f0e8` (marfil claro)
- **Acento**: `#d4a574` (ámbar/dorado)
- **Sans**: `'Inter', sans-serif`
- **Mono**: `'JetBrains Mono', monospace`

## 0.1 Topbar de navegación (todas las vistas)

Presente siempre en la parte superior de la pantalla.

| Selector | Elemento |
|---|---|
| `data-testid="nav-topbar"` | Header completo de navegación |
| `data-testid="nav-brand"` | Link del brand (título del runtime, viene de `/api/config`) |
| `data-testid="nav-chat"` | Link a Chat (ruta `/`) |
| `data-testid="nav-flow"` | Link a Flow (`/flow`) |
| `data-testid="nav-mindmap"` | Link a Mindmap (`/mindmap`) |
| `data-testid="nav-users"` | Link a Users (`/users`) |
| `data-testid="nav-dashboard"` | Link a Dashboard (`/dashboard`) |

**Punto de control**: el link activo tiene clase `active` y atributo `data-active="true"`. Los labels de los links vienen de `/api/config.nav_labels`. El brand muestra `config.runtime_title`. A la derecha hay dos chips: KB label (`#kbLabel`) y health status (`#healthLabel`).

**Estado visual esperado**:
- Barra horizontal de ~44px de alto
- Brand a la izquierda (texto bold)
- Links monoespaciados en mayúscula, centrados
- Chips metadata a la derecha (KB name + health status)

---

## 1. Chat-Inspector (`/`)

Layout de 3 columnas: sidebar izquierdo | timeline central | inspector derecho.

### 1.1 Sidebar izquierdo — Estado Global

| Selector | Elemento |
|---|---|
| `data-testid="chat-sidebar"` | Panel izquierdo completo (oculto en mobile < md) |
| `data-testid="sidebar-user"` | Card "Usuario" — external_id, traits, eventos |
| `data-testid="sidebar-conversation"` | Card "Estado" — flow_node + kind del último turno |
| `data-testid="sidebar-agents"` | Card "Config" — modelo LLM, KB activa, negocio |
| `data-testid="sidebar-pulse"` | Card "Agent Pulse" — Online/Offline con dot |

**Puntos de control**:
- `#sidebarUserId`: external_id del usuario (viene de `/api/config.name`)
- `#sidebarTraits`: chips de traits extraídos en el último turno
- `#sidebarEvents`: conteo de eventos/traits
- `#sidebarConvState`: "Esperando mensaje…" o "Último: {flow_node} · {kind}"
- `#sidebarModel`: "Modelo: {model}" de `/api/config`
- `#sidebarKB`: "KB: {kb_label}" de `/api/config`
- `#sidebarPulse`: dot verde + "Online" si `/api/health.status === "ok"`

**Estado esperado**:
- 4 cards verticales apiladas, cada una con borde sutil y padding
- Cada card tiene un header monoespaciado con icono Material Symbols
- La última card (Pulse) decorada con un blur radial decorativo

### 1.2 Timeline Central — Conversación

| Selector | Elemento |
|---|---|
| `data-testid="chat-input"` | Textarea de entrada de mensaje |
| `data-testid="chat-send"` | Botón de envío (icono "send") |
| `data-testid="turn-{n}"` | Cada respuesta del asistente (data-turn-id dinámico) |

**Puntos de control**:
- `#messages`: contenedor del scroll de mensajes
- Cada mensaje user: avatar de persona (círculo) + texto Markdown renderizado
- Cada mensaje assistant: avatar de robot + texto + metadata footer (flow_node, atoms count, include_tags, kind badge)
- Los mensajes assistant son clickeables → seleccionan el turno para el inspector
- Links a atoms en el texto: clase `atom-link`, data-atom="{atom-id}", click → modal
- `#sessionTitle`: "Session: {business_name}"
- `#sessionBadge`: "ID: {session_id}"
- Placeholder input: viene de `/api/config.input_placeholder`

**Estado esperado**:
- Línea vertical decorativa a la izquierda (pseudo-elemento)
- Mensajes en cards, usuario y asistente alternados
- Cada turno assistant tiene footer con flow_node, atom count, include_tags, kind
- Al hacer click en un turno assistant, se ilumina con glow accent (`glow-active`)

### 1.3 Inspector Derecho — Auditoría de Turno

| Selector | Elemento |
|---|---|
| `data-testid="inspector"` | Panel derecho completo |
| `data-testid="inspector-summary"` | Sección Summary (4 campos) |
| `data-testid="inspector-context"` | Sección Context (atoms por familia) |
| `data-testid="inspector-reasoning"` | Sección Razonamiento (agentes) |
| `data-testid="context-atom-{id}"` | Card de un átomo específico en Context |
| `data-testid="atom-modal"` | Modal de detalle de un átomo |
| `data-testid="agent-row"` | Fila de un agente (expandible) |

**Puntos de control en Summary**:
- 4 datos en grilla 2×2: Usuario reconocido, Intent (kind coloreado: `fallback`=rojo error, `tool_call`=terciario, `nl`=secondary), Tool llamada (o "—"), Step actual (flow_node)

**Puntos de control en Context**:
- 1-2 frases explicativas: "{N} atoms en contexto · Retenidos: X · Nuevos: Y · Desertados: Z"
- Grupo por familia (self=verde, domain=azul, conversation=ámbar, user=magenta)
- Cada atom es una card clickeable entera: título humano visible + ID + role + grounds_step
- Click → abre modal (`data-testid="atom-modal"`)

**Puntos de control en Razonamiento**:
- 5 filas de agentes reales del pipeline, en orden de ejecución: **Ruteador de contexto**, **Orquestador**, **Conversador**, **Gate**, **Perfilador** (async post-turno).
- Cada fila: icono + nombre + descripción con datos reales de `turn.decisions`.
- Click → expande acordeón:
  - Ruteador: bundle `[{doc_id, family, motivo, score}]`, con conteo por tipo de motivo (piso de seguridad / grounding / similitud / traits).
  - Orquestador: `kind`, `reason`, transición `step.before → step.after`, `allowed_transitions`, y veto si aplica.
  - Conversador: borrador pre-gate y texto final post-gate.
  - Gate: `approved`, `action`, `reasons`, `criterion_ids` (o `skipped` en turnos no-NL).
  - Perfilador: traits nuevos del turno.
- En demo estos datos vienen del state machine (`decisions` prefabricado), con la misma forma que el runtime real.

**Estado esperado por defecto (sin turno seleccionado)**:
- "Selecciona una respuesta del asistente para auditar su turno."
- Botón "close" (icono) para limpiar selección

### 1.4 Modal de Átomo

| Selector | Elemento |
|---|---|
| `data-testid="atom-modal"` | Backdrop + contenedor modal |
| `#modalTitle` | Título del modal (atom_id) |
| `#modalBody` | Cuerpo con datos completos del atom |

**Contenido del modal**:
- Título
- Familia (self/domain/conversation/user)
- Path del documento
- Tags (chips)
- Body en Markdown renderizado

---

## 2. Flow (`/flow`)

Editor de grafo de ConversationStep con React Flow + dagre.

### 2.1 Sidebar Izquierdo — Paleta

| Selector | Elemento |
|---|---|
| `data-testid="flow-palette"` | Panel de tipos de paso arrastrables |
| `data-testid="flow-palette-item"` | Cada tipo de paso (4 tipos) |

**Tipos de paso disponibles** (con su color e icono):
- **Interacción simple** (`#e6a85c`, 💬)
- **Obtención de datos** (`#c97db9`, 📝)
- **Handout** (`#7fb3d5`, 🤝)
- **Llamado a tool** (`#7cba7c`, ⚙️)

**Puntos de control**:
- Cada ítem es arrastrable (drag & drop) al canvas
- Al soltar, crea un ConversationStep con valores por defecto
- `data-testid="flow-add-subflow"`: botón para añadir subflow agrupador
- `data-testid="flow-subflow-{id}"`: cada subflow listado con toggle collapse

### 2.2 Canvas Central — Grafo

| Selector | Elemento |
|---|---|
| `data-testid="flow-drag-handle"` | Asa de arrastre en cada nodo (⠿) |
| `data-testid="flow-node-toolbar"` | Toolbar contextual del nodo seleccionado |

**Herramientas del NodeToolbar**:
- `data-testid="flow-node-rename"`: Renombrar (abre prompt)
- `data-testid="flow-node-kind"`: Cambiar tipo (cicla entre los 4 kinds)
- `data-testid="flow-node-delete"`: Borrar nodo

**Toolbar superior del canvas**:
| Selector | Función |
|---|---|
| `data-testid="flow-layout-toggle"` | Alterna LR ↔ TB (persiste en localStorage) |
| `data-testid="flow-link-horizontal"` | Modo linking (entra en modo, click en destino crea edge) |
| Botón "💾 Save" | Guardar (sin selector específico) |

**Estado esperado**:
- Nodos coloreados por kind (borde izquierdo más grueso del color del kind)
- Conexiones con flechas (arrow markers)
- Background grid sutil
- Minimap en esquina inferior derecha
- Controles de zoom (+/-) en esquina inferior izquierda

### 2.3 Inspector Derecho — Edición de Nodo

| Selector | Elemento |
|---|---|
| `data-testid="flow-inspector"` | Header del inspector |
| Contenido dinámico | Campos según el kind del nodo |

**Campos editables**: Nombre, Tipo (select), Instrucciones (textarea), + campos específicos por kind:
- `obtencion_datos`: required_slots
- `handout`: handout_target
- `llamado_tool`: tool_ref, tool_params

**Campos siempre visibles (no editables directamente)**:
- Transiciones (chips)
- Grounding Atoms (chips)
- Condición término (textarea)
- ID (mono, gris)

### 2.4 Tools Panel (Inferior del Sidebar)

| Selector | Elemento |
|---|---|
| `data-testid="flow-tools-panel"` | Panel de herramientas de la KB |
| `data-testid="flow-tool-item"` | Cada tool listada (arrastrable) |

**Estado esperado**:
- Lista de ToolAtoms de la KB activa (fuente: `/api/tools`)
- Cada tool: nombre (bold) + descripción (truncada a 50 chars)
- Arrastrar una tool al canvas → crea nodo `llamado_tool` con `tool_ref` seteado
- Si no hay tools: "Sin tools en esta KB" en gris

---

## 3. Mindmap (`/mindmap`)

Visualización de la KB con 3 layouts (árbol, top-down, embeddings).

### 3.1 Sidebar Izquierdo — Filtro y Layout

| Selector | Elemento |
|---|---|
| `data-testid="mindmap-sidebar"` | Panel lateral izquierdo |

**Secciones**:
- **Filtrar rama**: input de búsqueda + lista de familias (self, domain, conversation, user)
- Cada rama es clickeable: clase `mm-rama`, al activarse tiene clase `active` + color accent
- **Layout** (parte inferior): 3 opciones clickeables
  - `data-testid="mindmap-layout-tree"`: Árbol LR (default)
  - `data-testid="mindmap-layout-topdown"`: Top-Down (TB)
  - `data-testid="mindmap-layout-embeddings"`: Embeddings (PCA 2D)
- `data-testid="mindmap-xfamily-toggle"`: checkbox para mostrar links horizontales entre familias

**Estado esperado**:
- Sidebar angosto (220px) con scroll vertical
- Familias listadas con icono + nombre
- Rama activa resaltada con background accent transparente

### 3.2 Canvas Central — Grafo de Conocimiento

| Selector | Elemento |
|---|---|
| `data-testid="mindmap-search"` | Input de búsqueda de nodos (en topbar del canvas) |
| `data-testid="mindmap-node-toolbar"` | Toolbar flotante del nodo seleccionado |
| `data-testid="mindmap-drag-handle"` | Asa de arrastre (⠿) en cada nodo |
| `data-testid="mindmap-node-{id}"` | Cada nodo en el grafo |

**Colores por familia**: self=`#7cba7c` (verde), domain=`#7fb3d5` (azul), conversation=`#e6a85c` (ámbar), user=`#c97db9` (magenta)

**Tipos de nodo**:
- **Root** (familia): borde del color de la familia, fondo del mismo color, texto oscuro, icono grande
- **Branch** (subpath): fondo tintado, borde del color de la familia
- **Atom**: fondo oscuro, borde izquierdo grueso del color de la familia, 5W icono, tipo en mono

**NodeToolbar acciones**:
- 🗑 Borrar
- ＋hijo Agregar hijo (Tab)
- ＋herm Agregar hermano (Enter)
- 🔗 Link horizontal (L)
- 💬 Comentario agente (coming soon)
- ↗doc Ir al documento (abre `/api/atom/{id}`)

**Tooltip de atom** (hover sobre nodo atom): aparece modal flotante con atom_id, label, 5WH, summary, tags

**Estado esperado**:
- Layout dagre LR por defecto
- Cada familia es una columna separada (self, domain, conversation, user en orden)
- Edges jerárquicos padre → hijo
- Minimap en esquina inferior derecha
- Leyenda flotante (esquina inferior derecha): colores de familias
- Topbar del canvas con input de búsqueda + hint de interacción

### 3.3 Leyenda y Decoraciones

| Selector | Elemento |
|---|---|
| `.mm-legend` | Leyenda fija en esquina inferior derecha |

**Contenido**: 4 ítems con dot color + icon + nombre de familia

---

## 4. Users (`/users`)

Vista unificada de perfilado, eventos y conversaciones de usuarios.

### 4.1 Sidebar Izquierdo — Lista de Usuarios

| Selector | Elemento |
|---|---|
| `data-testid="users-list"` | Contenedor de la lista de usuarios |

**Cada usuario**:
- `data-testid="user-item-{user_id}"`: chip clickeable con alias, ID, última actividad, traits count, turnos count
- Clase `active` cuando seleccionado

### 4.2 Selector de Vista

| Selector | Elemento |
|---|---|
| `data-testid="users-view-selector"` | Barra de 3 botones |
| `data-testid="view-profile"` | Botón "Perfil" |
| `data-testid="view-events"` | Botón "Eventos" |
| `data-testid="view-conversations"` | Botón "Conversaciones" |

**Estado esperado**: el botón activo tiene clase `active`.

### 4.3 Perfil (`data-testid="users-profile"` representado por el panel)

Dos sub-columnas:

**Izquierda — KPIs** (`data-testid="profile-kpis"`):
- **Turnos**: total conversaciones
- **Traits**: rasgos aprendidos
- **Última actividad**: fecha
- **Actividad semanal**: gráfico de barras SVG (6 semanas)
- **Mensajes por semana**: gráfico de barras SVG secundario

**Derecha — Traits** (`data-testid="profile-traits"`):
- Fichas de traits: título, categoría (chip), ID, barra de confianza (gradient ámbar), source, descripción
- Si no hay traits: "Sin traits todavía."

### 4.4 Eventos (`data-testid="users-events"`)

Tres gráficos:
- **Adherencia semanal (%)**: gráfico de línea SVG (6 puntos)
- **Frecuencia de contacto**: barras SVG
- **Mood estimado**: barras SVG

Debajo: lista de eventos recientes (últimas 5 conversaciones).

### 4.5 Conversaciones

| Selector | Elemento |
|---|---|
| `data-testid="conversation-{session_id}"` | Cada conversación listada (clickeable → navega a `/?user={external_id}`) |

**Cada conversación**: fecha, resumen, #turnos, resultado.

---

## 5. Hotkeys Globales (Flow + Mindmap)

| Acción | Tecla | Notas |
|---|---|---|
| Buscar nodo | `Ctrl+F` o `/` | Enfoca input de búsqueda |
| Borrar selección | `Delete` / `Backspace` | Elimina nodo seleccionado |
| Agregar hijo | `Tab` | Con nodo seleccionado |
| Agregar hermano | `Enter` | Con nodo seleccionado |
| Link horizontal | `L` | Activa modo linking |
| Collapse/expand | `Space` | Colapsa/expande hijos |
| Layout 1/2/3 | `1` `2` `3` | Árbol / Top-Down / Embeddings |
| Centrar en nodo | `F` | Fit view en nodo seleccionado |
| Cancelar modo | `Esc` | Sale de linking/search |
| Ayuda | `?` | Overlay con todas las hotkeys |

---

## 6. Endpoints Clave (Referencia)

| Endpoint | Propósito | Vista(s) |
|---|---|---|
| `/api/config` | Config del negocio (title, labels, placeholder) | Todas |
| `/api/health` | Estado del backend | Todas (topbar) |
| `/api/chat` | POST: enviar mensaje | Chat |
| `/api/atom/{id}` | GET: detalle de un atom | Chat (modal), Mindmap |
| `/api/taxonomy` | GET: árbol de la KB | Mindmap |
| `/api/tools` | GET: ToolAtoms de la KB | Flow |
| `/api/profiles` | GET: perfiles + traits + eventos + conversaciones | Users |
| `/api/events` | GET: serie temporal por user_id | Users |
| `/api/flow` | GET: grafo de ConversationStep | Flow |
| `/api/viz/graph` | GET: embeddings graph (PCA 2D) | Mindmap |

---

## 7. Estados por Defecto (Pantallas Vacías)

| Vista | Estado inicial esperado |
|---|---|
| **Chat** | Input vacío, inspector dice "Selecciona una respuesta…", sidebar con datos de config, un mensaje de greeting |
| **Flow** | Grafo cargado desde `/api/flow` (o vacío si no hay steps), inspector dice "Selecciona un nodo para inspeccionar" |
| **Mindmap** | Grafo cargado desde `/api/taxonomy`, sidebar con familias, leyenda visible, topbar con search |
| **Users** | Lista de usuarios cargada desde `/api/profiles`, detalle vacío ("Selecciona un usuario…"), vista Perfil activa por defecto |

---

*Fin de la guía. Los selectores listados son estables y pueden usarse para screenshots automatizados con Playwright u otras herramientas.*