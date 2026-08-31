---
id: task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto
status: active
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto
current_node: checklist-task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto-execution-ready
history: []
references:
- desk/drawer/tasks/task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto.md
depends_on: []
pills: []
files: []
checklists:
- checklist-task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto-execution-ready
- checklist-task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto-testing-ready
- checklist-task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Concurrencia: ensure_user pierde el mensaje del primer contacto

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184448-suggestion-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto.md`.

## Scope

_State what is in scope and what is out of scope._

Goal: que dos requests simultaneas de un usuario nuevo no se pisen ni descarten turnos.
Scope: kb_agent/orchestrator.py:170-176 (ensure_user) y :714-719 (_load_or_create_session_state). Ambos hacen SELECT-then-INSERT sin lock ni upsert. Repro medido: 8 requests concurrentes con el mismo session_id NUEVO -> 7 de 8 explotan con sqlite3.IntegrityError (UNIQUE constraint failed: users.external_id y session_state.user_id); solo 1/8 procesa el mensaje, el resto se pierde y el cliente ve un 500. No duplica el usuario: DESCARTA el turno. Mismo disparador que la colision de turn_id (dos pestanas, doble tap, reintento de webhook). Fix: capturar IntegrityError, session.rollback() y re-SELECT, o INSERT ... ON CONFLICT DO NOTHING.
Validation: test de regresion nuevo con N threads sobre un session_id nuevo afirmando 1 solo Users, 1 solo SessionState y N mensajes persistidos; hoy los 243 tests pasan sin ejercer concurrencia.

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto.md.

## Validation

_List the checks required before this task can close._

- pytest

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
