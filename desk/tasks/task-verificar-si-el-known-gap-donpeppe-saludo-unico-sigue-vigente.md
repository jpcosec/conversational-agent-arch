---
id: task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente
status: active
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente
current_node: checklist-task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente-execution-ready
history: []
references:
- tests/e2e/simulation/scenarios.py
- tests/e2e/simulation/test_simulated_conversations.py
depends_on: []
pills: []
files: []
checklists:
- checklist-task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente-execution-ready
- checklist-task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente-testing-ready
- checklist-task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Verificar si el known_gap donpeppe_saludo_unico sigue vigente

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Correr la capa e2e (smoke + simulaciones con juez) sobre el runtime post-batch (20eb34b + 16f39fa) y emitir veredicto del known_gap donpeppe_saludo_unico - si la entidad Conversation lo arreglo, retirar el xfail estricto de tests/e2e/simulation/scenarios.py; si sigue vigente, documentar por que y dejarlo. Esta corrida es ademas la validacion integrada de la fase runtime-vitali.

## Scope

_State what is in scope and what is out of scope._

Superficie - tests/e2e/** y credenciales Vertex (.env). No tocar runtime ni KBs; Don Peppe se recrea, se verifica el mecanismo, no se arreglan sus atoms.

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente.md.

## Validation

_List the checks required before this task can close._

- set -a; source .env; set +a; python -m pytest tests/e2e

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
