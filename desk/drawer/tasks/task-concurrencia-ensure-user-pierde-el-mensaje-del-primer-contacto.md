# Concurrencia: ensure_user pierde el mensaje del primer contacto

ID: task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184448-suggestion-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto.md`.

## Scope

Goal: que dos requests simultaneas de un usuario nuevo no se pisen ni descarten turnos.
Scope: kb_agent/orchestrator.py:170-176 (ensure_user) y :714-719 (_load_or_create_session_state). Ambos hacen SELECT-then-INSERT sin lock ni upsert. Repro medido: 8 requests concurrentes con el mismo session_id NUEVO -> 7 de 8 explotan con sqlite3.IntegrityError (UNIQUE constraint failed: users.external_id y session_state.user_id); solo 1/8 procesa el mensaje, el resto se pierde y el cliente ve un 500. No duplica el usuario: DESCARTA el turno. Mismo disparador que la colision de turn_id (dos pestanas, doble tap, reintento de webhook). Fix: capturar IntegrityError, session.rollback() y re-SELECT, o INSERT ... ON CONFLICT DO NOTHING.
Validation: test de regresion nuevo con N threads sobre un session_id nuevo afirmando 1 solo Users, 1 solo SessionState y N mensajes persistidos; hoy los 243 tests pasan sin ejercer concurrencia.

## Source

- `desk/inbox/20260827-184448-suggestion-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto.md`

## Done When

- The message is resolved, answered, or promoted into active work.
