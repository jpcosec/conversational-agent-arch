---
id: task-renombrar-kb-agent-ontologizador-a-kb-agent-knowledge
status: ready_for_testing
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-renombrar-kb-agent-ontologizador-a-kb-agent-knowledge
current_node: checklist-task-renombrar-kb-agent-ontologizador-a-kb-agent-knowledge-closeout-ready
history:
- operator-task-renombrar-kb-agent-ontologizador-a-kb-agent-knowledge-activate
- operator-task-renombrar-kb-agent-ontologizador-a-kb-agent-knowledge-ready-for-testing
references:
- commit:e04e1f0
- 'suite: SKIP_LLM_TESTS=1 pytest tests/unit tests/integration -> 243 passed'
depends_on: []
pills: []
files: []
checklists:
- checklist-task-renombrar-kb-agent-ontologizador-a-kb-agent-knowledge-execution-ready
- checklist-task-renombrar-kb-agent-ontologizador-a-kb-agent-knowledge-testing-ready
- checklist-task-renombrar-kb-agent-ontologizador-a-kb-agent-knowledge-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms: []
closeout_evidence_verified: false
---

# Renombrar kb_agent/ontologizador a kb_agent/knowledge

## Rationale

_Explain why this task exists or the business driver behind it._

Owner canoniza el subsistema como knowledge y pide erradicar el nombre Ontologizador del software sin tocar docs ni otras lanes

## Goal

_Describe the concrete result this task must produce._

Mover el paquete a kb_agent/knowledge, actualizar imports y comentarios/docstrings Python, mantener la suite tests/unit + tests/integration igual de verde antes y después

## Scope

_State what is in scope and what is out of scope._

Solo kb_agent/, frontends/, tests/, scripts/, deploy/ y el desk task/board necesarios para enrutar y cerrar la tarea; no tocar source/, knowledge_vitali/README.md ni el borrado staged de scripts/build_vitali_kb.py

## Implementation Path

_Outline the expected implementation route or affected surface._

kb_agent/knowledge

## Validation

_List the checks required before this task can close._

- SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration

## Done When

_Name the observable condition that makes the task complete._

Existe kb_agent/knowledge en lugar de kb_agent/ontologizador, no quedan imports o referencias Python de ontologizador en las rutas permitidas, la suite SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration pasa antes y después, y el cambio cierra en un commit atómico deskops
