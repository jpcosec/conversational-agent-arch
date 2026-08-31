---
id: task-mindmap-no-hay-escritura-de-atoms-desde-la-ui
status: active
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-mindmap-no-hay-escritura-de-atoms-desde-la-ui
current_node: checklist-task-mindmap-no-hay-escritura-de-atoms-desde-la-ui-execution-ready
history: []
references:
- desk/drawer/tasks/task-mindmap-no-hay-escritura-de-atoms-desde-la-ui.md
depends_on: []
pills: []
files: []
checklists:
- checklist-task-mindmap-no-hay-escritura-de-atoms-desde-la-ui-execution-ready
- checklist-task-mindmap-no-hay-escritura-de-atoms-desde-la-ui-testing-ready
- checklist-task-mindmap-no-hay-escritura-de-atoms-desde-la-ui-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Mindmap: no hay escritura de atoms desde la UI

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184453-suggestion-mindmap-no-hay-escritura-de-atoms-desde-la-ui.md`.

## Scope

_State what is in scope and what is out of scope._

DECISION del owner - para Vitali la UI queda READ-ONLY. Esta task se reduce a la limpieza UX - remover del toolbar del mindmap las mutaciones locales que prometen persistencia inexistente (borrar, +hijo, +hermano, link horizontal, hotkeys) y documentar el modo read-only en frontends/UI-GUIDE.md. El modo editor persistido queda como task diferida aparte en el drawer (task-modo-editor-de-atoms-en-la-ui).

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-mindmap-no-hay-escritura-de-atoms-desde-la-ui.md.

## Validation

_List the checks required before this task can close._

- pytest

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
