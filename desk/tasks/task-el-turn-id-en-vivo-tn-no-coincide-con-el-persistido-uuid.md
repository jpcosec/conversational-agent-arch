---
id: task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid
status: active
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid
current_node: checklist-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-execution-ready
history: []
references:
- desk/drawer/tasks/task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid.md
depends_on: []
pills: []
files: []
checklists:
- checklist-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-execution-ready
- checklist-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-testing-ready
- checklist-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# El turn_id en vivo (tN) no coincide con el persistido (uuid)

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184450-suggestion-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid.md`.

## Scope

_State what is in scope and what is out of scope._

Goal: un turno, un identificador, se mire en vivo o al reabrir la conversacion.
Scope: en vivo la UI muestra 'tN' del contador de frontends/chat/app.py:239-256, pero /api/history devuelve el turn_id persistido en la tabla turns (uuid4().hex[:12], kb_agent/orchestrator.py:507). Mismo turno, dos identificadores distintos segun el camino. El frontend usa turn_id como clave del Inspector (frontends/chat/index.html:127,133,215), asi que cualquier logica que cruce vivo e historico no matchea. Confirmado por lectura de codigo; no verifique el efecto visual en la UI. Conviene resolverlo junto con la colision de turn_id, es el mismo contador.
Validation: test que manda un turno, lo lee por /api/history y afirma que el turn_id es el mismo que devolvio /api/chat.

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid.md.

## Validation

_List the checks required before this task can close._

- pytest

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
