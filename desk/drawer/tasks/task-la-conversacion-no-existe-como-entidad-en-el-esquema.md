---
id: task-la-conversacion-no-existe-como-entidad-en-el-esquema
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

# La conversacion no existe como entidad en el esquema

ID: task-la-conversacion-no-existe-como-entidad-en-el-esquema
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184449-suggestion-la-conversacion-no-existe-como-entidad-en-el-esquema.md`.

## Scope

Goal: que el sistema sepa donde empieza y termina una conversacion, en vez de inferirlo por dia calendario.
Scope: es la causa estructural detras de la delimitacion de conversaciones y del historial que va al LLM. Tres sintomas del mismo hueco: (1) session_state tiene PK = user_id SOLO (kb_agent/models_sql/session.py:24) -- una fila por usuario para siempre, sin sesion activa/expirada, sin cierre, sin TTL; el flow_node/active_domain persiste indefinidamente. (2) chat_history.session_id NUNCA se setea (kb_agent/orchestrator.py:722-725 no lo pasa, aunque turns.session_id si se llena); verificado en runs/ui-chat-vitali.sqlite: chat_history con session_id=NULL y el turns del mismo turno con 'ui:47ef40ea069d'; por eso _group_conversations (frontends/chat/app.py:136-186) agrupa por DIA CALENDARIO, mezclando temas distintos del mismo dia y partiendo en dos una charla que cruza medianoche. (3) el historial que va al prompt (kb_agent/ontologizador/compiler.py:826-851) filtra solo por user_id, sin session_id ni corte temporal: history_limit=6 limita cantidad, no vigencia, asi que los ultimos 6 mensajes de toda la vida del usuario entran al prompt hayan pasado 2 minutos o 3 meses. Requiere decision de diseno antes de codear: entidad Conversation o session_id con FK, criterio de cierre (TTL por inactividad?), y migracion alembic. Nota: chat_history.session_id ya existe nullable desde la migracion 8df38d93ccd7, sin FK ni constraint.
Validation: tests/integration/test_conversation_grouping.py extendido para agrupar por sesion real y no por dia; test de que el historial del prompt no cruza el limite de conversacion.

## Source

- `desk/inbox/20260827-184449-suggestion-la-conversacion-no-existe-como-entidad-en-el-esquema.md`

## Done When

- The message is resolved, answered, or promoted into active work.
