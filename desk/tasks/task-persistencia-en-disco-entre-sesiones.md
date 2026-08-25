---
id: task-persistencia-en-disco-entre-sesiones
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-persistencia-en-disco-entre-sesiones
current_node: checklist-task-persistencia-en-disco-entre-sesiones-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-persistencia-en-disco-entre-sesiones-execution-ready
- checklist-task-persistencia-en-disco-entre-sesiones-testing-ready
- checklist-task-persistencia-en-disco-entre-sesiones-closeout-ready
task_type: test
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-sql-capa-identidad-y-estado
---

# Persistencia en Disco entre Sesiones

## Rationale

_Explain why this task exists or the business driver behind it._

DB en :memory: pierde todo al cerrar; traits/reservas/historial no sobreviven

## Goal

_Describe the concrete result this task must produce._

DB SQLite en disco; cerrar y reabrir el orquestador conserva usuarios, traits y reservas

## Scope

_State what is in scope and what is out of scope._

kb_agent/orchestrator.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._

TEST E2E CICLO-DE-VIDA: instanciar Orchestrator(db en archivo), aprender un trait + crear reserva, DESTRUIR el objeto, instanciar uno NUEVO apuntando al mismo archivo, y assertar que el trait y la reserva SIGUEN ahi. Evidencia: runs/e2e/persistence-check.json mostrando estado antes/despues del reinicio.
