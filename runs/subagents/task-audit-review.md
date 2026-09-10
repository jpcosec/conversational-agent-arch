## Review
- Correct: el drawer mezcla tres tipos de ítems bien distinguibles: semillas deliberadamente vagas (`seed-*`), tasks concretas listas para ejecución (`task-ingestion-declarativa-de-traits-desde-el-formulario-registro-source-form`, `task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica`) y triage técnico ya bien acotado (`task-concurrencia-*`, `task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security`).
- Correct: ya hay avances en código/tests que vuelven obsoletas partes del drawer: el prompt NL sí inyecta historial (`kb_agent/llm.py:90-103`, `tests/unit/test_llm_prompts.py:60-68`), la UI ya agrupa conversaciones por `session_id` cuando existe (`frontends/chat/app.py:136-186`, `tests/integration/test_conversation_grouping.py:1-13, 82-89, 130-133`), y `rule-antonia-eventos-adversos` ya contiene la frase pedida (`knowledge/atoms/rule-antonia-eventos-adversos.md:791`).
- Blocker: no conviene promover tal cual las tasks que mezclan decisión de arquitectura o dato externo con implementación (`task-la-conversacion-no-existe-como-entidad-en-el-esquema`, `task-mindmap-no-hay-escritura-de-atoms-desde-la-ui`, `task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools`, `task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios`), porque hoy abrirían scope.
- Note: el repo ya tenía muchos cambios unstaged previos; no había archivos staged (`git diff --cached --name-only` vacío).

## Auditoría
| Task id | Veredicto | Razón | Solapes | Preguntas |
|---|---|---|---|---|
| `seed-dividir-current-kb-agent` | **a · mantener en drawer** | Semilla acotada pero explícitamente diferida hasta retomar spec2viz (`desk/drawer/tasks/seed-dividir-current-kb-agent.md:29-32`). | Relación temática con `seed-mas-subagentes-al-loop`; no duplicada. | — |
| `seed-mas-subagentes-al-loop` | **a · mantener en drawer** | Demasiado vaga: “agregar un par de subagentes más” y “scope por definir” (`desk/drawer/tasks/seed-mas-subagentes-al-loop.md:11-18`). | Roza `seed-dividir-current-kb-agent` por la misma dependencia a `seed-recomponer-spec2viz-y-atoms`. | — |
| `seed-profundizar-la-kb` | **a · mantener en drawer** | Semilla útil pero demasiado amplia; no hay scope operativo (`desk/drawer/tasks/seed-profundizar-la-kb.md:11-18`). | Se cruza a nivel macro con `task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools`, pero no la reemplaza. | — |
| `task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas` | **b · promover** | El bug sigue vivo: `/api/chat` incrementa el contador y luego relee `counters[session_id]` después de la llamada lenta (`frontends/chat/app.py:239-256`). La task está bien acotada y el fix propuesto coincide con el código. | **Fusionar o coordinar** con `task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid`. | — |
| `task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto` | **b · promover** | `ensure_user` y `_load_or_create_session_state` siguen haciendo SELECT→INSERT con `commit()` sin upsert/rehidratación (`kb_agent/orchestrator.py:170-176`, `kb_agent/orchestrator.py:714-719`). Es un bug operacional claro. | Relación técnica con `task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios` por tocar `Users`/`SessionState`, pero no es duplicado. | — |
| `task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid` | **b · promover** | La UI devuelve `tN` (`frontends/chat/app.py:239-256`), pero el rastro persiste `uuid4().hex[:12]` (`kb_agent/orchestrator.py:507-509`). Además el modelo `Turns` documenta que `turn_id` debiera ser el id de runtime por sesión (`kb_agent/models_sql/turns.py:16-24`). | **Merge recomendado** con `task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas`; ambas son el mismo contrato de `turn_id`. | — |
| `task-evento-adverso-el-conversador-debe-decir-que-un-profesional-del-programa-registrar-el-evento` | **a · mantener en drawer** | La capa de datos ya trae exactamente el mensaje pedido: `rule-antonia-eventos-adversos` dice “un profesional del programa registrará...” (`knowledge/atoms/rule-antonia-eventos-adversos.md:791`). La task parece desfasada respecto al estado actual; antes de promoverla como coding task conviene solo revalidar el escenario. | Vecina funcional de la simulación `antonia_evento_adverso`, pero no veo otra task duplicada. | — |
| `task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara` | **c · ambiguo / no promover aún** | El problema existe a nivel de comportamiento, pero el mecanismo no quedó cerrado: hoy el prompt solo dice “No inventes nada” (`kb_agent/llm.py:106-109`) y en `knowledge/atoms` los gate criteria visibles son de Antonia, no un criterio grounded genérico. Promoverla así mezcla policy runtime vs contenido por-KB. | Se cruza con `task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa` y con `task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica` como temas de calidad de grounding/retrieval, no como duplicado. | **¿El criterio grounded genérico debe vivir en código/runtime o cada KB debe declarar su propio GateCriterion equivalente?** |
| `task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios` | **c · ambiguo / no promover aún** | El diagnóstico técnico es correcto (`Users.external_id` único en `kb_agent/models_sql/identity.py:13-18`; `_external_id` genera `ui:<session>` en `frontends/chat/app.py:83-85`), pero la propia task admite que no hay evidencia empírica y que depende de la decisión de conversación. Falta la clave canónica de persona. | Se cruza con `task-la-conversacion-no-existe-como-entidad-en-el-esquema` y, más tangencialmente, con `task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto`. | **¿Cuál es la clave canónica de persona entre canales: teléfono, email, CRM lead id u otra?** |
| `task-ingestion-declarativa-de-traits-desde-el-formulario-registro-source-form` | **b · promover** | Está marcada como `execution-ready` (`desk/drawer/tasks/task-ingestion-declarativa-de-traits-desde-el-formulario-registro-source-form.md:8-18`), el hueco existe (no encontré `source='form'` en `kb_agent/**/*.py`) y el catálogo Vitali ya expone los trait ids objetivo (`knowledge_vitali/atoms/trait-vitali-pais-*.md`, `trait-vitali-edad-*.md`, `trait-vitali-persona-juridica.md`, `trait-vitali-para-*.md`). | Se conecta con `task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica`, pero una es ingreso declarativo y la otra ranking del perfilador. | — |
| `task-la-conversacion-no-existe-como-entidad-en-el-esquema` | **c · ambiguo / no promover aún** | Está **mezclada**: ya hubo mejora parcial en UI/consultas (`frontends/chat/app.py:136-186`, `tests/integration/test_conversation_grouping.py:1-13, 82-89, 130-133`), pero persisten los huecos estructurales: `SessionState` sigue 1:1 por `user_id` (`kb_agent/models_sql/session.py:21-31`), `chat_history.session_id` no se persiste (`kb_agent/orchestrator.py:722-725`) y el historial del prompt sigue filtrando solo por `user_id` (`kb_agent/knowledge/compiler.py:839-847`). Tal como está, mezcla plumbing inmediato con rediseño/migración. | **Split recomendado**: (1) persistir y consumir `chat_history.session_id`; (2) decidir entidad `Conversation`/TTL/migración. Se cruza con `task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid` e `task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios`. | **¿Se modela entidad `Conversation` con FK o basta persistir `session_id` + TTL? ¿Cuál es el criterio de cierre?** |
| `task-mindmap-no-hay-escritura-de-atoms-desde-la-ui` | **c · ambiguo / no promover aún** | El estado actual ya está documentado como read-only (`frontends/UI-GUIDE.md:181-185`), pero el toolbar sigue ofreciendo mutaciones locales (`frontends/taxonomy/index.html:90-95`) y hotkeys de borrado/link (`frontends/taxonomy/index.html:185`). La task mezcla una decisión de producto/arquitectura de deskops con una limpieza UX barata. | **Split recomendado**: (1) sacar acciones locales engañosas; (2) si se quiere edición persistida, abrir task aparte de arquitectura/escritura SLDB. | **¿La decisión de producto es read-only definitivo o edición persistida desde la UI?** |
| `task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica` | **b · promover** | Está marcada `execution-ready` (`desk/drawer/tasks/task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica.md:8-18`) y el gap sigue vigente: `_load_candidates()` carga todos los traits (`kb_agent/perfilador/extractor.py:73-84`) aunque ya existe infraestructura semántica reutilizable (`kb_agent/knowledge/compiler.py:315-352`). | Relación estrecha con `task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa` e `task-ingestion-declarativa-de-traits-desde-el-formulario-registro-source-form`. | — |
| `task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools` | **c · ambiguo / no promover aún** | Aunque figura `execution-ready` (`desk/drawer/tasks/task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools.md:8-18`), el scope mezcla una parte ya accionable (P5b: limpiar residuo de Calendar) con varias decisiones externas abiertas en `source/DUDAS-KB.md:21-72` (ubicaciones, precios, tipologías, catálogo de citas, TZ multi-país, segmentación). | **Split recomendado**: (1) cleanup P5b listo para ejecutar; (2) backlog de preguntas de negocio P1-P4/P6/P7; (3) vincular `task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security` como task hermana o hija. | **¿Se publican ubicaciones exactas? ¿Se permiten precios en conversación? ¿Qué catálogo de citas/TZ aplica? ¿El agente cubre solo Suite o también Broker/Franquicia?** |
| `task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa` | **b · promover** | El silencio sigue en ambos caminos: `knowledge_base/operations.py:631-633` y `kb_agent/knowledge/compiler.py:342-346` hacen `continue` sin aviso al ver embeddings nulos. No encontré guardas equivalentes en CI/tests. | Se conecta con `task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica` y con `task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security`, porque ambas dependen de retrieval sano. | — |
| `task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente` | **b · promover** | Es chica, concreta y probablemente cierre deuda rápido: el `known_gap` aún dice “sin historial” (`tests/e2e/simulation/scenarios.py:163-175`), pero el prompt ya inyecta historial (`kb_agent/llm.py:90-103`, `tests/unit/test_llm_prompts.py:60-68`). Su propia hipótesis de obsolescencia está bien fundada. | Relación vecina con `task-la-conversacion-no-existe-como-entidad-en-el-esquema`, pero no es duplicada: esta task solo pide revalidar/quitar un xfail zombie. | — |
| `task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security` | **b · promover** | El compilador espera ese piso y lo fuerza por código (`kb_agent/knowledge/compiler.py:358-366`), pero en `knowledge_vitali/atoms` no encontré ningún `conversation:security`. El gap de contenido es real y bien delimitado. | Se cruza con `task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools`, pero por criticidad conviene mantenerla visible como task separada si no se arma un épico Vitali. | — |

## Solapes y reordenamiento sugerido
- **Fusionar** `task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas` + `task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid` bajo un único frente “contrato de `turn_id`”.
- **Partir** `task-la-conversacion-no-existe-como-entidad-en-el-esquema` en “plumbing inmediato de `session_id`” vs “diseño de conversación/TTL/migración”.
- **Partir** `task-mindmap-no-hay-escritura-de-atoms-desde-la-ui` en “limpieza UX read-only” vs “edición persistida de atoms”.
- **Partir** `task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools` en “cleanup P5b” vs “preguntas de negocio”.
- **Secuenciar** `task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa` antes o junto con `task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica`, para no optimizar un camino cuyo fallo hoy es silencioso.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Se auditó cada archivo bajo desk/drawer/tasks, se contrastó con código/tests/docs reales y se escribió este informe en runs/subagents/task-audit-review.md sin tocar el resto del repo."
    }
  ],
  "changedFiles": [
    "/home/jp/proyectos/_worktrees/vitali/runs/subagents/task-audit-review.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "git status --short",
      "result": "passed",
      "summary": "Inspección del árbol; había cambios unstaged previos en el repo."
    },
    {
      "command": "git diff --cached --name-only",
      "result": "passed",
      "summary": "Sin archivos staged."
    },
    {
      "command": "python -m pytest tests/integration/test_chat_api.py -q",
      "result": "passed",
      "summary": "22 tests OK; confirma contrato actual de /api/chat con turn_id vivo tipo tN."
    },
    {
      "command": "python -m pytest tests/integration/test_conversation_grouping.py -q",
      "result": "passed",
      "summary": "3 tests OK; confirma agrupación por session_id y fallback legacy por día."
    },
    {
      "command": "python -m pytest tests/unit/test_llm_prompts.py -q",
      "result": "passed",
      "summary": "8 tests OK; confirma que el prompt NL sí inyecta historial."
    },
    {
      "command": "python -m pytest tests/unit/test_models_sql.py -q",
      "result": "passed",
      "summary": "13 tests OK; el modelo Turns sigue documentando unicidad de turn_id por sesión."
    }
  ],
  "validationOutput": [
    "tests/integration/test_chat_api.py: 22 passed",
    "tests/integration/test_conversation_grouping.py: 3 passed",
    "tests/unit/test_llm_prompts.py: 8 passed",
    "tests/unit/test_models_sql.py: 13 passed"
  ],
  "residualRisks": [
    "Las tasks dependientes de LLM real o de decisiones de negocio (evento adverso, grounding, identidad, conversación, reconstrucción KB Vitali) no quedaron resueltas por mera inspección estática.",
    "El repo ya tenía cambios locales previos; este informe no intentó normalizarlos ni revisarlos fuera del alcance del drawer audit."
  ],
  "noStagedFiles": true,
  "diffSummary": "Solo se añadió el informe de auditoría solicitado en runs/subagents/task-audit-review.md.",
  "reviewFindings": [
    "merge: task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas + task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid",
    "split: task-la-conversacion-no-existe-como-entidad-en-el-esquema",
    "split: task-mindmap-no-hay-escritura-de-atoms-desde-la-ui",
    "split: task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools",
    "stale-candidate: task-evento-adverso-el-conversador-debe-decir-que-un-profesional-del-programa-registrar-el-evento"
  ],
  "manualNotes": "No se modificó código de producto; solo se generó este reporte."
}
```