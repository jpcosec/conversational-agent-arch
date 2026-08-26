---
id: task-scrub-completo-del-assistant-y-marca-veraz
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-scrub-completo-del-assistant-y-marca-veraz
current_node: complete
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-scrub-completo-del-assistant-y-marca-veraz-execution-ready
- checklist-task-scrub-completo-del-assistant-y-marca-veraz-testing-ready
- checklist-task-scrub-completo-del-assistant-y-marca-veraz-closeout-ready
task_type: test
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-aislamiento-estricto-de-pii
---

# Scrub Completo del Assistant y Marca Veraz

## Rationale

_Explain why this task exists or the business driver behind it._

La respuesta del assistant se guarda con pii_scrubbed=True sin pasar por scrub; la marca miente

## Goal

_Describe the concrete result this task must produce._

Todo texto persistido en ChatHistory pasa por scrub() antes de marcarse pii_scrubbed=True

## Scope

_State what is in scope and what is out of scope._

kb_agent/orchestrator.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._
