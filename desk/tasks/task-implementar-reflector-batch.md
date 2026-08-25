---
id: task-implementar-reflector-batch
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-reflector-batch
current_node: checklist-task-implementar-reflector-batch-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-implementar-reflector-batch-execution-ready
- checklist-task-implementar-reflector-batch-testing-ready
- checklist-task-implementar-reflector-batch-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-reflector-batch
- atom-domain-atom
- atom-rule-atom
---

# Implementar Reflector Batch

## Rationale

_Explain why this task exists or the business driver behind it._

Para automatizar el engrosamiento de la KB funcional

## Goal

_Describe the concrete result this task must produce._

Job CRON que procesa historiales en batch a Domain/Rule atoms

## Scope

_State what is in scope and what is out of scope._

kb_agent/reflector.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._
- [ ] Conectar la lectura explícitamente a la tabla ChatHistory (ya purgada de PII) en la BD SQL.

## Estrategia de Testing Asignada
- [ ] **Simulación Batch**: Alimentar el Reflector con un lote de historiales falsos pre-procesados (sin PII).
- [ ] Ejecutar el ciclo de consolidación.
- [ ] Hacer `assert` comprobando que se escribieron físicamente nuevos archivos Markdown (nuevos `DomainAtom` o `RuleAtom`) en un directorio `.sldb_test/` de prueba.
