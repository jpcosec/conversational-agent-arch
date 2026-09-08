---
id: task-mover-logica-reimplementada-a-kgdb-sldb-pron
status: active
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-mover-logica-reimplementada-a-kgdb-sldb-pron
current_node: checklist-task-mover-logica-reimplementada-a-kgdb-sldb-pron-testing-ready
history:
- operator-task-mover-logica-reimplementada-a-kgdb-sldb-pron-activate
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-mover-logica-reimplementada-a-kgdb-sldb-pron-execution-ready
- checklist-task-mover-logica-reimplementada-a-kgdb-sldb-pron-testing-ready
- checklist-task-mover-logica-reimplementada-a-kgdb-sldb-pron-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
closeout_evidence_verified: false
pill_graduation_verified: true
---

# Mover logica reimplementada a kgdb/sldb/pron

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

gemini_test deja de reimplementar diagrama de conversacion, navegacion de grafo, embeddings y escrituras al store; usa kgdb (relaciones tipadas), sldb (store) y pron (World/Store/Graph/Matcher). Lo que falte en esas libs se agrega alla.

## Scope

_State what is in scope and what is out of scope._

kb_agent/knowledge, knowledge_base/operations.py, frontends/chat/app.py, frontends/flow_editor, knowledge/.sldb (RelationDocs), tests; legos/pron y hum-ecosystem/tools/kgdb para lo que falte

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- python -m pytest tests/unit tests/integration -q; pytest en pron y kgdb

## Done When

_Name the observable condition that makes the task complete._
