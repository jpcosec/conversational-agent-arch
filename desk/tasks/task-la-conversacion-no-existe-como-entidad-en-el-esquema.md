---
id: task-la-conversacion-no-existe-como-entidad-en-el-esquema
status: ready_for_testing
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-la-conversacion-no-existe-como-entidad-en-el-esquema
current_node: checklist-task-la-conversacion-no-existe-como-entidad-en-el-esquema-closeout-ready
history:
- operator-task-la-conversacion-no-existe-como-entidad-en-el-esquema-activate
- operator-task-la-conversacion-no-existe-como-entidad-en-el-esquema-ready-for-testing
references:
- desk/drawer/tasks/task-la-conversacion-no-existe-como-entidad-en-el-esquema.md
depends_on: []
pills: []
files: []
checklists:
- checklist-task-la-conversacion-no-existe-como-entidad-en-el-esquema-execution-ready
- checklist-task-la-conversacion-no-existe-como-entidad-en-el-esquema-testing-ready
- checklist-task-la-conversacion-no-existe-como-entidad-en-el-esquema-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
closeout_evidence_verified: false
pill_graduation_verified: true
---

# La conversacion no existe como entidad en el esquema

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184449-suggestion-la-conversacion-no-existe-como-entidad-en-el-esquema.md`.

## Scope

_State what is in scope and what is out of scope._

MODELO DECIDIDO por el owner - Usuario tiene traits, eventos y una LISTA de conversaciones. Conversacion es una lista de turnos. Turno es del usuario o de nuestro lado. Si es de nuestro lado puede ser override (humano) o agente. Si es agente, el turno debe guardar el trail completo del sistema (contexto compilado, decisiones, gate, tool calls) para poder auditar de donde salio la respuesta. Scope - modelar la entidad Conversation con FK desde turnos y chat_history; tipar el turno (user / override / agent); persistir el trail del agente por turno; criterio de cierre de conversacion definido en config; migracion alembic; el historial que va al prompt no debe cruzar el limite de la conversacion. Superficies - kb_agent/models_sql/, kb_agent/orchestrator.py, kb_agent/knowledge/compiler.py (o el modulo de historial vigente), frontends/chat/app.py (_group_conversations), alembic/.

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-la-conversacion-no-existe-como-entidad-en-el-esquema.md.

## Validation

_List the checks required before this task can close._

- pytest

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
