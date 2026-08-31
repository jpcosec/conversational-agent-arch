---
id: task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas
status: active
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas
current_node: checklist-task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas-execution-ready
history: []
references:
- desk/drawer/tasks/task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas.md
depends_on: []
pills: []
files: []
checklists:
- checklist-task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas-execution-ready
- checklist-task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas-testing-ready
- checklist-task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Concurrencia: el turn_id de la UI colisiona entre requests simultaneas

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184337-suggestion-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas.md`.

## Scope

_State what is in scope and what is out of scope._

Goal: que cada respuesta de /api/chat devuelva su propio turn_id, tambien bajo requests concurrentes de la misma sesion.
Scope: frontends/chat/app.py:239-256. El contador se incrementa al principio (counters[session_id] += 1) pero el label se RELEE del dict compartido despues de la llamada lenta al orquestador/LLM, en vez de capturar el valor propio. Repro medido: 12 threads contra la misma sesion -> las 12 respuestas devolvieron el mismo 't13' (12/12, no es fluke). Se dispara con dos pestanas (comparten localStorage.kb_chat_session), doble tap de enviar, o reintento de webhook de Twilio. Rompe el Inspector del frontend, que usa turn_id como clave (index.html:127,133,215): un click puede abrir el turno de otra respuesta. Fix: capturar my_turn = counters[session_id] justo tras incrementar y usarlo en los tres returns.
Validation: test de regresion nuevo con N threads contra la misma sesion afirmando turn_ids unicos; hoy ningun test ejerce concurrencia.

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas.md.

## Validation

_List the checks required before this task can close._

- pytest

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
