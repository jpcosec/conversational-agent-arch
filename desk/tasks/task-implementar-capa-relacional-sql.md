---
id: task-implementar-capa-relacional-sql
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-capa-relacional-sql
current_node: checklist-task-implementar-capa-relacional-sql-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-implementar-capa-relacional-sql-execution-ready
- checklist-task-implementar-capa-relacional-sql-testing-ready
- checklist-task-implementar-capa-relacional-sql-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-sql-capa-identidad-y-estado
- atom-trait-atom
---

# Implementar Capa Relacional SQL

## Rationale

_Explain why this task exists or the business driver behind it._

Para aislar PII e Identidad de SLDB

## Goal

_Describe the concrete result this task must produce._

Definir SQLAlchemy/SQLModel para Users y UserTraits

## Scope

_State what is in scope and what is out of scope._

kb_agent/models_sql/

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._
- [ ] Crear tabla de SessionState para registrar el nodo activo de la máquina de estados.
- [ ] Crear tabla ChatHistory (logs de conversación).
- [ ] Implementar mecanismo robusto de limpieza de PII en ChatHistory para consumo seguro del Reflector.
