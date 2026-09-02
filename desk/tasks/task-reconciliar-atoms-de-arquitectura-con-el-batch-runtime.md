---
id: task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime
current_node: checklist-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-execution-ready
- checklist-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-testing-ready
- checklist-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Reconciliar atoms de arquitectura con el batch runtime

## Rationale

_Explain why this task exists or the business driver behind it._

El batch 20eb34b+16f39fa cambio verdades de arquitectura que los atoms aun no reflejan; los docs se materializan desde atoms.

## Goal

_Describe the concrete result this task must produce._

Actualizar atom-concepto-turno-extendido (turn_id uuid unico), atom-persistencia-sql (Conversation + TurnKind + identity_key phone), atom-orquestador-hub (_resolve_conversation, carreras ensure_user), atom-perfilador-asincrono (pre-filtro top-k + ingestion form + precedencia form sobre perfilador), atom-sldb-knowledge-base (audit embeddings) y renombrar/reescribir atom-ontologizador-context-compiler a knowledge; despues rematerializar docs.

## Scope

_State what is in scope and what is out of scope._

Solo desk/atoms y docs materializados; cero cambios de runtime; no tocar knowledge/ ni knowledge_vitali/.

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- python desk/bundles/materialize.py --check
- sldb stores check --store .sldb

## Done When

_Name the observable condition that makes the task complete._

python desk/bundles/materialize.py --check sin drift y atoms sin menciones al paquete viejo.
