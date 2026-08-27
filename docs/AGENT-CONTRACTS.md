# Contratos de agentes: qué recibe cada uno, de dónde, y qué puede escribir

Estado: **especificación objetivo + auditoría del código actual** (2026-08-27).
Escrito a mano, no ensamblado desde atoms como `ARCHITECTURE.md`. Cuando se
estabilice, promover a atoms de `desk/` y a specs de `desk/spec2viz/`.

Este documento existe porque la documentación actual describe *cajas*
(Ontologizador, Conversador, Policy) pero no dice **qué contexto recibe cada
agente ni de qué fuente sale**. Ese contrato es lo que define el sistema.

Cada sección tiene dos partes: **Diseño** (lo que el sistema debe hacer) y
**Hoy** (lo que el código hace, con referencia a archivo:línea para que se
pueda verificar y no discutir de memoria).

---

## 0. Base del sistema

El sistema se sostiene sobre tres cosas:

1. **Documentos estructurados** leídos vía SLDB, envueltos en `knowledge`.
   Son indexables por los campos de su frontmatter y tienen **relaciones
   horizontales** entre sí. No son solo atoms: hay steps, rules, traits,
   gates, tools, style, strategy, boundary, fallback, self (11 modelos hoy).
2. **Contexto por agente**, que es **fijo** o **dinámico** según el agente
   (ver §2). Un agente con contexto fijo lo carga al arrancar y no cambia por
   turno; uno con contexto dinámico lo recibe compilado en cada turno.
3. **Cuatro agentes** con responsabilidades separadas: conversador, ruteador
   de contexto, orquestador y gate.

`knowledge` debe cumplir dos cosas o el resto no se sostiene:

- **Compilar contexto de forma determinista**: misma pregunta + mismo step +
  mismo perfil ⇒ mismo contexto.
- **Exponer herramientas de búsqueda para el LLM**, para que el ruteador pueda
  buscar los atoms que corresponden a la interacción y no depender solo de un
  filtro fijo.

---

## 1. Dónde vive cada cosa (esquema vs instancia)

No hay duplicación entre `kb_agent/models/knowledge/` y `knowledge/`: es
**esquema vs datos**, unidos por el registro del store.

| Capa | Ruta | Qué es |
|---|---|---|
| Esquema | `kb_agent/models/knowledge/*.py` | Clases Pydantic: campos, obligatoriedad, `semantics` |
| Instancias | `knowledge/atoms/*.md` | Los 71 documentos, tipificados por frontmatter (`atom_type`), no por carpeta |
| Registro | `knowledge/.sldb/core/models/*.yaml` | Une cada modelo (`model_ref`) con su índice de documentos |
| Runtime | `knowledge/.sldb/runtime/` | Secciones, DAG semántico, índice |

**Hoy — deuda:** los `path:` del registro apuntan a
`/home/jp/proyectos/_worktrees/gemini_test-kb/...`, un worktree que ya no
existe. Funciona porque SLDB resuelve por `model_ref`, pero es un residuo que
rompe en cuanto algo use `path`.

### 1.1 Mecanismos de relación entre documentos

| Mecanismo | Declarado en | Poblado | Leído por el runtime | Veredicto |
|---|---|---|---|---|
| `tags` (8 namespaces) | 71/71 | sí | **sí**, es el único que manda | funciona |
| `parent` | 71/71 | 23/71 (48 `null`) | no | jerarquía parcial, sin uso |
| `semantic_anchors` | 71/71 | **0/71** | no | declarado y vacío |
| `embedding` (768d) | 71/71 | sí | **no** | poblado y nunca leído |
| `domain_ref` | 37/71 | siempre `psp-selfix` | no | constante, no discrimina |

Namespaces de tags en uso: `system` (71), `domain` (35), `conversation` (31),
`topic` (6), `gate` (5), `self` (5), `user` (5), `channel` (1).

Toda la relación horizontal real recae en `tags`, que es un match de string.
Las relaciones semánticas (anchors, embeddings) existen como campo pero no
como comportamiento.

---

## 2. Contratos por agente

Resumen. El detalle y la auditoría van en 2.1–2.4.

| Agente | Contexto fijo (carga al arrancar) | Contexto dinámico (por turno) | Fuente del dinámico | Escribe en |
|---|---|---|---|---|
| **Conversador** | personalidad, instrucciones | documentos del ruteador, perfil del usuario, estrategia, conocimiento, **historial** | ruteador de contexto | nada (solo redacta) |
| **Ruteador de contexto** | prompt de cómo buscar | step actual, conversación, datos SQL | session_state, chat_history, SQL | nada (entrega contexto) |
| **Orquestador** | flow completo de steps | contexto del ruteador, decisión de avance | ruteador + su propia lógica | SQL vía tools; step actual |
| **Gate** | documentos gate de la KB | respuesta redactada | conversador | nada; dispara handoff / protocolo |

### 2.0 La familia del documento dice qué agente lo posee

Cada uno de los 11 modelos de knowledge declara una **familia**
(`__family__`, ver `KNOWLEDGE-MODEL.md` §3.1). Las cinco familias mapean
uno a uno sobre los contratos de esta sección:

| Familia | Documentos | Agente que la carga como **base** | Carga base |
|---|---|---|---|
| `self` | SelfDeclaration, StyleGuide, CapabilityBoundary, ToolAtom | Conversador (persona) · Orquestador (tools) | fija, al arrancar |
| `conversation` | ConversationStep, StrategyRule, FallbackRule | Orquestador (flujo completo) | fija, al arrancar |
| `domain` | DomainAtom, RuleAtom | — (no tiene base; entra solo por el ruteador) | ninguna |
| `user` | TraitAtom | Perfil (los ids vienen de SQL `user_traits`) | por usuario |
| `gate` | GateCriterion | Gate | fija, al arrancar |

Dos reglas, y hay que no mezclarlas:

1. **La familia dice quién carga el documento como línea base.** Es lo que
   cada agente tiene *antes* de que empiece el turno. Es fijo y no depende
   de lo que diga el paciente.
2. **El ruteador puede meter cualquier documento, de cualquier familia,
   al bundle del turno — si lo justifica.** La familia no restringe la
   selección dinámica; la restringe la justificación. Ejemplos:
   - el paciente dice que está ansioso → entra el `TraitAtom`
     `trait-antonia-ansioso-aplicacion` (familia `user`), con su descripción
     y sus reglas de manejo, aunque el perfil SQL todavía no tenga ese trait;
   - la pregunta toca eventos adversos → entran las `RuleAtom` de
     farmacovigilancia (familia `domain`) *y* el `ConversationStep`
     `evento_adverso` (familia `conversation`) como candidato de navegación;
   - el paciente pregunta si puede agendar → entra el `ToolAtom`
     (familia `self`) para que el orquestador lo tenga a la vista.

   La salida del ruteador no es una lista de ids: es un bundle
   `[{doc_id, motivo}]`. El motivo es parte del contrato — es lo que hace
   auditable el contexto y lo que el rastro del turno (`decisions.ruteador`)
   debe mostrar en vez de un conteo.

Hoy ningún consumidor lee `__family__` (registro en `null`, runtime por
prefijo de tag, UIs a mano); la clase `Agent` de §7 debería recibir sus
documentos **base por familia**, y el ruteador buscar **sobre las 11
colecciones** sin filtro de familia.

### 2.1 Conversador

**Diseño.** Arranca con personalidad e instrucciones fijas, **cargadas desde
la KB**, no hardcodeadas. Por turno recibe del ruteador: los documentos que
corresponden, el profiling del usuario, la estrategia dinámica y el
conocimiento. Tiene la conversación. No decide flujo, no llama tools.

**Hoy.**

- ✅ Personalidad desde la KB: `persona` se arma desde `SelfDeclaration`
  (whoami), `StyleGuide` (estilo) y `CapabilityBoundary` (límites);
  `strategy` y `fallback` desde sus atoms (`compiler.py:_extract_persona`,
  `_extract_strategy`, `_extract_fallback`). Correcto.
- ✅ Perfil: recibe `user_traits` (`compiler.py:_load_user_traits`).
- ❌ **No tiene la conversación.** Los campos completos de lo que ve
  (`ontologizador/compiled_document.py:17-32`):
  `scenario, question, user_traits, domain_facts, rules, tools,
  grounding_atoms, flow_node, allowed_transitions, missing_slots,
  system_turn, is_empty, persona, strategy, fallback_text`.
  **No hay historial.** Cada turno es ciego a los anteriores; entre turnos
  solo persisten traits y `flow_node`. Efecto observado en CLI: afirmó "te
  agendo el recordatorio" y al turno siguiente no sabía de qué se hablaba.
- ❌ "Conocimiento según el contexto" no se cumple porque el ruteador no
  selecciona (ver 2.2): recibe *todo* domain + *todo* rule.

### 2.2 Ruteador de contexto

**Diseño.** Tiene el step actual, la conversación y los datos SQL. Tiene
acceso a las **herramientas de búsqueda de knowledge** para encontrar los
documentos que corresponden a este step y a esta interacción del paciente
— **de cualquier familia** (§2.0, regla 2): domain, rules, traits, steps
vecinos, tools. Cada documento que mete al bundle va con su **motivo**.
Viene con un prompt que le indica cómo hacer esa búsqueda y cómo
justificarla. Le pasa el bundle a los otros agentes.

**Hoy — el agente no existe, pero sus herramientas sí, huérfanas.** Lo que
el runtime usa es `ContextCompiler` (`kb_agent/ontologizador/compiler.py`),
que **no es un agente**: no tiene prompt, no llama LLM, no decide. Es un
compilador fijo.

Pero el paquete `knowledge_base/` (`KnowledgeOperations`, 832 líneas,
21 tests en verde) ya implementa las operaciones por agente que este
contrato pide, y **`kb_agent` no lo importa ni una vez**:

| Operación | Para quién | Qué hace que el compilador no |
|---|---|---|
| `explore_multi(query)` | ruteador | embeddings (umbral 0.3) + fuzzy + vecinos KGDB, top-10 **con score** |
| `step_next(user_id)` | orquestador | `flow_node` de SQL → `get_next_transitions()` + `get_grounding_atoms()`. **Ojo:** esos dos devuelven `[]` porque el grafo no tiene aristas tipadas (§4.2 de KNOWLEDGE-MODEL); la fase 1.1 lee el campo del step en su lugar |
| `traits(user_id)` | ruteador / conversador | resuelve cada `trait_id` contra su `TraitAtom` (título, descripción, categoría) |
| `self_context()` | conversador | identidad + estilo + límites como base |
| `context(user_id)` | ruteador | bundle por usuario |
| `propose / promote / reflect / organize` | reflector | curación de la KB |

Es la capa que pobló los embeddings (`index embeddings`) y la única que los
lee. El runtime reimplementó una versión más pobre (carga todo, sin
grafo tipado, traits como id) y dejó ésta sin consumidor: no es legacy, es
**el destino que el runtime nunca alcanzó**. Conectarla es el camino corto
para este agente (ver §7.4).

- ❌ Selección de conocimiento (`compiler.py:73-74`):
  ```python
  domain_facts = self._find_atoms("domain")
  rules        = self._find_atoms("rule")
  ```
  y `_find_by_model` (`compiler.py:159-170`) devuelve **todos** los atoms del
  tipo, ordenados por `id`. La `question` se pasa a `compile()` pero **no
  participa de la selección**: es un campo del documento, nada más.
  Resultado medido con LLM real: **43 de 71 atoms por turno**, todos con
  `score: 1.0` — un valor hardcodeado en `orchestrator.py:378`, no una
  relevancia. Entra `atom-antonia-gamp5` (validación de software) cuando
  una paciente dice "me da miedo la aguja".
- ❌ No usa embeddings ni anchors (§1.1). El contrato del campo dice
  "se compara contra el embedding in-situ de la query"
  (`models/knowledge/index_proxies.py:55`); esa comparación no está
  implementada en ningún punto del runtime.
- ❌ No tiene la conversación (mismo hueco que 2.1).
- ❌ **Los traits entran como id, no como documento.** `_load_user_traits`
  (`compiler.py:~320`) hace `select(UserTraits.trait_id)` y el conversador
  recibe `["trait-antonia-ansioso-aplicacion"]` — el string, sin la
  descripción ni las reglas de manejo del `TraitAtom`. Y solo los traits
  que **ya están** en SQL: si el paciente dice "estoy ansioso" en este
  turno, el documento de ansiedad no entra hasta que el perfilador lo
  persista *después* del turno. Es exactamente el caso que la regla 2 de
  §2.0 exige cubrir.
- ❌ No hay herramientas de búsqueda expuestas al LLM. `SLDBReader` tiene
  `find()`, `find_fields()`, `fetch()` (`sldb_reader.py:31-53`) pero son
  internas. Las únicas tools registradas para el modelo son
  `agendar_recordatorio` y `crear_reserva` (`tools/__init__.py`).
- ⚠️ Lo que **sí** hace bien, y es el patrón a extender: el grounding por
  step. `_augment_from_kgdb` (`compiler.py:274-316`) toma el step actual y
  resuelve `grounding_atoms = kgdb.docs_for_tag(step)` — es decir, para la
  familia `conversation` **sí** selecciona por contexto (10 atoms, no 31).
  El agujero está en `domain` y `rule`.

Sobre determinismo: el compilador **es** determinista, pero de la forma
barata — determinismo por ausencia de decisión. El requisito de §0 pide
determinismo *con* selección.

### 2.3 Orquestador

**Diseño.** Tiene acceso a todo el flow de steps de conversación, pero
**solo puede avanzar por pasos** (transiciones definidas, no saltos
arbitrarios). Tiene tools para escribir en SQL y para mover la etapa de la
conversación. Decide si nos movemos de step y/o si se llama una tool.

**Hoy.** `Orchestrator` (`kb_agent/orchestrator.py`) existe, pero concentra
más de lo que el diseño le asigna, y la decisión no es un agente.

- ✅ Flow de steps real: 11 `ConversationStep`, `flow_node` persistido en
  `session_state`, `missing_slots` por step.
- ✅ Tools de escritura SQL: `agendar_recordatorio` → `recordatorios`,
  `crear_reserva` → `reservas`, ejecutadas vía `execute_tool`
  (`orchestrator.py:178`).
- ✅ **"Solo puede avanzar por pasos" — resuelto en fase 1.1** (`c82764c`).
  Cada `ConversationStep` declara sus transiciones (`## Allowed
  Transitions`: `onboarding → registro_estado`; `despedida` es terminal;
  `saludo → onboarding | registro_estado | journey_operativo |
  derivacion_medinfo`) y el compilador ahora las lee del documento.
  Antes exponía *todos* los hermanos (`allowed_transitions = [s for s in
  steps if s != active]`): 10 destinos desde cualquier step, incluido el
  terminal.

  **Corrección a lo que este documento afirmaba antes:** decía que
  `KGDBReader.get_next_transitions()` ya leía esas aristas y que faltaba
  llamarlo — un "bug de cableado de dos líneas". Es falso. Ese método existe
  pero devuelve `[]` para los 11 steps: el ingest SLDB→KGDB nunca emite
  aristas `flows_to`/`grounded_by`, sólo el grafo tag-céntrico (`tagged_as`,
  `semantic_parent`). Por lo mismo,
  `KnowledgeOperations.step_next()` (`operations.py:660`) tampoco resuelve
  transiciones, aunque su forma sea la correcta. Ver `KNOWLEDGE-MODEL.md`
  §4.2.

  Falta todavía la mitad de la regla: que el orquestador **no pueda** saltar
  fuera de esa lista (guardia `before_tool`, fase 2.4).
- ❌ La decisión es heurística, no un agente. `decide_turn`
  (`kb_agent/agent.py:109`) es una policy pura sin LLM: elige tool con
  `_select_relevant_tool` (matching contra la pregunta) y clasifica el step
  destino con `_classify_psp_intent` (**keywords**). Efecto observado: en 4
  turnos de CLI pidiendo y confirmando un recordatorio, `system_turn` fue
  `null` en todos — **la tool nunca se llamó** mientras el conversador
  afirmaba haberla agendado. En un PSP farmacéutico eso es una acción
  declarada y no ejecutada.
- ⚠️ Nombres cruzados: el código tiene un `RouterStateMachine`
  (`state_machine.py`) que **no rutea contexto** — rutea el estado del turno
  (`idle → evaluating_context → drafting_response → waiting_tool`). Es
  infraestructura del orquestador, no el ruteador de 2.2.

### 2.4 Gate

**Diseño.** Configuración **fija** de documentos de la KB que filtran la
respuesta. Al detectar un caso especial: quick handoff a humano y/o activar
protocolo.

**Hoy.** `_validate_response` (`orchestrator.py:~262-338`).

- ✅ Lee los 5 `GateCriterion` directo del reader (son invisibles al
  compilador por diseño — correcto, es contexto fijo).
- ✅ Existe un camino de rechazo: `kind = "derived"` y una respuesta
  enlatada "prefiero que un profesional del programa la revise"
  (`orchestrator.py:191-198`).
- ❌ **No usa los criterios que lee.** Lee `criterion`, `approval_condition`
  y `rejection_action` de cada atom y después decide con heurísticas de
  string hardcodeadas:
  ```python
  if "dosis" in atom_id or "dosis" in criterion:
  ```
  (`orchestrator.py:~300`). Agregar un gate atom nuevo **no cambia el
  comportamiento** salvo que su id contenga las palabras que el código ya
  conoce. La KB es decorativa para este agente.
- ❌ El "handoff" es solo un texto. No hay evento, no hay cola de revisión,
  no hay protocolo que se active, no queda registro en SQL de que el turno
  fue derivado (`gate_rejection` se agrega al dict compilado y se pierde).

---

## 3. Perfil de usuario (SQL)

**Diseño.** Cada usuario tiene en SQL: conversaciones pasadas, traits,
eventos. Datos personales quedan externos por ahora. Para un usuario
reconocido, el perfil se carga automáticamente.

**Hoy.** Seis tablas en estrella sobre `users` (`kb_agent/models_sql/`):

```
users (id, external_id, channel, created_at)
 ├─ user_traits    (user_id, trait_id, confidence, source)         ← perfilador
 ├─ session_state  (user_id, current_node, active_domain,
 │                  flow_node, flow_slots, buffer, updated_at)      ← orquestador
 ├─ chat_history   (id, user_id, role, content, pii_scrubbed,
 │                  created_at)                                     ← orquestador
 ├─ reservas       (user_id, fecha, hora, personas, nombre)         ← tool
 └─ recordatorios  (user_id, dia, hora, nombre)                     ← tool
```

- ✅ Traits: se cargan automáticamente para usuario reconocido.
- ✅ PII: `scrub()` antes de persistir, `pii_scrubbed=True`.
- ❌ **Conversaciones pasadas: se guardan pero no se cargan.** `chat_history`
  persiste `role + content`, y ningún agente lo lee en el turno (2.1).
- ❌ **No hay concepto de sesión/conversación.** `chat_history` no tiene
  `session_id`; es una lista plana de mensajes por usuario. No se puede
  distinguir una conversación de otra. (`/api/profiles` inventa
  `session_id = "hist-<id>"`, el id de *una fila*, por eso la UI muestra un
  ítem por mensaje.)
- ❌ **No hay eventos.** No existe tabla de eventos ni de turnos. El rastro
  de auditoría (atoms compilados, `flow_node`, `state_trace`, decisión del
  gate) se produce en cada turno y **no se persiste**: solo vive en la
  respuesta HTTP. Reabrir una conversación en la UI da `0 atoms`.
- ⚠️ Las dos junturas SQL↔KB son strings sin integridad:
  `user_traits.trait_id` → atom `trait-*`, y `session_state.flow_node` →
  tag `conversation:steps.*`. Renombrar un atom deja filas colgando y nada
  lo detecta.
- ⚠️ No hay migraciones (ni alembic ni equivalente). `create_all()` crea
  tablas nuevas pero no altera existentes: una DB creada antes de
  `flow_node` revienta en el primer turno (`OperationalError: no such
  column`). Pasó con `runs/local-chat.sqlite`; se parchó a mano.

---

## 4. Enrolamiento

**Diseño.** Los usuarios ya vienen inscritos. Si uno no lo está, se lo
enrola preguntando teléfono, mail y nombre, y se lo deriva a un doctor.

**Hoy — no existe.** Un `external_id` desconocido se crea al vuelo
(`orchestrator.py:111`, `channel_from_external_id`) y la conversación sigue
como si estuviera inscrito. No hay paso de enrolamiento, no hay derivación,
no hay distinción entre inscrito y desconocido.

---

## 5. Correspondencia de nombres (diseño ↔ código)

Parte de la confusión documental viene de que los nombres no coinciden.

| Diseño | Código | Nota |
|---|---|---|
| Conversador | `GeminiConversador` | coincide |
| Ruteador de contexto | `ContextCompiler` ("ontologizador") | no es agente; no rutea |
| Orquestador | `Orchestrator` + `decide_turn` + `RouterStateMachine` | repartido en 3 piezas |
| Gate | `_validate_response` ("policy gate") | método privado del orquestador |
| — | `RouterStateMachine` | **no** es el ruteador de contexto |
| Perfilador | `TraitExtractor` | post-turno, async; fuera de los 4 agentes |
| Reflector | `ReflectorBatch` | offline; genera atoms desde `chat_history` |
| herramientas de knowledge por agente | `knowledge_base.KnowledgeOperations` | existe, testeado, **sin consumidor** en el runtime |

---

## 6. Mapa de brechas, por impacto

0. **`knowledge_base` está huérfano del runtime.** Las herramientas por
   agente existen y están testeadas (§2.2), pero `kb_agent` no las importa.
   Cablearlas por hooks (§7.4) cierra de golpe parte de 1, 2 y 4 sin
   escribir retrieval nuevo. Es la acción con mejor relación
   efecto/esfuerzo de esta lista.
1. **No hay ruteador de contexto.** El conversador recibe 60 % de la KB en
   cada turno, sin selección por pregunta. Es la brecha que hace el
   comportamiento impredecible y el coste creciente (cada atom nuevo de
   dominio entra a todos los turnos de todos los usuarios). La búsqueda
   con score ya existe en `knowledge_base.explore_multi`; falta el agente
   que la use y justifique.
2. **Los agentes no tienen la conversación.** Sin historial no hay
   coherencia entre turnos, y las tools se "confirman" sin ejecutarse.
3. **El gate no usa la KB.** Heurísticas hardcodeadas sobre ids; el handoff
   es un texto sin efecto.
4. **Las transiciones de step no están restringidas.** Cualquier step es
   alcanzable desde cualquier otro.
5. **No se persiste el rastro de turno** (atoms, step, gate). Auditar un
   turno pasado es imposible por esquema, no por UI.
6. **No hay sesión en `chat_history`** ni tabla de eventos.
7. **No hay enrolamiento.**
8. **Sin migraciones**: cada cambio de modelo rompe DBs existentes.
9. Relaciones semánticas muertas: `semantic_anchors` vacío, `embedding` sin
   lector, `parent` a medias.
10. Deuda de registro: `path:` del store apunta a un worktree inexistente.

Las brechas 5, 6 y 8 se resuelven con el mismo cambio (una tabla de turnos
con `session_id` + una migración). Las brechas 1, 2 y 9 se resuelven juntas
(el ruteador con embeddings + historial).

---

## 7. Una sola clase `Agent` para los cuatro

Hoy cada agente está implementado distinto: el conversador es una clase que
llama a `google-genai` con un prompt armado a mano (`llm.py:113`), el gate
es un método privado del orquestador con heurísticas, `decide_turn` es una
función pura con keywords, y el ruteador no existe. Cuatro formas para cuatro
cosas que son **la misma cosa**: un contexto, un prompt base, un conjunto de
tools, una salida.

### 7.1 Qué hay en el SDK

`google-adk 2.3.0` está instalado (no se usa) y su `LlmAgent` es exactamente
esa abstracción. Campos relevantes, verificados contra el paquete:

| Campo ADK | Cubre |
|---|---|
| `instruction` | prompt base del agente |
| `static_instruction` | contexto **fijo** (se cachea; no cambia por turno) |
| `tools` | `FunctionTool`, `AgentTool` (un agente como tool de otro) |
| `include_contents` | si recibe el historial de la conversación o no |
| `output_schema` | salida estructurada (Pydantic) |
| `before_model_callback` / `after_model_callback` | interceptar entrada/salida del modelo |
| `sub_agents`, `disallow_transfer_to_peers` | composición y restricción de transferencias |

`google-genai` (el cliente que ya usa el código) cubre lo mismo a bajo nivel
vía `GenerateContentConfig(system_instruction=..., tools=[...])`, sin el
runner.

### 7.2 Los cuatro agentes sobre la misma clase

| | Conversador | Ruteador de contexto | Orquestador | Gate |
|---|---|---|---|---|
| **Contexto fijo** | persona + estilo + límites (KB) | prompt de cómo buscar | flow completo de steps (KB) | los 5 `GateCriterion` (KB) |
| **Contexto dinámico** | documentos del ruteador, perfil, estrategia | step actual, perfil, datos SQL | contexto del ruteador | respuesta redactada |
| **Historial** | sí | sí | sí | no (solo la respuesta) |
| **Tools** | ninguna | búsqueda en KB (`find`, `find_fields`, `fetch`) | mover step, escribir SQL (`agendar_recordatorio`, `crear_reserva`) | handoff, activar protocolo |
| **Salida** | texto | bundle `[{doc_id, motivo}]` + estrategia | decisión: `{step_target, tool_call \| none}` | `{approved, reasons, action}` |
| **Determinista** | no | sí (mismo input ⇒ mismos ids) | sí | sí |

Dos observaciones que salen de la tabla:

- **El gate es un `after_model_callback` del conversador**, no un agente
  aparte con turno propio: recibe la respuesta, la valida contra sus
  documentos fijos, y o la deja pasar o la reemplaza por el handoff. Eso lo
  hace más barato y elimina un round-trip.
- **El ruteador y el orquestador tienen salida estructurada**, no texto.
  Deben declarar `output_schema`. Hoy `decide_turn` ya devuelve un dict con
  esa forma — la diferencia es que lo calcula con keywords en vez de con un
  modelo que tenga el contexto.

### 7.3 Recomendación

**Definir una clase abstracta propia, delgada, con los mismos nombres de
campo que ADK, implementada sobre `google-genai`.** No adoptar el runner de
ADK todavía.

Por qué no ADK entero ahora:

- ADK trae su propio `Runner` y `SessionService` que quieren ser dueños del
  estado de sesión. Eso colisiona con `RouterStateMachine`, `session_state`
  en SQL y el event bus, que ya existen y funcionan. Migrar el runtime
  entero es otro proyecto.
- Ya muestra churn: `pytest.ini` silencia `BaseAgentConfig is deprecated`.

Por qué sí los nombres de ADK:

- Si los campos se llaman `instruction`, `static_instruction`, `tools`,
  `include_contents`, `output_schema`, pasar a `LlmAgent` más adelante es
  un cambio de import, no un rediseño.
- Y obliga a que **el contexto fijo sea declarado**, no armado a mano en un
  prompt string como hoy.

Contrato mínimo de la clase:

```python
class Agent(Protocol):
    name: str
    instruction: str                  # prompt base
    static_instruction: str           # contexto fijo, cargado desde KB al arrancar
    tools: list[FunctionTool]
    include_contents: bool            # recibe historial
    output_schema: type[BaseModel] | None

    def run(self, dynamic_context: Context, history: list[Turn]) -> Output: ...
```

Lo que **no** cambia: el `Protocol` `Conversador.draft_nl(compiled) -> str`
que usan los tests (`tests/support/fakes.py:FakeConversador`) se mantiene
como adaptador sobre el `Agent` conversador, así la suite offline sigue
corriendo sin LLM.

Orden sugerido de migración, por brecha que cierra (§6):

1. Clase `Agent` + conversador sobre ella (sin cambio de comportamiento;
   es el caso de prueba de la abstracción).
2. Ruteador de contexto como `Agent` con tools de búsqueda en KB → cierra
   la brecha 1.
3. Gate como `after_model_callback` leyendo sus criterios de verdad → cierra
   la brecha 3.
4. Orquestador como `Agent` con `output_schema` de decisión → cierra 4 y el
   bug de tools declaradas y no ejecutadas.

### 7.4 Hooks: cómo se conecta knowledge a los agentes

ADK expone pre/post hooks en `LlmAgent`, y son el mecanismo natural para
enchufar `knowledge_base` sin reescribir el orquestador. Firmas verificadas
en `google-adk 2.3.0` (todas aceptan también una **lista** de callbacks,
que se encadenan):

| Hook | Firma | Puede |
|---|---|---|
| `before_model_callback` | `(ctx, llm_request) → LlmResponse \| None` | mutar el request (inyectar contexto) o cortocircuitar devolviendo una respuesta |
| `after_model_callback` | `(ctx, llm_response) → LlmResponse \| None` | reemplazar la respuesta |
| `before_tool_callback` | `(tool, args, ctx) → dict \| None` | vetar o reescribir los args de una tool |
| `after_tool_callback` | `(tool, args, ctx, result) → dict \| None` | reescribir el resultado; persistir |
| `before/after_agent_callback` | `(ctx) → Content \| None` | envolver el turno entero |

Sobre los cuatro agentes:

| Hook | Agente | Implementación |
|---|---|---|
| `before_model` | **Ruteador de contexto** | llama a `knowledge_base`: `self_context()` (base), `step_next(user)` (step + transiciones tipadas + grounding), `traits(user)` (documentos, no ids), `explore_multi(pregunta)` (candidatos con score); arma el bundle `[{doc_id, motivo}]` y lo inyecta en `llm_request`. El motivo va al rastro del turno. |
| `after_model` | **Gate** | valida `llm_response` contra los `GateCriterion` (contexto fijo, leídos de verdad); si rechaza, devuelve el handoff como `LlmResponse` y registra `gate_rejection`. |
| `before_tool` | **Orquestador** (guardia) | para la tool `move_step`: veta si el destino no está en las `allowed_transitions` del step activo (las que el compilador ya lee del documento desde la fase 1.1). Ahí se cumple "solo puede avanzar por pasos". |
| `after_tool` | **Orquestador** (persistencia) | escribe `session_state` / `recordatorios` / `reservas` y el rastro de la tool. Ahí se elimina "te agendé" sin tool. |

Esto cambia la recomendación de §7.3 en un punto: los hooks son la razón
más fuerte a favor de `LlmAgent` de ADK. Si se mantiene la clase propia,
tiene que exponer **estos mismos cuatro hooks con estas firmas** —
son la interfaz por la que knowledge entra y sale de cada agente, y el
motivo de que `knowledge_base` no necesite conocer al orquestador.

---

## 8. Cómo se verificó

Todo lo marcado "Hoy" se comprobó contra el código en `dev @ 800ebe4`, con
el orquestador real (Gemini vía Vertex, no el fake de tests):

- Conteo de atoms por turno: `POST /api/chat` con "me da miedo la aguja" →
  `len(context.items) == 43`, `Counter(score) == {1.0: 43}`.
- Campos de frontmatter y relaciones: parseo de los 71 `knowledge/atoms/*.md`.
- Tool no ejecutada: `printf 'hola\nquiero agendar un recordatorio...\nsi,
  confirmalo\n' | python -m kb_agent.cli` → `system_turn: null` ×4.
- Tablas y columnas: `PRAGMA table_info` sobre `runs/local-chat.sqlite`.
- Rutas del registro: `head knowledge/.sldb/core/models/DomainAtom.yaml`.
