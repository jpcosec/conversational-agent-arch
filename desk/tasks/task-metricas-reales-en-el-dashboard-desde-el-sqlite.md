---
id: task-metricas-reales-en-el-dashboard-desde-el-sqlite
status: ready_for_testing
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-metricas-reales-en-el-dashboard-desde-el-sqlite
current_node: checklist-task-metricas-reales-en-el-dashboard-desde-el-sqlite-closeout-ready
history:
- operator-task-metricas-reales-en-el-dashboard-desde-el-sqlite-activate
- operator-task-metricas-reales-en-el-dashboard-desde-el-sqlite-ready-for-testing
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-metricas-reales-en-el-dashboard-desde-el-sqlite-execution-ready
- checklist-task-metricas-reales-en-el-dashboard-desde-el-sqlite-testing-ready
- checklist-task-metricas-reales-en-el-dashboard-desde-el-sqlite-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms: []
closeout_evidence_verified: false
pill_graduation_verified: true
---

# Metricas reales en el dashboard desde el sqlite

## Rationale

_Explain why this task exists or the business driver behind it._

El dashboard es un mock estatico con numeros inventados; las metricas que importan (fallback, gate, leads con contacto, latencia) hoy se sacan a mano de la base.

## Goal

_Describe the concrete result this task must produce._

Endpoint /api/metrics y dashboard con conversaciones por dia, porcentaje de turnos en fallback, porcentaje derivados por el gate, leads con datos de contacto, latencia media por turno; chip 'Datos de ejemplo' eliminado.

## Scope

_State what is in scope and what is out of scope._

frontends/dashboard/index.html, /api/metrics en frontends/chat/app.py leyendo turns, chat_history, users, user_traits. Latencia: persistir duracion del turno en turns (migracion alembic pequena) o calcularla desde created_at de chat_history.

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration -q
- python -m pytest tests/ui -q

## Done When

_Name the observable condition that makes the task complete._

/dashboard muestra numeros que coinciden con una consulta directa al sqlite; sin mock; tests/ui verdes.
