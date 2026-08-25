---
id: task-conectar-maquina-de-estados-al-orquestador
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-conectar-maquina-de-estados-al-orquestador
current_node: checklist-task-conectar-maquina-de-estados-al-orquestador-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-conectar-maquina-de-estados-al-orquestador-execution-ready
- checklist-task-conectar-maquina-de-estados-al-orquestador-testing-ready
- checklist-task-conectar-maquina-de-estados-al-orquestador-closeout-ready
task_type: test
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-api-gateway-y-state-router
- atom-turno-de-sistema-system-turn
---

# Conectar Maquina de Estados al Orquestador

## Rationale

_Explain why this task exists or the business driver behind it._

RouterStateMachine existe con tests pero el orquestador la ignora; el turno no pasa por nodos reales

## Goal

_Describe the concrete result this task must produce._

El orquestador enruta cada turno por RouterStateMachine real (idle->evaluating_context->drafting_response/waiting_tool->idle)

## Scope

_State what is in scope and what is out of scope._

kb_agent/orchestrator.py, kb_chat_ui/state_machine.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._

TEST E2E TRAZA-DE-NODOS: correr un turno real y assertar que state_trace == [idle, evaluating_context, drafting_response, idle] leido de la SM real; y en un tool-call, que la traza incluye waiting_tool. Evidencia: runs/e2e/state-trace.json con la secuencia real de nodos.
