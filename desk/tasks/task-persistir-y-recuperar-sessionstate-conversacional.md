---
id: task-persistir-y-recuperar-sessionstate-conversacional
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-persistir-y-recuperar-sessionstate-conversacional
current_node: complete
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-persistir-y-recuperar-sessionstate-conversacional-execution-ready
- checklist-task-persistir-y-recuperar-sessionstate-conversacional-testing-ready
- checklist-task-persistir-y-recuperar-sessionstate-conversacional-closeout-ready
task_type: test
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-sql-capa-identidad-y-estado
- atom-contexto-compilado
---

# Persistir y Recuperar SessionState Conversacional

## Rationale

_Explain why this task exists or the business driver behind it._

SessionState se importa pero nunca se lee/escribe; el scenario va hardcodeado por turno

## Goal

_Describe the concrete result this task must produce._

El orquestador escribe SessionState (current_node, active_domain) por usuario y lo recupera al iniciar cada turno

## Scope

_State what is in scope and what is out of scope._

kb_agent/orchestrator.py, kb_agent/models_sql/session.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._
