---
id: task-implementar-ontologizador-context-compiler
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-ontologizador-context-compiler
current_node: checklist-task-implementar-ontologizador-context-compiler-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-implementar-ontologizador-context-compiler-execution-ready
- checklist-task-implementar-ontologizador-context-compiler-testing-ready
- checklist-task-implementar-ontologizador-context-compiler-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-ontologizador-context-compiler
- atom-contexto-compilado
---

# Implementar Ontologizador Context Compiler

## Rationale

_Explain why this task exists or the business driver behind it._

Para aislar la extracción de conocimiento del LLM

## Goal

_Describe the concrete result this task must produce._

Motor determinista que resuelve p(Escenario, Pregunta, Perfil)

## Scope

_State what is in scope and what is out of scope._

kb_agent/ontologizador.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._

## Estrategia de Testing Asignada
- [ ] **Graph Assertions (PyTest)**: Crear un directorio `.sldb_test/` con átomos ficticios.
- [ ] Proveer un `user_id` falso y una consulta de prueba.
- [ ] Hacer `assert` estricto de que el JSON resultante contiene exactamente los IDs esperados y omite cualquier átomo irrelevante. No se debe usar LLM en este test.
