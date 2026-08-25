---
id: task-alinear-agente-conversador-a-nueva-arquitectura
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-alinear-agente-conversador-a-nueva-arquitectura
current_node: checklist-task-alinear-agente-conversador-a-nueva-arquitectura-execution-ready
history: []
references: []
depends_on: []
pills:
- desk/contexts/pill-conversador-jamas-alucina-sin-contexto.md
files: []
checklists:
- checklist-task-alinear-agente-conversador-a-nueva-arquitectura-execution-ready
- checklist-task-alinear-agente-conversador-a-nueva-arquitectura-testing-ready
- checklist-task-alinear-agente-conversador-a-nueva-arquitectura-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-agente-conversador
- atom-contexto-compilado
---

# Alinear Agente Conversador a Nueva Arquitectura

## Rationale

_Explain why this task exists or the business driver behind it._

El prompt y comportamiento debe seguir el nuevo flujo de inyección estricta

## Goal

_Describe the concrete result this task must produce._

Refactorizar conversador_apos para depender 100% del contexto

## Scope

_State what is in scope and what is out of scope._

kb_agent/agent.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._
- [ ] Definir el contrato exacto (JSON Schema) del payload 'Contexto Compilado' entre Ontologizador y Conversador.

## Estrategia de Testing Asignada
- [ ] **Boundary Test (Quiebre)**: Inyectar un contexto vacío por la fuerza y validar mediante regex que la respuesta es explícitamente de desconocimiento ('No sé / Averiguaré'), fallando si hay alucinación.
- [ ] **Tool-Call Test**: Proveer un contexto con un ToolAtom y validar que el output del modelo sea estrictamente un JSON de `function_call` y no texto libre.
