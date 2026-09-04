---
id: task-chat-de-producto-sin-inspector-para-el-equipo-de-vitali
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-chat-de-producto-sin-inspector-para-el-equipo-de-vitali
current_node: checklist-task-chat-de-producto-sin-inspector-para-el-equipo-de-vitali-execution-ready
history: []
references: []
depends_on:
- task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo
pills: []
files: []
checklists:
- checklist-task-chat-de-producto-sin-inspector-para-el-equipo-de-vitali-execution-ready
- checklist-task-chat-de-producto-sin-inspector-para-el-equipo-de-vitali-testing-ready
- checklist-task-chat-de-producto-sin-inspector-para-el-equipo-de-vitali-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Chat de producto sin inspector para el equipo de Vitali

## Rationale

_Explain why this task exists or the business driver behind it._

El chat actual es una herramienta de auditoria; el equipo de Vitali necesita probar la vendedora virtual como la veria un cliente, y el canal real es el telefono.

## Goal

_Describe the concrete result this task must produce._

Ruta /chat con solo la conversacion: brand del negocio, sin inspector ni badges, boton Nueva conversacion, formulario inicial opcional de nombre y telefono que fija external_id por telefono (identity_key phone), diseño movil primero, indicador de escribiendo. Navegacion en tres grupos: Chat, Operacion (Leads, Metricas), Desarrollo (Inspector, Flow, Mindmap), etiquetas en espanol desde el yaml.

## Scope

_State what is in scope and what is out of scope._

frontends/chat (nueva plantilla), frontends/shared, project.*.yaml nav_labels, frontends/UI-GUIDE.md, tests/ui.

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration -q
- python -m pytest tests/ui -q

## Done When

_Name the observable condition that makes the task complete._

Un tester en el celular abre /chat, se identifica con su telefono, conversa y el mismo usuario aparece en Leads con su ficha; tests/ui verdes.
