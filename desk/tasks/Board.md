---
# board-xxx
id: board-001
# Affected workspace or domain
scope: desk
# List of task-xxx paths
tasks:
- desk/tasks/task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp.md
- desk/tasks/task-renombrar-kb-agent-ontologizador-a-kb-agent-knowledge.md
- desk/tasks/task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto.md
- desk/tasks/task-la-conversacion-no-existe-como-entidad-en-el-esquema.md
- desk/tasks/task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios.md
- desk/tasks/task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa.md
- desk/tasks/task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica.md
- desk/tasks/task-ingestion-declarativa-de-traits-desde-el-formulario-registro-source-form.md
- desk/tasks/task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security.md
- desk/tasks/task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente.md
- desk/tasks/task-mindmap-no-hay-escritura-de-atoms-desde-la-ui.md
# List of pill-xxx paths
pills:
- desk/contexts/pills.md
# List of ritual-xxx paths
rituals:
- desk/rituals/phase.md
- desk/rituals/execution.md
- desk/rituals/testing.md
- desk/rituals/closeout.md
# e.g., system:sldb, workspace:desk
tags:
- workspace:desk
---

# gemini_test Board

## Purpose

_Explain what this board routes and why it exists._

Enrutar el trabajo activo del repo y mantener visibles sus gates de ejecución, testing, closeout y fase.

## Notes

_Add short operational notes about the current routed set._

- Capa 1 (testing pendiente): las dos tareas ready_for_testing (PSP Antonia, rename knowledge) cierran antes de abrir capa nueva.
- Capa 2 (contrato turn_id + concurrencia): turn-id-colisiona y turn-id-vivo-vs-persistido son el mismo contrato de turn_id, ejecutarlas juntas; ensure-user es la misma zona de orchestrator.
- Capa 3 (esquema conversacion + identidad): modelo decidido por el owner (usuario -> traits, eventos, lista de conversaciones; conversacion -> lista de turnos; turno user/override/agente; turno agente guarda el trail completo). Identidad canonica por telefono, configurable.
- Capa 4 (retrieval + KB): guarda de embeddings antes o junto al pre-filtro del perfilador; grounding va como GateCriterion por KB; piso de seguridad de Vitali como RuleAtom conversation:security.
- Mindmap: read-only para Vitali; solo limpieza UX. El modo editor quedo diferido en drawer (task-modo-editor-de-atoms-en-la-ui).
- Saltada por ahora: task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools (decision del owner).

## Task Details

_Generated from the task references above._

- Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP [ready_for_testing] - La KB de Antonia (knowledge/atoms/) modela completo el flujo de atención PSP: las 4 ramas de clasificación como RuleAtom, los steps faltantes del grafo conversacional (derivación MedInfo, revisión humana, journey operativo F0, autovalidación policy gate) como ConversationStep con transiciones coherentes, los criterios regulatorios del policy gate como átomos GateCriterion de la nueva familia gate (modelo nuevo, invisible al runtime actual), y los domain atoms de soporte (MedInfo, proceso FV, journeys, titulación, molécula) que completan la ontología cerrada PSP — todo indexado en el store SLDB y verificable por conversación real contra el runtime sin ninguna modificación del código de turno (decide_turn, compiler, state_machine, orchestrator).
- Renombrar kb_agent/ontologizador a kb_agent/knowledge [ready_for_testing] - Mover el paquete a kb_agent/knowledge, actualizar imports y comentarios/docstrings Python, mantener la suite tests/unit + tests/integration igual de verde antes y después
- Concurrencia: ensure_user pierde el mensaje del primer contacto [ready_for_testing] - Triage and resolve the inbox message promoted from `desk/inbox/20260827-184448-suggestion-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto.md`.
- La conversacion no existe como entidad en el esquema [ready_for_testing] - Triage and resolve the inbox message promoted from `desk/inbox/20260827-184449-suggestion-la-conversacion-no-existe-como-entidad-en-el-esquema.md`.
- Identidad no unificada entre canales: el mismo usuario es dos usuarios [ready_for_testing] - Triage and resolve the inbox message promoted from `desk/inbox/20260827-184449-suggestion-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios.md`.
- Una KB sin embeddings falla en silencio y nadie avisa [ready_for_testing] - Triage and resolve the inbox message promoted from `desk/inbox/20260827-184451-suggestion-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa.md`.
- Vitali no tiene piso de seguridad: ningun RuleAtom conversation:security [ready_for_testing] - Triage and resolve the inbox message promoted from `desk/inbox/20260827-184452-suggestion-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security.md`.
- Verificar si el known_gap donpeppe_saludo_unico sigue vigente [active] - Triage and resolve the inbox message promoted from `desk/inbox/20260827-184454-suggestion-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente.md`.
- Mindmap: no hay escritura de atoms desde la UI [ready_for_testing] - Triage and resolve the inbox message promoted from `desk/inbox/20260827-184453-suggestion-mindmap-no-hay-escritura-de-atoms-desde-la-ui.md`.
