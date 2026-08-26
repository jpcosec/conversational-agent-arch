---
id: seed-ui-correcciones-y-vistas
title: UI tidy — navegación, chat-inspector, mindmap, docs+tests
status: open
tags:
- seed
- ui
- frontends
- navigation
- chat
- inspector
- mindmap
---

## Semilla

Scope completo de reorganización de UIs, tras recabar información del código
(frontends/*, app.py, tests/ui) y discutir cada vista.

Depende de: seed-recomponer-spec2viz-y-atoms.
Áreas: 1) navegación, 2) chat-inspector, 3) sidebar left, 4) flow, 5) mindmap,
6) user profiling, 7) placeholder/desharcodeos, 8) documentación UX, 9) tests.

---

## 0. Estilo global — alinear con Flow Editor

La estética de TODAS las UIs debe parecerse a `frontends/flow_editor/index.html`:

**Paleta y fondo:**
- Fondo `#0a0a0f`, paneles `#12121a~#0a0a0f` con gradient.
- Bordes `rgba(212,165,116,.18)` (accent con 18% opacidad).
- Texto `#f5f0e8`.
- Acento `#d4a574` (ámbar).

**Layout:**
- Sin header top duplicado (el flow editor solo tiene topbar minimal con brand + nav).
- Sidebar angosto (280px), fondo gradient, border derecho con accent.
- Área principal flex-1 sin decoración extra.
- Scrollbars sutiles (personalizadas, mismas que flow).

**Fuentes y tipografía:**
- `'Inter', sans-serif` para cuerpo.
- `'JetBrains Mono', monospace` para código/datos.
- Tamaños: 11px mono para metadatos, 13-15px para contenido.

**Componentes (válido para todas las vistas):**
- Cards con `border:1px solid rgba(212,165,116,.18)`, `border-radius:14px`, `padding:16px`.
- Hover: `border-color:#d4a574`, opcional `box-shadow:0 0 0 1px #d4a574`.
- Botones/links: `font-family:'JetBrains Mono'`, `font-size:11px`, `padding:6px 12px`.
- Tags/chips: `font-size:10px`, `px-1.5 py-0.5`, `border-radius:8px`.
- Transiciones: `all .15s` o `transition:all .18s`.

**NO usar:**
- Tailwind utility classes en markup nuevo (flow editor usa CSS plano, no Tailwind).
- Fondos de panel blancos/gris claro.
- Textos grises (#666, #999) — usar `var(--muted)` con opacidad.
- Botones con bordes redondeados excesivos (>16px).

**Referencia visual:** leer `frontends/flow_editor/index.html` líneas 1-80 (setup
completo: imports, reset CSS, layout, sidebar, topbar, cards).

---

## 1. Navegación global — unificar

**Problema:** 2 navbars duplicadas (header top + sidebar left), mismos 5 links,
2 sistemas de estilo. Sidebar dice "Workbench · arch: conversational-agent"
hardcodeado.

**Qué hacer:**
- Unificar en un solo sistema de navegación (1 navbar, no 2).
- Nombres nuevos de vistas (ver sección 4 abajo).
- El título y descripción del sidebar deben venir de config (no hardcode).

---

## 2. Chat — Inspector derecho

Estructura actual (de arriba abajo):

| Hoy | Reemplazo |
|---|---|
| **Resumen del Turno** (latency, kind, model, traits) | → **Summary** reducido: user reconocido? / intent / tool llamada / step actual. Quitar latency, model, traits. |
| **Mesa de Contexto** (retained/added/removed) | → **Context** (1-2 frases: por qué el compilador eligió este contexto y estos atoms). Organizado por **familia** (self/domain/conversation/user). Mostrar solo título humano. |
| **Atoms del contexto** (cards de cada atom) | → **Eliminar**. Es redundante con Context y "se ve re feo". Los atoms van dentro de Context. |
| **Razonamiento** (state_trace + tool ejecutada) | → **Summary por agente**: Ontologizador (qué compiló), Conversador (qué redactó), Perfilador (qué extrajo), Reflector (si aplica). Click → expandir detalle (acordeón o modal). |
| **Agent Pulse** (health status) | → Mover a sidebar izquierdo (sección global). |

**Mejoras de interacción en Context:**
- Click en toda la card (no solo texto).
- Hover → sombreado.
- Modal con info completa del atom: summary, tipo/familia (hoy falta), provenance, tags.

**Detalle de Razonamiento por agente:**
- Cada motor muestra su "conversación interna" como minilog.
- ¿Acordeón inline o modal? → decidir al implementar.

---

## 3. Chat — Sidebar izquierdo (contenido global)

Hoy: solo links de navegación + "API Docs". Pasa a ser **navegación + panel de estado global**.

Mostrar:
- **Info del usuario activo**: eventos, traits (sin entrar al detalle).
- **Summary de la conversación** si está cerrada.
- **Estado de la conversación** si está abierta.
- **Configuraciones globales de los agente**s (desde /api/config).
- **Agent Pulse** (movido del inspector).

**Pregunta pendiente:** ¿sidebar único (navegación arriba, estado abajo, scroll) o 2 paneles separados? → decidir al picar.

---

## 4. Nombres de vistas (renombrar)

| Actual | Nuevo | Ruta | Por qué |
|---|---|---|---|
| Chat | **chat-inspector** | `/` (sigue siendo landing) | El nombre distingue que no es solo chat |
| Flow Editor | **flow** | `/flow` | "Editor" es ruido |
| Taxonomía | **mindmap** | `/mindmap` | El `<title>` ya dice "Mindmap" |
| Perfilado | **user profiling** | `/profiling` | Inglés consistente |
| Embeddings | → mod de mindmap | (no es vista separada) | Comparte React Flow, es toggle |

**Side-wide rename:**
- `<title>` HTML
- href en navbar
- Rutas del backend (app.py: routers)
- Labels en navegación

**Pendiente:** ¿mantener rutas viejas como redirects? / ¿Embeddings como toggle dentro de mindmap o vista separada desde mindmap? → decidir al picar.

---

## 5. Flow (ex Flow Editor)

Renombrar a `flow`. Ruta `/flow`. Mejoras de funcionalidad:

### 5.1 Subflows colapsables (inspirado en XState)

- Poder agrupar nodos en **cajitas contenedoras** (subflows).
- La cajita se colapsa/expande: colapsada muestra solo el nombre del subflow
  y las aristas que entran/salen del grupo; expandida muestra los nodos internos
  con sus conexiones.
- Inspiración visual: XState (xstate.js.org) — regiones con borde dashed,
  label en el borde superior izquierdo, fondo ligeramente distinto.
- Agregar/quitar nodos de un subflow debe ser drag & drop.
- Los subflows deben anidables (subflow dentro de subflow).

### 5.2 Edición usable (borrar + drag & drop)

- Falta **botón para borrar** nodos/aristas: click en nodo → toolbar contextual
  con opciones (borrar, renombrar, cambiar kind). Hoy la UI es solo visualización.
- **Drag & drop más usable**:
  - Paleta lateral con tipos de nodo (`interaccion_simple`, `obtencion_datos`,
    `handout`, `llamado_tool`) que se arrastran al canvas.
  - Al soltar, crear el ConversationStep con valores por defecto y mostrarlo
    en el grafo.
  - Conexión entre nodos: arrastrar desde un handle de salida a un handle de
    entrada (React Flow ya lo soporta nativamente, solo falta habilitarlo).
- Al crear/editar un nodo, el inspector lateral debe permitir editar **todos**
  los campos del ConversationStep (instructions, required_slots, tool_ref,
  grounding_atoms, completion_condition, etc.).

### 5.3 Toolbar de tools (vista de tools existentes)

- En el costado (o como panel toggleable), mostrar un **listado de tools
  existentes**: las declaradas en la KB activa (`ToolAtom` atoms, tipo
  `type.knowledge.tool`).
- Esto implica crear **un endpoint** `/api/tools` que devuelva los ToolAtoms
  del store activo (parecido a `/api/taxonomy` pero filtrando solo tools).
- O reusar `/api/taxonomy` y filtrar por familia `self:tool` en el frontend.
- Cada tool en el listado muestra: nombre, schema JSON (args), descripción.
- Arrastrar una tool desde el listado al canvas debería crear un nodo
  `llamado_tool` con `tool_ref` ya seteado.
- **Vista de tools independiente** (opcional): ruta `/tools` como página
  standalone que liste todas las tools de la KB activa, con detalle de schema
  y en qué steps se usan.

### 5.4 Layout: horizontal ↔ vertical

- Botón/switch para cambiar la dirección del layout automático (dagre) entre
  `LR` (left-to-right, horizontal) y `TB` (top-to-bottom, vertical).
- Hoy usa `rankdir=LR` hardcodeado en el layout de dagre.
- Al cambiar, re-layout automático del grafo completo con animación.
- Recordar la preferencia en `localStorage`.

### 5.5 Scope de implementación

Prioridades:
1. Borrar nodos + drag & drop básico (5.2) — desbloquea edición mínima.
2. Layout horizontal↔vertical (5.4) — fácil, solo cambiar rankdir.
3. Toolbar de tools (5.3) — depende de endpoint nuevo o filtro taxonomy.
4. Subflows colapsables (5.1) — más complejo, requiere React Flow grupos.

### 5.6 Tooltips explicativos en conceptos no obvios

Ciertos conceptos del modelo no son intuitivos (p.ej. `handout`,
`interaccion_simple` vs `obtencion_datos`, `grounding_atoms`,
`completion_condition`). Al hacer hover sobre:
- **el label del kind** de un nodo (en el grafo o en el inspector)
- **el nombre de un campo** en el inspector de edición
- **un tag o chip** (como los `conversation:steps.*`)

 debe aparecer un **tooltip** (no modal) con una explicación en lenguaje
 natural de qué significa ese concepto y para qué sirve.

**Formato del tooltip:**
- Aparece a los ~300ms de hover.
- Texto corto (1-2 líneas), sin tecnicismos.
- Ejemplo: hover sobre `handout` → "Deriva el usuario a otro canal o
  persona (humano, otro bot, formulario externo)."
- Las explicaciones pueden venir de:
  - Un `description` field en el modelo (si existe en el ConversationStep).
  - Un mapa estático en el frontend (kind → descripción).
  - Opcionalmente desde la KB vía un nuevo endpoint `/api/glossary`.

**No aplicar a:**
- IDs de atoms (son opacos por diseño, el modal ya explica).
- Timestamps o metadatos evidentes.

**NC   Patrón reusable:** si armamos un mapa léxico (`kind → desc`) en el
frontend, el mismo tooltip sirve en Flow, Mindmap (kinds de atom), y en
cualquier vista que muestre conceptos del modelo.

---

## 6. Mindmap (ex Taxonomía + Embeddings)

Renombrar a `mindmap`. Ruta `/mindmap`.
**Taxonomía + Embeddings se fusionan**: Mindmap es la vista base (árbol
familias→atoms con editor inline). Embeddings es un **toggle/switch** que
superpone la proyección PCA 2D sobre el mismo árbol, coloreado por familia.
React Flow es la base común. Colores por familia: self=verde salvia,
domain=azul acero, conversation=ámbar, user=magenta suave.

### 6.1 Sidebar izquierdo — filtro por rama

- Sidebar con árbol de **namespaces/ramas** (ej: `conversation:steps.*`,
  `self:*`, `domain:*`).
- Click en una rama → filtra los nodos visibles en el canvas a solo esa rama
  y sus hijos.
- Búsqueda/filtro textual sobre nombres de ramas.

### 6.2 Collapse / expand

- Los nodos con hijos deben ser colapsables: collapse → oculta los hijos y
  muestra solo el padre con un badge de count (`+3`).
- Botón en el nodo (esquina) o en el toolbar del nodo.

### 6.3 Drag handle en nodos (no mover arrastrando el body)

- Usar `drag-handle` de React Flow
  (https://reactflow.dev/examples/nodes/drag-handle): un asa pequeña
  (icono `grid_view` o seis puntos) en cada nodo como único punto de
  arrastre. Así el cuerpo del nodo no se mueve al hacer click, evitando
  moverlos sin querer.
- Adicionalmente, botón `collapse children` en el mismo nodo.

### 6.4 Node toolbar

Usar `NodeToolbar` de React Flow
(https://reactflow.dev/examples/nodes/node-toolbar) — toolbar flotante que
aparece al hover/select sobre un nodo, con:
- **Borrar** (delete node).
- **Agregar hijo** (create child atom bajo este).
- **Agregar hermano** (create sibling atom al mismo nivel).
- **Dejar comentario agente** (placeholder: "coming soon" — abre un textarea
  que persiste un comentario de agente asociado al atom, para que otro
  agente lo lea).
- (opcional) **Ir al documento** (abre el modal de detalle).

### 6.5 Links horizontales entre familias (cross-family edges)

Hoy los edges en el árbol son jerárquicos (padre→hijo por namespace). Pero
existen relaciones semánticas _horizontales_ entre atoms de distintas
familias (ej: `trait-cardiaco` → `domain-procedimientos-especiales`).

- Agregar un **filtro de relaciones**: toggle/selector que active la
  visualización de cross-family edges.
- Por defecto **NO** se muestran (solo jerarquía).
- Al activarlos, se dibujan edges entre atoms que comparten tags, o que
  tienen relaciones explícitas en el modelo (si existen).
- Mecanismo de resolución a definir: ¿desde el backend (nuevo endpoint que
  devuelva relaciones) o desde el frontend (match por tags compartidos)?
  → decidir al implementar.
- Visualmente: edges con línea dashed y color distinto a los jerárquicos.

---

## 6a. Subtask derivada — claridad de conceptos en toda la UI

Problema: ciertos conceptos del modelo (\"grounding atoms\", `handout`,
`allowed_transitions`, `completion_condition`, etc.) no son intuitivos ni
están explicados en la UI. El usuario no entiende qué significan ni cómo
usarlos.

**Qué hacer (auditar vista por vista):**
1. Listar todos los conceptos/modelos que aparecen en la UI (en labels,
   tooltips, inspector, modal, sidebar).
2. Para cada uno, determinar si el nombre actual es auto-explicativo o
   necesita contexto.
3. Donde no lo sea, agregar:
   - Tooltip con explicación breve (ver 5.6).
   - O cambiar el label por algo más humano (ej: \"grounding atoms\" →
     \"atoms relacionados\" o \"hechos de apoyo\").
   - O agregar un enlace a un glosario/doc.

**Ejemplo concreto:** \"grounding atoms\" podría renombrarse a \"atoms
relacionados\" o \"hechos de apoyo\" y mostrar los atoms linkeados en lugar de
solo el ID. Revisar este y otros casos similares.

**Criterio de aceptación:** un usuario nuevo sin contexto del modelo interno
debe poder entender cada sección de la UI sin abrir documentación externa.

---"}]

## 7. User Profiling (ex Perfilado)

- Renombrar a `user profiling`. Ruta `/profiling`.
- Mantener funcionalidad actual (fichas de usuario × traits candidatos).
- Sin cambios de contenido en este scope.

---

## 8. Placeholder del input de chat (deshardcodeo)

**Problema:** el placeholder del textarea dice `ej: que pizzas tienen?` (Don Peppe hardcodeado, línea 159 de index.html).

**Solución:**
- Agregar `input_placeholder` a `project.config.yaml` (sección `ui:`).
- Exponerlo en `ProjectConfig.to_public_dict()` en `kb_agent/project_config.py`.
- La UI lo lee desde `/api/config` y lo setea como placeholder.
- Valor por defecto neutro: `"Escribe tu mensaje..."`.
- Hoy `/api/config` ya expone `name`, `greeting`, `runtime_title`, `kb_label`, `model`, `mode`. Agregar `input_placeholder`.

---

## 9. Documentación UX

- Actualizar `frontends/chat/UX-expected.md` para reflejar el nuevo inspector (sin sección atoms redundante, con Context por familia, Razonamiento por agente, Summary reducido).
- Crear o actualizar `frontends/chat/USAGE.md` que documente cómo se usa cada vista del chat-inspector, qué significa cada sección, a qué endpoint corresponde.
- Las vistas nuevas (mindmap, flow rename) deben reflejarse en `current-system-overview.md` y `desk/spec2viz/README.md`.
- Spec2viz: actualizar `matrix-ui-semantic-surface` si cambian las UIs. Agregar doc de uso en el overview.

---

## 10. Tests (Playwright)

Tests existentes (`tests/ui/test_playwright_smoke.py`): solo smoke básico.
Cobertura faltante (la interfaz nueva debe poder testearse):

- [ ] chat: envío de mensaje → inspector con Context por familia.
- [ ] chat: click en card de Context → modal con info completa del atom.
- [ ] chat: Razonamiento → expandir agente → ver detalle.
- [ ] chat: sidebar izquierdo → muestra traits/estado/config.
- [ ] mindmap: carga árbol taxonomía.
- [ ] mindmap: toggle embeddings → grafo PCA superpuesto.
- [ ] flow: carga grafo ConversationStep.
- [ ] flow: click en nodo → inspector.
- [ ] user profiling: carga y click en usuario → fichas de traits.
- [ ] navegación: links funcionan, nombres nuevos.
- [ ] placeholder: viene de config, no hardcodeado.

Cada test debe usar fixture `offline_orchestrator` (LLM fake, ya existe en
`tests/support/fakes.py`). El conftest ya tiene `playwright_available()` y el
fixture `base_url` levanta uvicorn in-process — reusar.

---

## Notas de implementación

- **chat-inspector tiene prioridad 1**: es la vista principal y la que más
  cambios tiene (inspector entero, sidebar, placeholder).
- **mindmap tiene prioridad 2**: fusión taxonomía+embeddings.
- **Navegación y renombres** (prioridad 3): se pueden hacer después de que las
  vistas funcionen, o en paralelo si no tocan la lógica.
- **Deshardcodeo del placeholder** es trivial y se puede hacer independiente.
- Dependencias: nada de esto requiere cambios en el backend (solo agregar
  `input_placeholder` a `project_config.py`). Todo es frontend/estático.
- La UI no tiene build step (Tailwind/React por CDN) — los cambios son
  directamente sobre los `.html`.

## Preguntas abiertas (resolver al picar)

1. Embeddings como toggle dentro de mindmap vs vista separada accesible desde mindmap.
2. Razonamiento por agente: ¿acordeón inline dentro del inspector o modal?
3. Sidebar izquierdo: ¿panel único (navegación + estado) o 2 paneles separados?
4. Rutas viejas (`/conversation_flow_editor`, `/taxonomy_explorer`, `/profiling_viewer`, `/viz`): ¿redirect a las nuevas?