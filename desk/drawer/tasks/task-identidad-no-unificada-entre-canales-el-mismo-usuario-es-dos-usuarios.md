---
id: task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios
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

# Identidad no unificada entre canales: el mismo usuario es dos usuarios

ID: task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184449-suggestion-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios.md`.

## Scope

Goal: reconocer a una persona como un solo usuario aunque escriba por WhatsApp y por la UI web.
Scope: kb_agent/models_sql/identity.py:14-31 -- users.external_id es UNIQUE y es la unica clave de identidad; ensure_user (kb_agent/orchestrator.py:170-176) y _external_id (frontends/chat/app.py:83-85) construyen 'whatsapp:+56...' vs 'ui:<session_id>' vs 'web-anon-*' vs 'wa-*'. No hay merge de identidad entre canales: la misma persona genera filas Users distintas, cada una con su propio SessionState y su propio historial, asi que el agente no la reconoce al cambiar de canal. Gap genérico (aplica a cualquier KB/negocio), derivado de lectura de codigo; todavia sin evidencia empirica de duplicacion real (la DB de vitali tiene 1 solo usuario hoy). Depende de la decision de la entidad conversacion.
Validation: test que enrola un usuario por un canal y lo reconoce por el otro, con un solo Users y su historial completo.

## Source

- `desk/inbox/20260827-184449-suggestion-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios.md`

## Done When

- The message is resolved, answered, or promoted into active work.
