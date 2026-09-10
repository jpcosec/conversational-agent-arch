---
id: task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools
status: deferred
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools
current_node: checklist-task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools-execution-ready
- checklist-task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools-testing-ready
- checklist-task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Reconstruir KB de Vitali: dudas de contenido y residuo de tools

## Rationale

_Explain why this task exists or the business driver behind it._

El crawl del sitio y la revision del systemprompt dejaron gaps de contenido y residuo de Google Calendar que no son responsabilidad nuestra. Documentado en source/DUDAS-KB.md.

## Goal

_Describe the concrete result this task must produce._

Resolver las dudas abiertas de la KB de Vitali (source/DUDAS-KB.md) y limpiar el residuo de tools externas, dejando la KB coherente con una unica tool n8n pendiente.

## Scope

_State what is in scope and what is out of scope._

knowledge_vitali/atoms/. Insumos: source/crawl/ (sitio oficial) y source/systemprompt.md. NO modelar tools de Google Calendar/Gmail (motor externo). Unica tool nuestra: flujo n8n aun no entregado. Pendiente de negocio: P1 ubicaciones exactas, P2 precios, P3 tipologias/dimensiones, P4 catalogo de citas, P6 timezone multipais, P7 segmentacion. Accionable ya sin esperar negocio: P5b limpiar residuo de Google Calendar en rule-timezone-routing y rule-visit-modality.

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- sldb stores check --store knowledge_vitali/.sldb
- python -m knowledge_base --kb knowledge_vitali index embeddings

## Done When

_Name the observable condition that makes the task complete._

Residuo de Calendar removido de la KB; dudas de negocio resueltas o marcadas como pendientes de dato externo; embeddings reindexados; sldb stores check PASS.
