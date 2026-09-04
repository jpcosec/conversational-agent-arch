---
id: task-tools-funcionales-de-vitali-registrar-lead-y-crear-visita-sobre-sql
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-tools-funcionales-de-vitali-registrar-lead-y-crear-visita-sobre-sql
current_node: checklist-task-tools-funcionales-de-vitali-registrar-lead-y-crear-visita-sobre-sql-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-tools-funcionales-de-vitali-registrar-lead-y-crear-visita-sobre-sql-execution-ready
- checklist-task-tools-funcionales-de-vitali-registrar-lead-y-crear-visita-sobre-sql-testing-ready
- checklist-task-tools-funcionales-de-vitali-registrar-lead-y-crear-visita-sobre-sql-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Tools funcionales de Vitali: registrar_lead y crear_visita sobre SQL

## Rationale

_Explain why this task exists or the business driver behind it._

Vitali corre en Modal sin tools: el agente recoge datos y promete confirmacion pero no persiste el lead ni la visita. El equipo comercial no tiene registro estructurado.

## Goal

_Describe the concrete result this task must produce._

Dos tablas SQL simples (leads, visitas) y dos tools con semantica de negocio (registrar_lead upsert parcial, crear_visita crea el evento en estado solicitada y deja el contacto), cableadas en project.vitali.yaml y en la KB como ToolAtom y steps.

## Scope

_State what is in scope and what is out of scope._

kb_agent/models_sql (leads, visitas) + migracion alembic; kb_agent/tools/leads.py y visitas.py; ToolAtoms y steps de knowledge_vitali via sldb; orquestador expone slots capturados al decidir y conserva flow_target en tool_call; /api/leads lee visitas; tests unit e integration offline.

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration -q

## Done When

_Name the observable condition that makes the task complete._

Un turno con datos completos ejecuta crear_visita, persiste lead y visita, avanza a cierre, el rastro no expone PII en claro, suite offline en verde.
