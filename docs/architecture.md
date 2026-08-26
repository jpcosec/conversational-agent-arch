# KB Agent Runtime — Arquitectura

## Índice

1. [Arquitectura general](#1-arquitectura-general)
2. [KB y la doctrina semántica](#2-kb-y-la-doctrina-semántica)
3. [Componentes](#3-componentes)
4. [Flujo de un turno](#4-flujo-de-un-turno)
5. [ContextCompiler y CompiledDocument](#5-contextcompiler-y-compileddocument)
6. [Diagrama de conversación (KGDB)](#6-diagrama-de-conversación-kgdb)
7. [Orquestador y ciclo de vida](#7-orquestador-y-ciclo-de-vida)
8. [Servidor FastAPI y UI](#8-servidor-fastapi-y-ui)
9. [Contrato de datos UI ↔ Backend](#9-contrato-de-datos-ui--backend)
10. [Modelos de datos](#10-modelos-de-datos)
11. [Decisiones de diseño](#11-decisiones-de-diseño)
12. [Tests](#12-tests)

---

## 1. Arquitectura general

```
CLIENTE (UI / CLI / Test)
    │ POST /api/chat
    ▼
┌──────────────────────────────────────────┐
│  kb_chat_ui/server.py: FastAPI           │
│  - mapea session_id <-> external_id      │
│  - adapta respuesta a formato UI          │
└────────────────┬─────────────────────────┘
                 │ Orchestrator.handle_turn()
                 ▼
┌──────────────────────────────────────────┐
│  kb_agent/orchestrator.py: Orchestrator  │
│  - orquesta el ciclo del turno           │
│  - crea RouterStateMachine               │
│  - persiste ChatHistory + SessionState   │
│  - corre Perfilador async                │
│  - arma el contexto atómico para la UI   │
└──┬───────────────┬──────────────┬────────┘
   │               │              │
   ▼               ▼              ▼
┌──────────┐ ┌───────────┐ ┌──────────┐
│Compiler  │ │Conversador│ │ SQL      │
│ SLDB+KGDB│ │ Gemini NL │ │identity, │
│ Produce  │ │ Tool call │ │session,  │
│Compiled  │ │ Fallback  │ │traits,   │
│Document  │ │           │ │history   │
└──────────┘ └───────────┘ └──────────┘
   │               │
   ▼               ▼
┌──────────┐ ┌───────────┐
│ SLDB     │ │ KGDB      │
│ (atoms)  │ │ (grafo)   │
└──────────┘ └───────────┘
```

### Capas de datos

| Capa | Tecnología | Contenido | Rol |
|---|---|---|---|
| **SLDB** | Store indexado + Markdown | 13 átomos (identidad, reglas, facts, tools, traits) | Conocimiento semántico reutilizable |
| **KGDB** | NetworkX + SLDB export | Grafo tag-céntrico con jerarquía `conversation:steps.*` | Diagrama de conversación y relaciones |
| **SQL** | SQLite (via SQLAlchemy) | Sesión, historial, traits por usuario, reservas | Estado vivo multi-usuario |

---

## 2. KB y la doctrina semántica

La KB vive en `.sldb_e2e_donpeppe/` (carpeta canónica de atoms) + `.sldb_e2e_donpeppe/.sldb/` (store indexado).

### Principios fundamentales

1. **Una KB = un negocio**: Cada knowledge base responde a un solo negocio. No se mezclan dominios.
2. **KB es conocimiento, no estado**: Estado vivo vive en SQL. La KB solo contiene conocimiento semántico.
3. **Multi-usuario, traits categorizados**: Los traits son un catálogo de rasgos (`user:traits.*`) que aplican a múltiples usuarios.
4. **Selección por tag, no por lectura**: El compilador selecciona átomos por su tag semántico sin leer el `answer`.
5. **Tools son un tipo, no un dominio**: `atom_type:tool` identifica tools con schema JSON.

### Árbol de tags semánticos

```
self:*                       → Identidad y personalidad del agente
  self:whoami                → Quién soy, qué soy
  self:estilo                → Tono, personalidad, registro
  self:tools                 → Tools disponibles (atom_type:tool)
  self:limites               → Qué no puedo hacer

conversation:*               → Flujo y reglas de interacción
  conversation:steps.*       → Pasos del escenario (onboarding, booking)
  conversation:fallback      → Qué hacer sin contexto suficiente
  conversation:strategy      → Estrategia de interacción

domain:*                     → Conocimiento del negocio (único por KB)
  domain:catalogo            → Catálogo de productos/servicios
  domain:horarios            → Horarios de atención
  domain:reglas.*            → Reglas de negocio

user:traits.*                → Catálogo de rasgos de usuario (multi-usuario)
  user:traits.celiaco        → Cliente sin gluten
  user:traits.vegetariano    → Cliente vegetariano

source:*                     → Procedencia y metadata
  source:e2e                 → Creado en test E2E
  source:manual              → Escrito a mano
  source:reflect             → Generado por reflector (futuro)
```

### Dimensiones de selección

Cada átomo tiene dos ejes:

| Eje | Ejemplo | Propósito |
|---|---|---|
| `atom_type` | domain, rule, tool, trait | Tipo de contenido (cómo se usa) |
| Tag semántico | `domain:catalogo`, `self:whoami` | Propósito (cuándo se selecciona) |

El compilador filtra por `atom_type` para saber **qué** incluir, y lee el tag semántico para asignar **rol** en el contexto.

### Contenido KB actual (13 átomos)

| Átomo | atom_type | Tags semánticos | Propósito |
|---|---|---|---|
| `atom-donpeppe-carta` | domain | `domain:catalogo` | Catálogo de pizzas y precios |
| `atom-donpeppe-horarios` | domain | `domain:horarios` | Horarios de atención |
| `self-whoami` | domain | `self:whoami` | Identidad del agente |
| `atom-donpeppe-regla-reservas` | rule | `domain:reglas.reservas` | Reglas de reserva |
| `conversation-steps-booking` | rule | `conversation:steps.booking` | Flujo de reserva |
| `conversation-steps-onboarding` | rule | `conversation:steps.onboarding` | Onboarding |
| `conversation-strategy` | rule | `conversation:strategy` | Estrategia general |
| `conversation-fallback` | rule | `conversation:fallback` | Fallback |
| `self-estilo` | rule | `self:estilo` | Estilo de comunicación |
| `self-limites` | rule | `self:limites` | Límites del agente |
| `atom-donpeppe-tool-reserva` | tool | `self:tools`, `conversation:steps.booking` | Schema JSON de `crear_reserva` |
| `atom-trait-sin-gluten` | trait | `user:traits.celiaco` | Trait celiaco |
| `atom-trait-vegetariano` | trait | `user:traits.vegetariano` | Trait vegetariano |

---

## 3. Componentes

### 3.1 SLDBReader (`kb_agent/ontologizador/sldb_reader.py`)

Lee documentos SLDB usando la API real de la librería `sldb` (`iter_search_records`, `search_records`).

```python
reader = SLDBReader(kb_root=Path(".sldb_e2e_donpeppe"), store_name=".sldb")

# Búsqueda semántica por tag
reader.find("domain:catalogo")          # → list[dict] con id, body, tags, path
reader.find("atom_type:domain")         # → todos los domain
reader.find("self:whoami")              # → un resultado

# Documento individual por id
reader.get_doc("atom-donpeppe-carta")   # → dict con todos los campos resueltos
```

### 3.2 KGDBReader (`kb_agent/ontologizador/kgdb_reader.py`)

Navega el grafo tag-céntrico generado desde SLDB. El grafo se construye automáticamente con `sldb_semantic_export_to_snapshot()`.

```python
reader = KGDBReader.from_sldb(".sldb_e2e_donpeppe/.sldb")

# Navegación tag-céntrica (diagrama de conversación)
reader.steps_under("conversation:steps")      # → ["booking", "onboarding"]
reader.docs_for_tag("conversation:steps.booking")  # → ["conversation-steps-booking", ...]
reader.has_tag("self:whoami")                  # → True

# Navegación genérica (networkx)
reader.find_nodes_by_type("semantic_tag")      # → todos los nodos tag
reader.get_neighborhood(tag_node, depth=1)     # → vecindario de un tag
```

### 3.3 ContextCompiler (`kb_agent/ontologizador/compiler.py`)

Produce un `CompiledDocument` con todo el contexto necesario para responder un turno.

```python
compiler = ContextCompiler(reader=sldb_reader, kgdb=kgdb_reader, identity_session=sql_session)
doc = compiler.compile(question="qué pizzas hay?", user_id=123)
```

**Selección (doctrina nueva)**:
- Todos los `atom_type:domain` → `domain_facts` (incluye `self:whoami`)
- Todos los `atom_type:rule` → `rules` (incluye `self:*` y `conversation:*`)
- Todos los `atom_type:tool` → `tools` (con schema JSON parseado)
- `user:traits.*` → `user_traits` resueltos contra SQL

**Enriquecimiento KGDB**:
- Lee `flow_node` desde `SessionState` si existe
- Deriva `flow_node` desde `conversation:steps.*`
- Expone `allowed_transitions` (steps hermanos)
- Resuelve `grounding_atoms` (documentos que groundean el step)

No se filtra por `scenario` — una KB = un negocio, todos los átomos son del negocio.

### 3.4 GeminiConversador (`kb_agent/orchestrator.py`)

Llama a Gemini real via Vertex AI para generar respuestas en lenguaje natural.

```python
conversador = GeminiConversador(genai.Client())
respuesta = conversador.draft_nl(compiled_dict)
```

Usa `domain_facts` + `rules` como grounding. Si hay traits, adapta la respuesta.

### 3.5 RouterStateMachine (`kb_chat_ui/state_machine.py`)

Máquina de estados que decide si responder en NL, ejecutar una tool, o hacer fallback.

```
idle → evaluating_context → drafting_response → idle
                          → drafting_response → waiting_tool → drafting_response → idle
                          → breakpoint_miss
```

### 3.6 Orchestrator (`kb_agent/orchestrator.py`)

Orquesta el ciclo completo de un turno:
1. Resuelve usuario y carga `SessionState`
2. Crea `ContextCompiler` + define `compile_context` closure
3. Crea `RouterStateMachine` con el compilador + conversador
4. Ejecuta el turno vía `router.handle_user_message()`
5. Si hay tool call: ejecuta y retoma
6. Persiste `SessionState` (flow_node persistido) + `ChatHistory`
7. Corre Perfilador async (extrae traits con Gemini)
8. Arma contexto atómico (`_build_turn_context`) para la UI
9. Devuelve respuesta enriquecida

### 3.7 Perfilador async

Extrae traits del usuario de forma asíncrona usando `TraitExtractor` + `GeminiTraitMapper`, y los persiste en `UserTraits` (SQL).

---

## 4. Flujo de un turno

### 4.1 Secuencia completa

```
Usuario: "¿qué pizzas tienen?"
  │
  ▼
FastAPI POST /api/chat
  │
  ▼
Orchestrator.handle_turn(external_id="ui:abc", message="¿qué pizzas tienen?")
  │
  ├─ 1) Carga usuario (Users) desde SQL
  ├─ 2) Carga SessionState (incluye flow_node) desde SQL
  ├─ 3) Crea ContextCompiler(reader, kgdb, identity_session)
  │
  ├─ 4) RouterStateMachine.handle_user_message()
  │     ├─ compile_context(question, user_id)
  │     │     ├─ ContextCompiler.compile()
  │     │     │   ├─ Resuelve scenario → "catalogo"
  │     │     │   ├─ _find_atoms("domain")  → [atom-donpeppe-carta, horarios, self-whoami]
  │     │     │   ├─ _find_atoms("rule")    → [regla-reservas, conversation.*, self.*]
  │     │     │   ├─ _find_tools()          → [crear_reserva]
  │     │     │   ├─ _load_user_traits()    → [] (o traits de SQL)
  │     │     │   └─ _augment_from_kgdb()
  │     │     │       ├─ steps_under("conversation:steps")
  │     │     │       ├─ flow_node ← onboarding (desde SQL o primer step)
  │     │     │       └─ grounding_atoms ← docs_for_tag(flow_node)
  │     │     └─ CompiledDocument.to_dict()
  │     │
  │     ├─ Evaluación: draft_conversador_response() decide
  │     │   ├─ ¿función call? → tool
  │     │   ├─ ¿sin contexto? → fallback
  │     │   └─ NL → GeminiConversador.draft_nl(compiled)
  │     │
  │     └─ RouterTurnResult {compiled_context, response, state_trace}
  │
  ├─ 5) [Si tool call] execute_tool() → system_turn
  │     └─ router.handle_tool_result() → segunda respuesta
  │
  ├─ 6) Persistir SessionState:
  │     ├─ active_domain = "pizzeria"
  │     ├─ flow_node = "conversation:steps.onboarding"  ← se guarda en SQL
  │     └─ allowed_transitions = ["conversation:steps.booking"]
  │
  ├─ 7) Persistir ChatHistory (scrubbeado)
  ├─ 8) Commit SQL
  ├─ 9) Perfilador async: extrae traits desde el mensaje
  │
  ├─ 10) _build_turn_context(compiled)
  │      ├─ Enrrique cada atom con title, tags, role semántico desde SLDB
  │      ├─ Marca grounds_step si el atom groundea el flow_node actual
  │      └─ Incluye flow_node, allowed_transitions
  │
  └─ 11) Retorna dict con {kind, reply, context, flow_node, state_trace, ...}
  │
  ▼
FastAPI adapta a formato UI
  │
  ▼
Cliente recibe turn con context.items, flow_node, etc.
```

### 4.2 Segundo turno (con flow_node persistido)

```
Usuario: "para el viernes a las 20, 4 personas"
  │
  ▼
Orchestrator.handle_turn()
  ├─ Carga SessionState → flow_node = "conversation:steps.onboarding"
  ├─ compile_context(current_step="conversation:steps.onboarding")
  │     └─ _augment_from_kgdb()
  │         ├─ steps_under("conversation:steps")
  │         ├─ current_step = "onboarding" (viene de SQL)
  │         └─ grounding = docs_for_tag("onboarding")
  │
  └─ Conversador responde: "Perfecto, ¿a nombre de quién hago la reserva?"
      (sigue en onboarding, porque el step no avanza explícitamente)
```

---

## 5. ContextCompiler y CompiledDocument

### 5.1 CompiledDocument

```python
@dataclass
class CompiledDocument:
    scenario: str                    # Etiqueta informativa del negocio (NO es filtro)
    question: str                    # Pregunta del usuario
    user_traits: list[str]           # Traits del usuario desde SQL
    domain_facts: list[dict]         # [{id, body}, ...] todos los atom_type:domain
    rules: list[dict]                # [{id, body}, ...] todos los atom_type:rule
    tools: list[dict]                # [{name, parameters}, ...] tools con schema JSON
    grounding_atoms: list[str]       # Ids de átomos que groundean el step actual
    flow_node: str | None            # Step actual del diagrama de conversación
    allowed_transitions: list[str]   # Steps hermanos (a dónde se puede ir)
    missing_slots: list[str]         # Slots faltantes (para captura progresiva)
    system_turn: dict | None         # Resultado de tool call
    is_empty: bool                   # True si no hay facts ni rules
```

### 5.2 Llamada interna

```python
compiler.compile(question, user_id, scenario=None, trigger="user", session_state)
```

- `session_state` se usa para leer `flow_node` (paso actual persistido en SQL)
- `scenario` es informativo (unused como filtro de selección)

---

## 6. Diagrama de conversación (KGDB)

### 6.1 Estructura real del grafo

El grafo se genera automáticamente desde SLDB via `sldb_semantic_export_to_snapshot()` y produce nodos con prefijos:

```
Nodos tag:
  sldb://semantic_tag/conversation:steps
  sldb://semantic_tag/conversation:steps.booking
  sldb://semantic_tag/conversation:steps.onboarding
  sldb://semantic_tag/self:whoami
  ...

Nodos documento:
  sldb://document/conversation-steps-booking
  sldb://document/atom-donpeppe-carta
  ...

Relaciones:
  <document>  --tagged_as-->  <tag>
  <tag.hijo>  --semantic_parent-->  <tag.padre>
```

### 6.2 Diagrama de conversación: `conversation:steps.*`

```text
conversation:steps
    ├── conversation:steps.onboarding
    │       └── tagged_as: conversation-steps-onboarding (rule)
    └── conversation:steps.booking
            ├── tagged_as: conversation-steps-booking (rule)
            └── tagged_as: atom-donpeppe-tool-reserva (tool)
```

### 6.3 Navegación

```python
# Steps disponibles
steps = reader.steps_under("conversation:steps")
# → ["conversation:steps.booking", "conversation:steps.onboarding"]

# Documentos que groundean un step
docs = reader.docs_for_tag("conversation:steps.booking")
# → ["atom-donpeppe-tool-reserva", "conversation-steps-booking"]
```

### 6.4 Ciclo en el compilador

```python
_augment_from_kgbd(doc, scenario, current_step):
    steps = kgdb.steps_under("conversation:steps")
    active = current_step if current_step in steps else onboarding or steps[0]
    doc.flow_node = active
    doc.allowed_transitions = [s for s in steps if s != active]
    doc.grounding_atoms = kgdb.docs_for_tag(active)
```

---

## 7. Orquestador y ciclo de vida

### 7.1 Estados persistidos en SQL (SessionState)

| Campo | Origen | Propósito |
|---|---|---|
| `active_domain` | Orchestrator | Escenario activo (etiqueta) |
| `flow_node` | Compiler | Step actual en el diagrama de conversación |
| `flow_slots` | Compiler | Transiciones permitidas + slots faltantes |
| `current_node` | RouterStateMachine | Nodo de la máquina de estados |

### 7.2 Construcción del contexto atómico

`_build_turn_context()` enriquece los atoms del `CompiledDocument`:

1. Para cada `domain_fact` o `rule`, busca el documento completo en SLDB via `reader.get_doc(id)`
2. Deriva el **rol semántico** desde los tags:
   - `self:*` → `self.whoami`, `self.estilo`, etc.
   - `conversation:*` → `conversation.fallback`, `conversation.steps.*`, etc.
   - `domain:*` → `domain_fact`
   - Si no hay eje reconocible → `rule` (fallback por atom_type)
3. Marca `grounds_step: true` si el atom está en `grounding_atoms` del KGDB
4. Incluye `flow_node` y `allowed_transitions` en el contexto

### 7.3 Perfilador async

El perfilador corre **después** de responder. Extrae traits del mensaje del usuario usando Gemini:
- Mensaje → trait candidate desde SLDB → Gemini mapea → persiste en `UserTraits`
- Corre en un worker SQL independiente para no bloquear el turno

---

## 8. Servidor FastAPI y UI

### 8.1 Server (`kb_chat_ui/server.py`)

```bash
# Arrancar
uvicorn kb_chat_ui.server:app --reload --port 8000

# Endpoints
POST /api/chat       → corre un turno real
GET  /api/atom/{id}  → sirve un atom del store SLDB
GET  /               → sirve la UI (index.html)
GET  /api/health     → health check
```

### 8.2 Mapeo session_id

```python
session_id = req.session_id or uuid4().hex[:12]
external_id = f"ui:{session_id}"
```

- La UI envía `session_id` opcional (viene de localStorage)
- El servidor lo mapea a `external_id` estable para el orquestador
- El orquestador preserva `SessionState` por `external_id`

### 8.3 Adaptación a formato UI

`_to_ui_turn()` transforma la respuesta del orquestador al contrato que consume la UI (`turn.context`).

---

## 9. Contrato de datos UI ↔ Backend

### 9.1 Request `POST /api/chat`

```json
{
  "message": "¿qué pizzas tienen?",
  "session_id": "abc123",
  "scenario": "pizzeria"
}
```

### 9.2 Response

```json
{
  "session_id": "abc123",
  "turn": {
    "turn_id": "t1",
    "user_message": "¿qué pizzas tienen?",
    "assistant_message": "En Don Peppe tenemos...",
    "kind": "nl",
    "scenario": "pizzeria",
    "scenario_source": "argument",
    "state_trace": ["idle", "evaluating_context", "drafting_response", "idle"],
    "flow_node": "conversation:steps.onboarding",
    "allowed_transitions": ["conversation:steps.booking"],
    "traits_after": [],
    "system_turn": null,
    "context": {
      "context_id": "ctx-t1",
      "scenario": "catalogo",
      "atom_ids": ["atom-donpeppe-carta", "atom-donpeppe-horarios", ...],
      "include_tags": ["domain:catalogo", "domain:horarios", "self:whoami", ...],
      "items": [
        {
          "atom_id": "atom-donpeppe-carta",
          "title": "Carta Don Peppe",
          "role": "domain_fact",
          "score": 1.0,
          "tags": ["atom_type:domain", "domain:catalogo", "source:e2e"],
          "grounds_step": false,
          "body": "Pizzas disponibles: Margherita $8900..."
        },
        {
          "atom_id": "conversation-steps-onboarding",
          "title": "Onboarding — primer contacto",
          "role": "conversation.steps.onboarding",
          "score": 1.0,
          "tags": ["atom_type:rule", "conversation:steps.onboarding", ...],
          "grounds_step": true,
          "body": "Al iniciar la conversación..."
        }
      ],
      "tools": [{"name": "crear_reserva", "parameters": {...}}],
      "user_traits": [],
      "grounding_atoms": ["conversation-steps-onboarding"],
      "flow_node": "conversation:steps.onboarding",
      "allowed_transitions": ["conversation:steps.booking"],
      "is_empty": false
    }
  }
}
```

---

## 10. Modelos de datos

### 10.1 SLDB: AtomDoc

| Campo | Tipo | Propósito |
|---|---|---|
| `id` | str | Identificador único del átomo |
| `title` | str | Título descriptivo |
| `five_wh_one_plus` | enum | Pregunta que responde (what, why, how, etc.) |
| `answer` | str | Contenido del átomo (conocimiento) |
| `tags` | list[str] | Tags semánticos namespaced |
| `provenance` | str\|null | Fuente del conocimiento |

### 10.2 SQL: SessionState

| Campo | Tipo | Propósito |
|---|---|---|
| `user_id` | int (PK) | Usuario |
| `active_domain` | str\|null | Escenario activo |
| `flow_node` | str\|null | Step actual del diagrama de conversación |
| `flow_slots` | JSON\|null | Transiciones + slots |
| `current_node` | enum | Nodo de la máquina de estados |
| `updated_at` | datetime | Última actualización |

### 10.3 SQL: ChatHistory

| Campo | Tipo | Propósito |
|---|---|---|
| `id` | int (PK) | Auto |
| `user_id` | int (FK) | Usuario |
| `role` | str | "user" \| "assistant" |
| `content` | str | Mensaje (scrubbeado) |
| `pii_scrubbed` | bool | Siempre true |
| `created_at` | datetime | Timestamp |

### 10.4 SQL: UserTraits

| Campo | Tipo | Propósito |
|---|---|---|
| `id` | int (PK) | Auto |
| `user_id` | int (FK) | Usuario |
| `trait_id` | str | Id del trait (ej. `trait-sin-gluten`) |

---

## 11. Decisiones de diseño

### 11.1 Por qué scenario ya no filtra átomos

**Problema anterior**: `domain:pizzeria` era el escenario y el filtro. Cada nuevo escenario requería duplicar la KB.

**Decisión**: Una KB = un negocio. Todos los atoms de la KB pertenecen al negocio. El compilador trae todos los `atom_type:domain` y `atom_type:rule` sin filtrar. El tag `domain:*` describe el **contenido** del negocio, no el **escenario** activo.

**Impacto**: `scenario` sobrevive como etiqueta informativa, nunca como filtro.

### 11.2 Por qué el KGDB no tiene nodos `conversation_flow_node`

**Problema anterior**: `_augment_from_kgdb` buscaba `conversation_flow_node` que no existe en el export automático de SLDB. Siempre devolvía `flow_node: None`.

**Decisión**: El grafo generado desde SLDB es tag-céntrico. El diagrama de conversación vive en la jerarquía `conversation:steps.*`. Se agregaron métodos helper (`steps_under`, `docs_for_tag`) para navegar esa estructura real.

**Impacto**: `flow_node` ahora funciona, derivado del step actual leído de `SessionState` o del primer step disponible.

### 11.3 Por qué se usa `atom_type` como eje primario de selección

**Problema anterior**: El compilador mezclaba dos conceptos en el filtro: qué tipo de átomo (domain/rule/tool) y a qué escenario pertenece.

**Decisión**: Separar. `atom_type` para selección (qué incluir), tag semántico para rol (cómo etiquetar). El compilador selecciona por `atom_type` y el `_build_turn_context` asigna rol semántico desde los tags.

### 11.4 Por qué el avance de flow_node es implícito

No hay una máquina de estados que fuerce transiciones rígidas entre steps. El `flow_node` es una **pista contextual** que guía al conversador. El avance se da naturalmente por la conversación: si el usuario pide una reserva, el step `onboarding` tiene el conocimiento para guiar la recolección de datos. Si en el futuro se necesita avance explícito, el orquestador puede inspeccionar la intención detectada o el resultado de una tool call para actualizar `flow_node` antes de persistir.

---

## 12. Tests

| Suite | Archivo | Tests | Qué prueba |
|---|---|---|---|
| Compilador | `tests/test_context_compiler.py` | 3 | Selección por doctrina nueva (todos los domain/rule, is_empty) |
| SLDB Reader | `tests/test_sldb_reader.py` | 4 | Búsqueda semántica, get_doc, find, fetch |
| KGDB Navigation | `tests/e2e/test_kgdb_navigation.py` | 1 | Navegación tag-céntrica, neighbourhood, docs_for_tag |
| UI Backend | `tests/e2e/test_ui_backend.py` | 5 | Health, index, get_atom, turn real con contexto atómico |
| Otros (45 unit) | `tests/` | 45 | Persistencia, reflector, PII, state machine, etc. |

### Comandos

```bash
# Unitarios
python -m pytest tests/test_context_compiler.py tests/test_sldb_reader.py -q

# E2E (requiere Vertex AI)
python -m pytest tests/e2e -q

# Todo
python -m pytest -q
```