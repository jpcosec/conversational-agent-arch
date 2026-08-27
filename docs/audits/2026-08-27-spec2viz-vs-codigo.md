# Auditoría de Consistencia: Specs spec2viz vs Código Real

## Spec: desk/spec2viz/backend/component.agent-ecosystem.yml

### Desfases encontrados

- **"4 actores" — FALTA Policy Gate como 5to rol conceptual.**
  El spec dice "la separación de los 4 actores (Conversador, Ontologizador, Perfilador, Reflector)". En la realidad:
  - Existe un **5to rol documentado**: Policy Gate. El archivo `kb_agent/models/knowledge/gate.py` define `GateCriterion` (exportado en `__init__.py`). Hay **5 átomos gate reales** en `knowledge/` (`gate-antonia-corpus.md`, `gate-antonia-derivacion.md`, `gate-antonia-diagnostico.md`, `gate-antonia-dosis.md`, `gate-antonia-promesas.md`), todos con tag `type.knowledge.gate` en el store indexado (`knowledge/.sldb`).
  - El desk atom `atom-mapeo-cadena-de-agentes-psp-sobre-el-runtime-antonia.md` dice explícitamente: "(5) Agente regulatorio / policy gate -> NO existe; debe ser un agente separado".
  - El spec no lo refleja ni como nodo planeado (sin código runtime).
  - **Evidencia**: `knowledge/atoms/gate-*.md` (5 archivos), `kb_agent/models/knowledge/gate.py`, `knowledge/.sldb` store con 5 docs tag `type.knowledge.gate`.

- **El nodo "policy_decide_turn" debería llamarse "orquestador".**
  El spec lo etiqueta como `decide_turn (policy pura, kb_agent/agent.py)`. El desk atom `atom-mapeo-cadena-de-agentes-psp-sobre-el-runtime-antonia.md` dice: "decide_turn (kb_agent/agent.py), que debe renombrarse conceptualmente a orquestador; clasifica el tipo de turno". La función `decide_turn` es invocada por `Orchestrator.handle_turn` (en `kb_agent/orchestrator.py`), que es quien realmente gobierna el flujo. El nombre no refleja que es el orquestador.

- **No hay nodo para Policy Gate.**
  El spec no contiene ningún nodo para Policy Gate. El desk atom `atom-policy-gate-como-agente-separado-con-rama-kb-propia.md` establece que debería existir como "agente separado del orquestador" aunque "no exista el paso de código que lo invoque". Sus criterios ya existen en la KB (5 átomos gate). **Debería haber un nodo** aunque sea como "planeado/sin runtime" con nota.

- **SLDB listado incompleto.**
  El spec dice que el Ontologizador "extrae subgrafos (Traits, Rules, Tools)" del SLDB. En realidad, el compilador (`kb_agent/ontologizador/compiler.py` línea 146-155) itera `_MODEL_TYPES` con **10 tipos**: `domain, rule, tool, trait, step, self, style, boundary, strategy, fallback`. El spec omite: Domain, Step, Self, Style, Boundary, Strategy, Fallback. Y además el store knowledge/ tiene también átomos de tipo `gate` (no consumido por compiler pero presente en store).
  - **Evidencia**: `compiler.py:_MODEL_TYPES` vs spec text.

- **El spec dice "Dominios Base SLDB (core/models, core/documents)".** 
  Esto describe la estructura interna de la librería SLDB, no del proyecto. Los stores reales del proyecto están en `knowledge/.sldb` y `tests/knowledge/.sldb`. La descripción es confusa y mezcla planos de abstracción.

### Coincidencias confirmadas

- Los 4 actores como motores/agentes existen: `kb_agent/agent.py` (agent/decide_turn), `kb_agent/llm.py` (Conversador), `kb_agent/ontologizador/` (Ontologizador), `kb_agent/perfilador/` (Perfilador), `kb_agent/reflector/` (Reflector).
- Los archivos listados (agent.py, state_machine.py, orchestrator.py, llm.py, tools/__init__.py) **existen todos**.
- La capa de persistencia SQL + SLDB está correctamente representada.
- Los puertos LLM (Conversador, TraitMapper protocols) existen en `kb_agent/llm.py`.
- El registry de tools (`kb_agent/tools/__init__.py`) existe y funciona como describe.

---

## Spec: desk/spec2viz/backend/component.knowledge-ontology.yml

### Desfases encontrados

- **Solo muestra 4 tipos atómicos; existen 11 modelos.**
  El spec lista: TraitAtom, DomainAtom, RuleAtom, ToolAtom. En realidad `kb_agent/models/knowledge/__init__.py` exporta **11 modelos**: DomainAtom, RuleAtom, ToolAtom, TraitAtom, ConversationStep, SelfDeclaration, StyleGuide, CapabilityBoundary, StrategyRule, FallbackRule, **GateCriterion**. Los stores reales (`knowledge/.sldb`, `tests/knowledge/.sldb`) contienen docs con tipos: domain, rule, tool, trait, step, self, style, boundary, strategy, fallback, **gate**.
  - **Evidencia**: `__init__.py` imports + stores con `type.knowledge.*`.

- **"Dominios Base SLDB (core/models, core/documents)" es impreciso.**
  El spec dice que contiene "core/models, core/documents". Esto describe la estructura de la librería SLDB internamente. Los dominios base reales del proyecto son los workspaces `workspace.knowledge` en `knowledge/.sldb` y `tests/knowledge/.sldb`. El directorio `core/` en `.sldb/` es parte del store indexado de SLDB, no un "dominio base" de negocio.

- **No se reflejan los ejes de activación.**
  El spec no muestra los ejes de activación (`self:*`, `domain:*`, `conversation:*`, `user:*`, `source:*`, `gate:*`). En los tags reales del store `knowledge/.sldb` se ven estos namespaces: `channel`, `conversation`, `domain`, `gate`, `self`, `system`, `user`, `type.knowledge.*`, `workspace`. El spec solo muestra la relación "rige" jerárquica, ignorando el sistema de tags.

### Coincidencias confirmadas

- SQL gestiona identidad (Users, UserTraits) y SLDB almacena conocimiento semántico. ✓
- La relación N:M entre UserTraits y TraitAtom es correcta. ✓
- Separación en capas SQL / SLDB / Proyecciones es correcta. ✓

---

## Spec: desk/spec2viz/backend/state.conversation-flow.yml

### Desfases encontrados

- **El estado "interrupted" NO EXISTE en el RouterNode enum real.**
  El spec lista 7 estados: `idle, buffering, evaluating_context, drafting_response, waiting_tool, breakpoint_miss, interrupted`. El `RouterNode` enum en `kb_agent/state_machine.py` líneas 18-25 define solo 6: `IDLE, BUFFERING, EVALUATING_CONTEXT, DRAFTING_RESPONSE, WAITING_TOOL, BREAKPOINT_MISS`. **No hay `interrupted`**. No hay ninguna referencia a "interrupted" en todo `kb_agent/`. Las transiciones `idle -> interrupted` y `interrupted -> evaluating_context` del spec **no existen en el código real**.
  - **Evidencia**: `router_node_enum` en `state_machine.py` lineas 18-25, grep zero hits para "interrupted" en todo kb_agent/.

- **Faltan transiciones reales de timeout.**
  El spec no incluye las transiciones reales de timeout que sí maneja el código: `WAITING_TOOL -> DRAFTING_RESPONSE` por tool_timeout (líneas 120-124 de state_machine.py) y el debounce timeout (`BUFFERING -> EVALUATING_CONTEXT` en `process_timeouts` líneas 127-138). El spec solo muestra un timeout_buffer para el debounce.

- **El contenedor "active_turn" es una abstracción visual que no existe en el código.**
  El spec agrupa buffering/evaluating_context/drafting_response/waiting_tool/breakpoint_miss bajo "active_turn". En el código no hay ningún concepto de "active_turn" como nodo o estado compuesto. Es inflado semántico.

- **La transición `idle -> interrupted` por "inactividad_prolongada" no existe.**
  El código no implementa timeouts de inactividad prolongada desde IDLE. El spec la muestra pero no hay código real que la respalde.

### Coincidencias confirmadas

- Los estados `idle, buffering, evaluating_context, drafting_response, waiting_tool, breakpoint_miss` existen y son exactamente los del `RouterNode` enum. ✓
- La transición `idle -> buffering` por mensaje_usuario es correcta (`handle_user_message`). ✓
- `buffering -> evaluating_context` por timeout_buffer es correcta (`process_timeouts`). ✓
- `evaluating_context -> waiting_tool` por tool (function_call) es correcta (`_is_function_call`). ✓
- `waiting_tool -> drafting_response` por tool_result es correcta (`handle_tool_result`). ✓
- `evaluating_context -> drafting_response` por contexto_resuelto es correcta (flujo normal). ✓
- `evaluating_context -> breakpoint_miss` por contexto_vacío es correcta (`is_empty` check). ✓
- `drafting_response -> idle` por respuesta_enviada es correcta (fin de turno). ✓

---

## Spec: desk/spec2viz/backend/sequence.extended-turn.yml

### Desfases encontrados

- **Falta "Orquestador" como participante.**
  El spec lista 8 participantes: User_Cron, Router, Ontologizador, Policy, ToolRegistry, API_Ext, Conversador, Perfilador. No aparece **Orchestrator.handle_turn** como actor — aparece solo en el mensaje inicial "del Router". El orquestador real (`kb_agent/orchestrator.py`) es quien cablea todo el flujo. "Policy" es un nombre que no refleja que es `decide_turn` dentro del orquestador.

- **El nombre del participante "Router" es ambiguo.**
  En el spec, "Router" parece mezclar el `RouterStateMachine` y el `Orchestrator`. En el código real, `Orchestrator.handle_turn` crea un `RouterStateMachine` local y lo usa. Son dos entidades separadas. El spec las fusiona en "Router".

- **El rol de "decide_turn(compiled_context)" debería estar dentro del orquestador.**
  El spec muestra `Policy: decide_turn(compiled_context)` como un paso externo a Router. En el código real, `decide_turn` es llamado dentro del closure `draft()` que el Orchestrator pasa al RouterStateMachine (orquestador.py línea ~145). No es un participante externo separado.

- **Falta el System Turn injection como paso explícito.**
  El spec muestra que ToolRegistry devuelve datos a Router, pero no muestra explícitamente que el Router inyecta el resultado como `system_turn` en el contexto y llama a `draft_response` de nuevo (el re-draft post-tool). En realidad `handle_tool_result` en state_machine.py (líneas 197-218) reconstruye el contexto con system_turn y llama `draft_response` otra vez. El flujo debería mostrar un loop.

### Coincidencias confirmadas

- El flujo general: mensaje -> RouterStateMachine -> Ontologizador (compile_context) -> decide_turn -> Conversador/ToolRegistry es correcto. ✓
- decide_turn devuelve `tool_call|fallback|nl` — confirmado en agent.py línea 52-66. ✓
- El perfilador actúa asíncronamente post-turno (EventBus). ✓
- ToolRegistry resuelve handlers desde project.config.yaml. ✓

---

## Spec: desk/spec2viz/backend/matrix.component-turn-lifecycle.yml

### Desfases encontrados

- **El componente "DecideTurn" es en realidad el orquestador, no la policy pura.**
  El spec lo etiqueta como "DecideTurn (policy pura, agent.py)". Pero en realidad `decide_turn` es una función invocada por `Orchestrator`. El orquestador (`Orchestrator.handle_turn`) gobierna las etapas `ingest`, `decide`, `execute`, `reply`. El nombre "DecideTurn" es confuso porque el orquestador hace más que decidir (también coordina la ejecución de tools y reply).
  - **Evidencia**: `atom-mapeo-cadena-de-agentes-psp-sobre-el-runtime-antonia.md`: "que debe renombrarse conceptualmente a orquestador".

- **El componente "Runtime" como contenedor sin clase real.**
  El spec introduce un "Runtime" contenedor que no existe como clase en el código. Es una abstracción visual válida pero no corresponde a ningún objeto real.

### Coincidencias confirmadas

- La matriz de etapas (ingest, context, decide, execute, reply) para el turno síncrono es correcta. ✓
- La matriz de etapas asíncronas (listen, extract, batch, thicken) es correcta. ✓
- Orchestrator en ingest/reply, RouterStateMachine en ingest/decide/execute, Ontologizador en context, Conversador en reply, Perfilador en extract, Reflector en batch/thicken — todo correcto. ✓
- ToolRegistry en execute, SQL en varias etapas, SLDB en context/thicken — correcto. ✓

---

## Spec: desk/spec2viz/backend/activity.example-flow-scheduling.yml

### Desfases encontrados

- **Ejemplo ignora tipos de átomos existentes en el mismo store.**
  El flujo muestra: "Ontologizador: Recupera Átomos de SLDB" y luego "Contexto = [Horarios] + [Regla No-Show] + [Tool Calendar]". Esto solo cubre 3 tipos (DomainAtom, RuleAtom, ToolAtom). El store `tests/knowledge/.sldb` para don peppe contiene **10 tipos**: domain, rule, tool, trait, step, self, style, boundary, strategy, fallback. El ejemplo no menciona que también se recuperan SelfDeclaration, StyleGuide, CapabilityBoundary, StrategyRule, ConversationStep, TraitAtom, FallbackRule en un turno real.

- **No muestra la etapa de Policy Gate ni menciona su ausencia.**
  El flujo termina con "Perfilador (Async)" pero no hay ninguna mención a un gate post-draft. Para PSP esto sería crítico — la respuesta se envía sin validación regulatoria.

### Coincidencias confirmadas

- El flujo de buffering -> profile -> ontologizador -> sldb -> compile -> conversador es correcto. ✓
- El tool calling cycle (pausa -> ejecuta -> retorno -> inyecta system turn) es correcto. ✓
- Perfilador asíncrono post-respuesta es correcto. ✓

---

## Spec: desk/spec2viz/catalog.yml

### Desfases encontrados

- **Descripción "Los 4 actores (Conversador, Ontologizador, Perfilador, Reflector) y DBs"** — debería notar que existe un 5to rol conceptual (Policy Gate) y que decide_turn es el orquestador.
- **Descripción "Diagrama del flujo de la conversación, buffering y estados"** — no advierte que el estado `interrupted` mostrado en el diagrama no existe en el código real.
- **Descripción "Separación de SQL (Identidad) vs SLDB (Átomos Semánticos)"** — no menciona que el spec correspondiente solo muestra 4 de los 11 tipos atómicos reales.

### Coincidencias confirmadas

- Las descripciones generales de cada vista son funcionalmente correctas en su mayoría. ✓
- La estructura del catálogo (categorías Global, Backend, Ejemplos, Testing, AST, Frontend) es correcta. ✓

---

## Spec: desk/spec2viz/backend/ast.kb_agent.yml

### Desfases encontrados

- **Falta `kb_agent/models/knowledge/gate.py` con `GateCriterion`.**
  El AST incluye módulos para boundary, domain, fallback, index_proxies, rule, self_declaration, step, strategy, style, tool, trait — pero **NO incluye `gate`**. El archivo `kb_agent/models/knowledge/gate.py` existe (con `class GateCriterion`) y está exportado en `__init__.py`. Esto es una omisión del AST generado.
  - **Evidencia**: `grep -c 'gate' ast.kb_agent.yml` → 0 matches; `kb_agent/models/knowledge/gate.py` existe.

- **Falta `kb_agent/models_sql/recordatorios.py`.**
  El AST incluye `models_sql/reservas` y `models_sql/session` pero no `models_sql/recordatorios`. El archivo `kb_agent/models_sql/recordatorios.py` existe y es importado en `orquestador.py` línea 24 (`from kb_agent.models_sql.recordatorios import Recordatorios`).

- **Falta `kb_agent/tools/recordatorios.py`.**
  El AST solo incluye `module_tools_reservas`. El archivo `kb_agent/tools/recordatorios.py` existe pero no aparece en el AST.

### Coincidencias confirmadas

- La mayoría de los módulos y clases en el AST corresponden al código real. ✓
- Las relaciones de importación son precisas (módulo → importa → otro módulo). ✓
- Los class items (Orchestrator, RouterStateMachine, ContextCompiler, etc.) están correctamente representados. ✓

---

## Spec: desk/atoms/ (átomos de documentación)

### Desfases encontrados

- **`atom-modelos-de-conocimiento-tipados.md`: Dice "Taxonomía de 11 modelos" pero solo enumera 10.**
  El texto dice: "Taxonomía de 11 modelos StructuredNLDoc (SLDB)" pero luego enumera únicamente 10: "DomainAtom, RuleAtom, ToolAtom, TraitAtom, ConversationStep, SelfDeclaration, StyleGuide, CapabilityBoundary, StrategyRule y FallbackRule". Falta **GateCriterion** (el undécimo modelo). El modelo GateCriterion existe en `kb_agent/models/knowledge/gate.py`, está exportado en `__init__.py`, y hay 5 átomos gate en producción (`knowledge/atoms/gate-*.md`).
  - **Severidad**: Mayor — el atom documenta la taxonomía pero omite el modelo más reciente.

### Coincidencias confirmadas

- `atom-mapeo-cadena-de-agentes-psp-sobre-el-runtime-antonia.md`: No menciona "4 actores" — describe correctamente las 5 etapas PSP y reconoce que Policy Gate no existe. ✓
- `atom-policy-gate-como-agente-separado-con-rama-kb-propia.md`: Documenta correctamente el policy gate como agente separado con rama KB propia. ✓
- `atom-clasificación-de-4-ramas-del-flujo-psp.md`: Habla de 4 ramas de clasificación PSP, no de actores. Correcto. ✓
- `atom-grafo-de-steps-actual-de-antonia-y-extensiones-psp-requeridas.md`: No menciona actores. Correcto. ✓
- `atom-decisión-familia-gate-con-modelo-gatecriterion-para-el-policy-gate.md`: Documenta la decisión de crear familia `gate`. Correcto. ✓

---

## Resumen de desfases por severidad

### Bloqueantes (información errónea que lleva a decisiones incorrectas)

1. **Estado `interrupted` inexistente** — state.conversation-flow.yml muestra un estado y transiciones que NO existen en `RouterNode` enum. Si alguien diseña código dependiendo de `interrupted`, fallará.
2. **Policy Gate ausente de todos los specs** — Existe el modelo `GateCriterion`, 5 átomos gate en KB, documentación desk, pero ningún spec de spec2viz lo refleja. Invisible para quienes lean los diagramas.
3. **AST.kb_agent.yml omite `gate.py`, `recordatorios.py`, `tools/recordatorios.py`** — El AST se presenta como "generado desde el código real" pero omite 3 archivos existentes. Engañoso para quienes lo usen como fuente de verdad.

### Menores (descripciones desactualizadas, omisiones de nuevos modelos)

4. **"4 actores" debería ser "4+1 actores" o notar Policy Gate** — en 3 lugares (spec, catalog, build HTML).
5. **SLDB listado como solo Traits/Rules/Tools** — omite Domain, Step, Self, Style, Boundary, Strategy, Fallback, Gate. Son 8 tipos omitidos de los 11 que maneja el compilador.
6. **`component.knowledge-ontology.yml` solo muestra 4/11 tipos atómicos** — debería actualizarse para reflejar ConversationStep, SelfDeclaration, StyleGuide, CapabilityBoundary, StrategyRule, FallbackRule, GateCriterion.
7. **`atom-modelos-de-conocimiento-tipados.md` dice 11 modelos pero enumera 10** — falta GateCriterion en la enumeración.

### Cosméticas (nombres, redacción)

8. **`policy_decide_turn` → debería llamarse `orquestador`** — consistente con la documentación desk que dice "debe renombrarse conceptualmente a orquestador".
9. **"DecideTurn" en matrix → debería ser "Orquestador"** — por coherencia con el punto anterior.
10. **"Dominios Base SLDB (core/models, core/documents)"** — redacción imprecisa que mezcla planos de abstracción.
11. **`sequence.extended-turn.yml`: "Policy" como participante** → debería ser "Orquestador (decide_turn)" o similar.

---

## Acceptance Report

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Comprehensive audit of all 9 spec files + 3 SLDB stores + full codebase completed. Report written to /home/jp/proyectos/gemini_test/context.md"
    }
  ],
  "changedFiles": [
    "/home/jp/proyectos/gemini_test/context.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "read + grep + find + bash + python (SLDBReader, iter_search_records) across all spec files, knowledge stores, and kb_agent/ code",
      "result": "passed",
      "summary": "All spec files read. RouterNode enum, SLDB stores (3 stores: .sldb/, knowledge/.sldb, tests/knowledge/.sldb), compiler._MODEL_TYPES, desk atoms, and all referenced .py files verified."
    }
  ],
  "validationOutput": [
    "Spec 1 (agent-ecosystem): 5 desfases (4 actores→5, nombre policy_decide_turn, falta Policy Gate, SLDB list incomplete, Dominios Base impreciso)",
    "Spec 2 (knowledge-ontology): 3 desfases (4/11 tipos, Dominios Base impreciso, sin ejes activación)",
    "Spec 3 (state-conversation-flow): 4 desfases (interrupted no existe, faltan timeouts reales, active_turn abstracto, idle→interrupted irreal)",
    "Spec 4 (sequence): 4 desfases (falta Orquestador, Router ambiguo, decide_turn interno, falta loop system_turn)",
    "Spec 5 (matrix): 1 desfase (DecideTurn→Orquestador)",
    "Spec 6 (activity): 2 desfases (ignora tipos, falta gate)",
    "Spec 7 (catalog): 3 desfases (4 actores, interrupted, 4/11 tipos)",
    "Spec 8 (AST): 3 omisiones (gate.py, recordatorios.py, tools/recordatorios.py)",
    "Spec 9 (desk atoms): 1 desfase (atom-modelos-conocimiento dice 11 pero lista 10, falta GateCriterion)"
  ],
  "residualRisks": [
    "SLDB stores may have additional docs not enumerated (744 records in knowledge/.sldb, only 42 shown as typed atoms; the rest are sections/fields that may contain additional atom_type values)",
    "No exhaustive check of every transition condition in state_machine.py vs the spec — only the key ones verified"
  ],
  "noStagedFiles": true,
  "diffSummary": "New report file context.md with complete audit findings across all 9 spec categories",
  "reviewFindings": [
    "blocker: state.conversation-flow.yml shows 'interrupted' state that does not exist in RouterNode enum (state_machine.py lines 18-25)",
    "blocker: ast.kb_agent.yml omits gate.py (GateCriterion), recordatorios.py, and tools/recordatorios.py despite all existing in code",
    "blocker: No spec mentions Policy Gate/GateCriterion despite existing model class + 5 KB atoms + desk documentation",
    "minor: component.knowledge-ontology.yml shows only 4 of 11 existing atom types",
    "minor: atom-modelos-de-conocimiento-tipados.md says 11 models but lists only 10",
    "cosmetic: policy_decide_turn node should be renamed orquestador per desk documentation",
    "cosmetic: DecideTurn in matrix should be Orquestador for consistency"
  ],
  "manualNotes": "Full report written to /home/jp/proyectos/gemini_test/context.md. The most critical findings are: (1) 'interrupted' state doesn't exist in RouterNode enum, (2) AST spec missing gate.py + 2 other files, (3) Policy Gate completely absent from all visual specs despite existing model and KB atoms."
}
```