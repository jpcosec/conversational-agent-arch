---
id: task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid
status: deferred
summary: ''
tags:
- workspace:desk
- artifact:task
- source:inbox
routine: ''
current_node: ''
history: []
references: []
depends_on: []
pills: []
files: []
checklists: []
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# El turn_id en vivo (tN) no coincide con el persistido (uuid)

ID: task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184450-suggestion-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid.md`.

## Scope

Goal: un turno, un identificador, se mire en vivo o al reabrir la conversacion.
Scope: en vivo la UI muestra 'tN' del contador de frontends/chat/app.py:239-256, pero /api/history devuelve el turn_id persistido en la tabla turns (uuid4().hex[:12], kb_agent/orchestrator.py:507). Mismo turno, dos identificadores distintos segun el camino. El frontend usa turn_id como clave del Inspector (frontends/chat/index.html:127,133,215), asi que cualquier logica que cruce vivo e historico no matchea. Confirmado por lectura de codigo; no verifique el efecto visual en la UI. Conviene resolverlo junto con la colision de turn_id, es el mismo contador.
Validation: test que manda un turno, lo lee por /api/history y afirma que el turn_id es el mismo que devolvio /api/chat.

## Source

- `desk/inbox/20260827-184450-suggestion-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid.md`

## Done When

- The message is resolved, answered, or promoted into active work.
