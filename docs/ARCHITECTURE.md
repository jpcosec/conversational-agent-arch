<!-- generado desde desk/bundles/bundle-arquitectura.md — no editar a mano; python desk/bundles/materialize.py -->
# Arquitectura del Sistema

Esta documentación está ensamblada a partir de los Átomos Semánticos del proyecto, garantizando que el diseño arquitectónico mantenga cero-drift con el código real.

> **Catálogo Visual Spec2Viz**: `desk/spec2viz/build/architecture.html`

## El Motor Conversacional Síncrono (Runtime)
### Canales de Entrada
Múltiples interfaces de conexión que convergen en el Orquestador. Incluyen el endpoint principal FastAPI (`POST /api/chat`), el webhook de WhatsApp/SMS de Twilio, y el intérprete local interactivo CLI. Todo canal expone un `external_id`.

### Orquestador (Hub Central)
Punto de entrada unificado (`Orchestrator.handle_turn`). Instancia la sesión SQL, inicializa el RouterStateMachine, delega la decisión a la policy pura, ejecuta las tool calls locales, delega la redacción al Conversador, persiste el historial purgado en SQL, y dispara asíncronamente al Perfilador a través del Event Bus.

### PII Scrubber
Capa de interceptación de privacidad. El Orquestador lo invoca para enmascarar (scrub) todo contenido antes de persistirlo en el historial SQL (`ChatHistory`) y antes de publicarlo en el EventBus, asegurando aislamiento absoluto de datos personales.

### Router State Machine
Máquina de estados técnica (`RouterStateMachine`) con 6 nodos (IDLE, BUFFERING, EVALUATING_CONTEXT, DRAFTING_RESPONSE, WAITING_TOOL, BREAKPOINT_MISS). Rutea la petición hacia el Ontologizador y pausa la ejecución síncrona en `WAITING_TOOL` mientras el Orquestador ejecuta una herramienta.

### Ontologizador (Context Compiler)
Motor de compilación determinista. Lee TODA la base de conocimiento tipada (los 10 modelos) desde SLDB, y extrae el nodo actual del grafo de ConversationStep (desde KGDB) para ensamblar el `CompiledDocument` que representa el estado exacto y los hechos relevantes para el turno.

### Ruteador de contexto como agente
`RouterAgent` (kb_agent/agents/router.py, commit f4fcf50) es el cuarto agente LLM del diseño (Conversador, Ruteador, Orquestador, Gate), construido sobre `kb_agent.agents.base.Agent` con rol `AgentRole.ROUTER`. Decide QUÉ documentos de la KB entran al bundle de contexto del turno y lo justifica — salida tipada `RouterDecision` con `BundleEntry {doc_id, motivo, family?, score?}`, motivo OBLIGATORIO por documento (contrato de auditoría, visible en el rastro y el Turn Inspector). Regla de oro — cualquier documento de cualquier familia puede entrar si el motivo lo justifica; la familia es carga base, no límite de selección. Tiene tools reales sobre la instancia única de `knowledge_base.operations.KnowledgeOperations` del proceso — `explore_multi` (similitud semántica + fuzzy con score, default `tuning.router_max_results`), `explore` (navegar el grafo) y `show` (leer un documento antes de decidir). Su `static_instruction` (`render_router_instruction`) es doctrina del sistema, no de la KB, con el encuadre de negocio como lead-in opcional (`AgentFraming` rol `router`). Dos garantías que no dependen del modelo — `apply_security_floor` (función pura) fuerza las `RuleAtom` con tag `conversation:security` siempre, y cada `doc_id` devuelto se valida contra el reader (alucinaciones descartadas). Sin RouterAgent inyectado o si falla, `ContextCompiler._build_bundle` sigue como fallback determinista (fail-open, igual que el gate); `decisions.ruteador.source` dice cuál de los dos produjo el bundle.

### Policy Pura (decide_turn)
Función de evaluación pura (`decide_turn`) sin estado ni I/O. Analiza el contexto compilado y determina estrictamente la acción a seguir devolviendo un `kind`: `tool_call` (si hay intención y parámetros válidos), `fallback` (si falta grounding o el contexto está vacío), o `nl` (lenguaje natural).

### Tool Handlers y Registry
Mecanismo de ejecución de acciones. Las tools son funciones locales de Python (`crear_reserva`, `agendar_recordatorio`) mapeadas en el `project.config.yaml`. Cuando la policy decide ejecutarlas, el Orquestador llama al handler, el cual típicamente muta estado relacional (tablas SQL de negocio).

### Agente Conversador
Motor generativo de lenguaje natural (`GeminiConversador`). Recibe el contexto validado (y el resultado de una tool si la hubo) y redacta la respuesta final usando el LLM externo. No alucina ni toma decisiones de flujo; obedece la identidad, estilo y límites provistos por el Ontologizador.

### Policy gate como agente separado con rama KB propia
El policy gate (etapa 5 PSP, compuerta regulatoria final) es un agente separado del orquestador con rama KB propia — `GateAgent` en kb_agent/agents/gate.py, sobre `kb_agent.agents.base.Agent` con rol `AgentRole.GATE`, `include_contents=False` y salida tipada `GateVerdict {approved, reasons, action, criterion_ids}`. Interviene DESPUÉS del draft del Conversador y ANTES de emitir al paciente (`Orchestrator._policy_gate`) — juzga la respuesta redactada contra los `GateCriterion` de la KB (familia `gate`, campos `criterion`, `approval_condition`, `rejection_action`), renderizados una vez en `static_instruction` por `render_gate_criteria` con el encuadre de negocio que llega de un `AgentFraming` de rol `gate` (knowledge/atoms/agent-antonia-gate.md); agregar un criterio a la KB cambia el juez sin tocar código (test de gobernanza en tests/unit/test_gate_agent.py). El veredicto es `approved` true sólo si TODOS los criterios se cumplen, con `action` `pass` | `handoff` (derivar la revisión a un humano con el borrador y el motivo) | `protocol` (aplicar un protocolo específico, p.ej. farmacovigilancia) y los `criterion_ids` violados. La única parte no gobernada por la KB es el pre-filtro determinista `response_claims_completed_action` (criterio sintético `gate-integridad-accion-no-ejecutada`) que rechaza respuestas que afirman una acción sin tool ejecutada en el turno ni en la sesión. Sin criterios en la KB o si el LLM falla, el gate aprueba (fail-open). El orquestador (decide_turn) sigue sin KB propia — su lógica es determinista y testeable.

### Encuadre de agentes desde la KB (AgentFraming)
Porque una KB = un negocio y el código no puede hardcodear el dominio. Cada agente LLM arma su prompt en dos capas — la doctrina (mecánica fija del runtime — familias, regla de oro, formato de salida) vive en las funciones `render_*` de `kb_agent/agents/` (`render_gate_criteria`, `render_router_instruction`, `render_orchestrator_flow`) y se mantiene business-neutral; el encuadre (quién es este agente EN ESTE negocio, más ejemplos de dominio) vive en la KB como documento tipado `AgentFraming` (kb_agent/models/knowledge/agent_framing.py, familia `agent`, campos `role`, `framing`, `examples`). Los roles válidos son el enum `AgentRole` de kb_agent/agents/base.py (`conversador` | `router` | `orchestrator` | `gate`), único punto de verdad de qué agentes existen. El Orquestador carga el encuadre por rol en `Orchestrator._load_agent_framing(role)` y lo inyecta como lead-in al `render_*` correspondiente; sin `AgentFraming` para un rol, el agente cae a un encuadre genérico neutro. Ejemplos en la KB de Antonia — knowledge/atoms/agent-antonia-gate.md (gate regulatorio de farmacovigilancia) y agent-antonia-router.md (ejemplos clínicos del ruteador). Detalle en docs/CONFIGURATION.md.

## Procesos Offline y Asíncronos
### InProcess Event Bus
Canal de mensajería in-memory que desacopla el cierre del turno síncrono del perfilado asíncrono. El Orquestador publica el turno aquí (`publish_turn_closed`), momento en el cual se aplica el enmascaramiento de PII antes de encolarlo.

### Perfilador Asincrono
Background worker (`TraitExtractor`) que consume eventos de turno cerrado desde el EventBus. Usa el LLM para inferir características del usuario contra los `TraitAtom` candidatos y hace un upsert (SQL `UserTraits`). Opera fuera del tiempo de respuesta del usuario.

### Reflector Batch
Job offline (`ReflectorAtomGenerator`) disparado por cron. Lee el `ChatHistory` ya scrubbeado de SQL, detecta patrones que se repiten >= 5 veces, e infiere nuevos átomos (`domain` o `rule`). Escribe directamente en SLDB usando `sldb docs create` e inyecta el tag de estado `proposed`.

## Capas de Datos y Conocimiento
### Configuración del Negocio
Archivo `project.config.yaml`. Separa el código duro del dominio del negocio. Configura dinámicamente la identidad visible del bot (name, slug), la ruta al store SLDB (`kb_root`), el modelo LLM subyacente y el mapeo de los handlers de tools permitidos.

### SQL: Identidad y Estado
Capa de persistencia relacional transaccional (vía SQLAlchemy). Almacena los `Users`, la máquina de estados persistente (`SessionState`), el `ChatHistory` (ya scrubbeado de PII), los mapeos relacionales de `UserTraits`, y las tablas de negocio como Reservas.

### SLDB: Base de Conocimiento
Store de documentos semánticos. Hospeda los 10 modelos tipados del negocio, organizados en 4 familias (self, domain, conversation, user). Permite el intercambio de átomos para transformar o re-propocionar al agente conversacional.

### KGDB: Grafo de Flujo
Capa de base de datos de grafo en memoria (NetworkX persistido). Indexa las relaciones semánticas entre los nodos de `ConversationStep` (ej. `flows_to`, `grounded_by`), permitiendo al Ontologizador trazar la ruta de la conversación de forma programática.

## Frontends
### Dashboard
Vista `/dashboard` servida por `create_app` (frontends/chat/app.py) desde `frontends/dashboard/index.html`. Es un mock estático transcrito del diseño de referencia `docs/dashboard-reference.png` — KPIs, series y listas son sintéticos y la página lo declara con el chip "Datos de ejemplo" (`data-testid="dashboard-mock-chip"`). Está enlazada en la topbar de todas las vistas (`nav-dashboard`, etiqueta `nav_labels.dashboard`) y sólo consulta `/api/config` (marca, kb_label, labels de nav) y `/api/health` (estado); no lee métricas del runtime.

### Modo demo
Modo opt-in del runtime que sirve las 4 vistas sin orquestador ni LLM. Se activa con `DEMO_MODE=1` y lo resuelve `ProjectConfig.demo_mode` (kb_agent/project_config.py) — nunca se enciende en modo test (`resolved_mode != "test"`) ni se setea en producción. Con el flag activo, `create_app` (frontends/chat/app.py) no exige Orchestrator y todos los `/api/*` responden datos prefabricados de `frontends/chat/demo_data.py` (config, atoms, flow, usuarios, perfiles); el chat usa `DemoStateMachineConversador`, una máquina de estados determinista (saludo -> consulta -> obtencion_datos -> tool_call) que imita al Conversador. Sobre las 4 vistas corre `frontends/shared/demo-tour.js`, un único recorrido guiado con cuadros que apuntan a elementos por `data-testid`, navega solo de vista en vista y guarda el progreso en localStorage (`demo-tour-idx`, `demo-tour-done`). Lo verifica tests/ui/test_demo_e2e.py (Playwright, marker `ui`, sin credenciales).
