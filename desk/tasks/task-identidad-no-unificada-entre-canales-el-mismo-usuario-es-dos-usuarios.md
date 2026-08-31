---
id: task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios
status: active
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios
current_node: checklist-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-execution-ready
history: []
references:
- desk/drawer/tasks/task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios.md
depends_on: []
pills: []
files: []
checklists:
- checklist-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-execution-ready
- checklist-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-testing-ready
- checklist-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Identidad no unificada entre canales: el mismo usuario es dos usuarios

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184449-suggestion-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios.md`.

## Scope

_State what is in scope and what is out of scope._

DECISION del owner - la clave canonica de persona para este producto es el TELEFONO, y debe poder configurarse (config del proyecto, no hardcode). Scope - unificar identidad entre canales usando telefono como clave canonica; agregar setting de clave de identidad en la config (project.config.yaml / project.vitali.yaml); merge o lookup de Users por esa clave en ensure_user y _external_id; mantener external_id por canal como alias. Superficies - kb_agent/models_sql/identity.py, kb_agent/orchestrator.py (ensure_user), frontends/chat/app.py (_external_id), config. Coordinar con la task de conversacion (misma zona de esquema).

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios.md.

## Validation

_List the checks required before this task can close._

- pytest

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
