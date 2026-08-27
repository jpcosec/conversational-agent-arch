# Cómo funciona el sistema — visión general

Documento índice de la arquitectura del **KB Agent Runtime**: cómo funciona de
punta a punta y para qué sirve cada vista del catálogo (`build/architecture.html`).

> **Doctrina**: una KB = un negocio. Nada del negocio (nombres, paths, tools,
> modelo, saludos) vive en el código. Todo sale de la KB (SLDB/KGDB) o de
> `project.config.yaml`. Cambiar de negocio = cambiar ese archivo + la KB.

---

## 1. Los tres subsistemas

| Subsistema | Qué es | Dónde |
|---|---|---|
| **Runtime** | El motor conversacional: recibe un mensaje, compila contexto, decide, redacta, persiste, perfila. | `kb_agent/` |
| **Knowledge** | El conocimiento del negocio: 12 modelos tipados en SLDB (incl. `GateCriterion` y `AgentFraming`) + grafo de flujo en KGDB + CLI de gestión. | `kb_agent/models/knowledge/`, `knowledge_base/`, `knowledge/` |
| **Frontend** | 6 vistas (chat `/`, flow `/flow`, mindmap `/mindmap`, users `/users`, dashboard `/dashboard` + tour guiado) servidas por un único FastAPI app factory; `DEMO_MODE=1` sirve datos fabricados. | `frontends/` |

---

## 2. El flujo de un turno (Runtime)

Todo el turno síncrono se lee de arriba a abajo en
`kb_agent/orchestrator.py::Orchestrator.handle_turn` — es el hub que cablea las
piezas. Secuencia real:

1. **HTTP** — `frontends/chat/app.py` `POST /api/chat` → `handle_turn(external_id, message, ...)`.
2. **Identidad + sesión** — `ensure_user` (SQL `Users`), `_load_or_create_session_state` (SQL `SessionState`, arranca en `IDLE`).
3. **Router** — `RouterStateMachine.handle_user_message` → `_run_turn` → `_compile_and_draft`. Estados: `IDLE → EVALUATING_CONTEXT`.
4. **Ontologizador + Ruteador** — `ContextCompiler.compile` lee TODA la KB tipada (domain, rule, tool, trait, persona self/style/boundary, strategy, fallback) + enriquece con el paso de flujo (KGDB), y delega el **bundle justificado** en el `RouterAgent` (`kb_agent/agents/router.py`: LLM con tools `explore_multi`/`explore`/`show` sobre `KnowledgeOperations`; cualquier documento puede entrar si está justificado `[{doc_id, motivo}]`). `apply_security_floor` fuerza por código las `RuleAtom` `conversation:security`; si el agente falla, cae a `_build_bundle` determinístico. Devuelve `CompiledDocument`.
5. **Breakpoint miss** — si el contexto viene vacío (`is_empty`): `EVALUATING_CONTEXT → BREAKPOINT_MISS`. Siempre sigue a `DRAFTING_RESPONSE`.
6. **Orquestador** — `OrchestratorAgent.decide` (`kb_agent/agents/orchestrator_agent.py`) resuelve con salida tipada `kind` + `step_target`, viendo el grafo de `ConversationStep` (static_instruction), las tools declaradas y las transiciones permitidas:
   - `tool_call` → el modelo pide una tool con args válidos contra el schema del `ToolAtom`.
   - `fallback` → contexto vacío / sin rules ni domain.
   - `nl` → responder en lenguaje natural.
   `apply_transition_guard` (código, no prompt) veta cualquier `step_target` fuera de `allowed_transitions`. Si el LLM falla, `kb_agent/agent.py::decide_turn` (keywords) es el fallback determinístico.
7. **Ejecución de tool** (si `tool_call`) — el router pausa (`DRAFTING_RESPONSE → WAITING_TOOL`); el orquestador ejecuta `execute_tool(...)` (handler de `kb_agent/tools/`, declarado en `project.config.yaml`), arma el **System Turn** (JSON) y reanuda: `handle_tool_result` → `WAITING_TOOL → DRAFTING_RESPONSE`.
8. **Conversador** — `kb_agent/llm.py::GeminiConversador.draft_nl` redacta el NL desde el contexto (persona + grounding + traits + system_turn si hubo tool). Nunca alucina: sin grounding, cae al fallback.
8b. **Gate** — si `kind == nl`, `GateAgent.evaluate` (`kb_agent/agents/gate.py`) juzga la respuesta redactada contra los `GateCriterion` de la KB (`knowledge/atoms/gate-antonia-*.md`, renderizados en su static_instruction) → `GateVerdict`. Rechazo ⇒ `kind = derived` y texto de derivación; error del LLM ⇒ fail-open. El encuadre de negocio de Ruteador/Orquestador/Gate viene de la KB (`AgentFraming` por `AgentRole`, p. ej. `agent-antonia-{gate,router}.md`); el código queda neutral.
9. **Persistencia SQL** — actualiza `SessionState` (flow_node, slots), persiste `ChatHistory` (user + assistant) con `scrub()` PII y `pii_scrubbed=True`, y el rastro por turno en `Turns` (decisión del orquestador, draft, gate). `commit`. Estado vuelve a `IDLE`.
10. **Perfilador (async)** — `publish_turn_closed` → `TraitExtractor.extract` mapea el turno a `trait_ids` y hace upsert en SQL `UserTraits`. Corre fuera del camino de respuesta.

**Reflector (batch, offline)** — job cron (`kb_agent/reflector/`): lee `ChatHistory`
ya scrubbeada, detecta patrones recurrentes (≥5 turnos), y propone atoms nuevos
(`domain`/`rule`) con `status: proposed` vía `knowledge_base/operations.py::propose`
(ruteados con `derive_path`). Un humano los promueve a `active`.

---

## 3. Las capas de datos (Knowledge)

| Capa | Qué guarda | Lectura |
|---|---|---|
| **SQL** | identidad (`Users`), traits aprendidos (`UserTraits`), estado vivo (`SessionState`), historial (`ChatHistory`), reservas/recordatorios. | SQLAlchemy `kb_agent/models_sql/` |
| **SLDB** | conocimiento tipado: los 12 modelos (ver abajo). | `ontologizador/sldb_reader.py` + `knowledge_base/operations.py` (tools del Ruteador) |
| **KGDB** | grafo de flujo conversacional: `ConversationStep` + relaciones (`flows_to`, `grounded_by`, `uses_tool`, ...). | `ontologizador/kgdb_reader.py` |

**Los 12 modelos tipados** (`kb_agent/models/knowledge/`), agrupados por `__family__`:

| Familia | Modelos | Para qué |
|---|---|---|
| **self** | SelfDeclaration, StyleGuide, CapabilityBoundary, ToolAtom | quién es el bot: identidad, tono, límites, tools |
| **domain** | DomainAtom, RuleAtom | qué sabe: hechos del negocio + reglas condicionales |
| **conversation** | ConversationStep, StrategyRule, FallbackRule | cómo conversa: flujo, estrategia, fallback |
| **user** | TraitAtom | descriptores reutilizables del usuario |
| **gate** | GateCriterion | criterios con los que el Gate juzga la respuesta redactada |
| **agent** | AgentFraming | encuadre de negocio de cada agente LLM (`role` ∈ AgentRole) |

Parámetros del runtime (`max_bundle_size`, `history_limit`, `router_max_results`, `tool_timeout_ms`) viven en el bloque `tuning` de `project.config.yaml` (`ProjectConfig.tuning`); la infra de Modal en el bloque `deploy` (ver `docs/CONFIGURATION.md`).

---

## 4. Índice de vistas del catálogo (14)

Abrir `build/architecture.html`. Tres secciones. **Niveles**: `logical.*` = cómo
está pensado (fiel al cableado real) · `current-*` = cómo está escrito ·
state/sequence/matrix = cómo se comporta.

### Backend · Runtime (el motor)

| Vista | Qué muestra | Cuándo mirarla |
|---|---|---|
| **logical-agent-ecosystem** | el modelo lógico: canales → orquestador-hub → 4 agentes LLM (Ruteador, Orquestador, Conversador, Gate) con guardas por código → 3 DBs, event bus, scrubber y Gemini | **empezar aquí**: entender el sistema sin ruido de módulos |
| **current-kb-agent** | los ~45 módulos reales de `kb_agent/` (incl. `agents/`) con su jerarquía e imports | ubicar un módulo o entender la estructura del runtime |
| **state-conversation-flow** | máquina de estados del turno (6 nodos de `RouterNode`) | entender los estados y transiciones (buffering, pausa por tool) |
| **sequence-extended-turn** | el turno en orden temporal (mensaje → ruteador → orquestador → tool → conversador → gate → perfilado) | seguir el flujo paso a paso |
| **matrix-component-turn-lifecycle** | qué componente participa en cada stage del turno | ver de un vistazo quién actúa en cada etapa |
| **current-deploy** | empaquetado Modal (código + KB) que sirve el ASGI, bloque `deploy` del yaml, app/volumen dev por `MODAL_APP_NAME`, alembic, release gate y CI | entender el despliegue serverless |
| **current-tests** | la suite por capas (unit/integration/e2e/ui + support) | ubicar dónde va un test |
| **deployment-backend-frontend** | separación explícita backend vs frontend | ver la frontera de despliegue |
| **activity-simulation-harness** | usuario simulado ↔ orquestador + juez LLM | entender las pruebas agente-vs-agente |

**Las tres lentes del mismo turno**: `state` = qué estados hay · `sequence` =
en qué orden · `matrix` = quién participa en cada etapa.

### Backend · Knowledge (el conocimiento)

| Vista | Qué muestra | Cuándo mirarla |
|---|---|---|
| **current-knowledge-base** | CLI de la KB: parser (11 subcomandos) + `KnowledgeOperations` (organize/derive_path/propose/promote) | gestionar la KB desde consola |
| **matrix-agents-kb-consumption** | qué **modelo** tipado lee/produce cada agente (12 modelos × 7 agentes) | saber qué conocimiento toca cada agente |

### Frontend (las UIs)

| Vista | Qué muestra | Cuándo mirarla |
|---|---|---|
| **current-frontends** | `chat.app` como hub FastAPI + las 6 vistas + proyectores de KB + `DEMO_MODE` | entender qué sirve cada endpoint |
| **state-chat-ui** | estados de la UI de chat (idle → enviando → turno → inspector → modal) | entender la interacción del inspector |
| **matrix-ui-semantic-surface** | qué familia de datos muestra/edita cada página + de qué config depende | ver qué superficie toca qué conocimiento |

---

## 5. Cómo regenerar

```bash
# validar + renderizar un spec
spec2viz diagram validate desk/spec2viz/backend/<spec>.yml
spec2viz diagram render   desk/spec2viz/backend/<spec>.yml --renderer mermaid --out desk/spec2viz/build

# matrices (vega): render + wrap a HTML embebible
spec2viz diagram render desk/spec2viz/backend/<matrix>.yml --renderer vega --out desk/spec2viz/build
python desk/spec2viz/wrap_vega.py desk/spec2viz/build/<matrix>.vega.json desk/spec2viz/build/<matrix>.html

# catálogo HTML (build/ está gitignored: re-renderizar todos los specs antes)
spec2viz catalog build --config desk/spec2viz/catalog.yml \
  --out desk/spec2viz/build/architecture.html --base-dir desk/spec2viz --atoms-dir desk/atoms
```

> **Gotcha**: `build/` está en `.gitignore`. Los `.mmd`/`.html` NO se commitean;
> hay que regenerarlos. Si el catálogo falla por `build/` vacío, re-renderiza
> todos los specs primero.
