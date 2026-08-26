---
id: task-conectar-reflector-al-flujo-real
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-conectar-reflector-al-flujo-real
current_node: complete
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-conectar-reflector-al-flujo-real-execution-ready
- checklist-task-conectar-reflector-al-flujo-real-testing-ready
- checklist-task-conectar-reflector-al-flujo-real-closeout-ready
task_type: test
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-reflector-batch
- atom-domain-atom
---

# Conectar Reflector al Flujo Real

## Rationale

_Explain why this task exists or the business driver behind it._

reflector/reader y reflector/generator existen pero nunca corren; cero referencias reales

## Goal

_Describe the concrete result this task must produce._

Un job real del Reflector lee ChatHistory scrubbeado y genera un atom nuevo (proposed) en el store SLDB

## Scope

_State what is in scope and what is out of scope._

kb_agent/orchestrator.py, kb_agent/reflector/reader.py, kb_agent/reflector/generator.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._
