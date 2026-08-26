---
id: task-integracion-total-end-to-end-con-corrida-real
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-integracion-total-end-to-end-con-corrida-real
current_node: complete
history: []
references: []
depends_on:
- task-implementar-extractor-de-traits
- task-implementar-generador-de-átomos-sldb
- task-implementar-fallback-estricto-del-conversador
- task-implementar-tool-calling-estructurado
- task-implementar-compilador-de-contexto
pills: []
files: []
checklists:
- checklist-task-integracion-total-end-to-end-con-corrida-real-execution-ready
- checklist-task-integracion-total-end-to-end-con-corrida-real-testing-ready
- checklist-task-integracion-total-end-to-end-con-corrida-real-closeout-ready
task_type: test
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-cuatro-motores-cognitivos-de-conversacion
- atom-contexto-compilado
- atom-agente-conversador
---

# Integracion Total End-to-End con Corrida Real

## Rationale

_Explain why this task exists or the business driver behind it._

Los 43 unit tests son mockeados; nada prueba el sistema COMPLETO conversando de verdad. Recupera niveles 2/3/4 de la estrategia de testing borrada.

## Goal

_Describe the concrete result this task must produce._

Cablear los 10 modulos al entrypoint y correr una conversacion REAL end-to-end contra Gemini real (Vertex ADC), SLDB real sembrado y SQL real. CERO mock, CERO dummy, CERO stub.

## Scope

_State what is in scope and what is out of scope._

tests/e2e/ (runner + chat real), tests/knowledge/ store real

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- Pregunta fuera de dominio ("¿cuál es la capital de Mongolia?") al Conversador con contexto is_empty=true.
- Assert: la respuesta es EXACTAMENTE "No tengo esa información a mano, la averiguaré." (Gemini real, no mock).

## Done When

_Name the observable condition that makes the task complete._

- PROHIBIDO mock, dummy, stub, monkeypatch del LLM, o fake del SLDBReader.
- Los 10 módulos nuevos se integran vía el runner E2E (tests/e2e/run_donpeppe.py y chat_donpeppe.py): SLDBReader real -> ContextCompiler real -> Conversador (Gemini real). Ese es el entrypoint de la nueva arquitectura.
- La corrida usa Gemini real vía Vertex ADC (ya funcional en este repo).
