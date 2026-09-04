---
id: task-vista-leads-con-cola-de-visitas-por-confirmar
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-vista-leads-con-cola-de-visitas-por-confirmar
current_node: checklist-task-vista-leads-con-cola-de-visitas-por-confirmar-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-vista-leads-con-cola-de-visitas-por-confirmar-execution-ready
- checklist-task-vista-leads-con-cola-de-visitas-por-confirmar-testing-ready
- checklist-task-vista-leads-con-cola-de-visitas-por-confirmar-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Vista Leads con cola de visitas por confirmar

## Rationale

_Explain why this task exists or the business driver behind it._

Mientras no exista la tool n8n el equipo comercial confirma las visitas a mano y no tiene donde ver que leads dejaron preferencia y datos de contacto.

## Goal

_Describe the concrete result this task must produce._

Reemplazar /users por una vista Leads: lista de conversaciones con estado de negocio (nuevo, calificado, con preferencia de visita, datos completos), ficha del lead y cola 'visitas por confirmar' con dia/bloque, modalidad, email y telefono; click abre la conversacion.

## Scope

_State what is in scope and what is out of scope._

frontends/profiling -> frontends/leads, endpoint /api/leads en frontends/chat/app.py derivado de users, user_traits, session_state.flow_slots, chat_history y turns. Sin cambios en el runtime.

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration -q
- python -m pytest tests/ui -q

## Done When

_Name the observable condition that makes the task complete._

Con el sqlite de produccion de Vitali, /leads lista los leads reales con su estado y la cola muestra los que llegaron a datos_contacto o cierre; tests/ui verdes.
