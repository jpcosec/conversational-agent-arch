---
id: task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara
status: active
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara
current_node: checklist-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-execution-ready
history: []
references:
- desk/drawer/tasks/task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara.md
depends_on: []
pills: []
files: []
checklists:
- checklist-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-execution-ready
- checklist-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-testing-ready
- checklist-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Grounding: el conversador afirma atributos de productos que la KB no declara

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Triage and resolve the inbox message promoted from `desk/inbox/20260827-160609-suggestion-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara.md`.

## Scope

_State what is in scope and what is out of scope._

DECISION del owner - el criterio grounded vive EN CADA KB como GateCriterion; los agentes no deben afirmar nada que no este en el contexto compilado y el gate es quien lo enforcea. Scope - definir el GateCriterion grounded por KB (partiendo por knowledge/ y knowledge_vitali/) y asegurar que el gate lo aplique; el prompt del conversador puede reforzar pero la garantia es el gate. La KB de ejemplo Don Peppe se va a recrear - arreglar el mecanismo, no el atom de pizzas.

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara.md.

## Validation

_List the checks required before this task can close._

- pytest

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
