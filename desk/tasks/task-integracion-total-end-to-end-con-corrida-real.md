---
id: task-integracion-total-end-to-end-con-corrida-real
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-integracion-total-end-to-end-con-corrida-real
current_node: checklist-task-integracion-total-end-to-end-con-corrida-real-execution-ready
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

- 

## Done When

_Name the observable condition that makes the task complete._

El servidor real levanta, una conversacion real de 3 turnos con la pizzeria Don Peppe pasa por router->ontologizador->conversador con Gemini real, y se observa: (1) respuesta con dato real del KB, (2) fallback canonico exacto ante pregunta fuera de dominio, (3) tool-call estructurado real.

## Niveles Recuperados (estrategia de testing borrada)

Recupera y ejecuta los niveles 2, 3 y 4 de la estrategia original — TODO con datos reales:

### Nivel 2 — Fallback estricto contra LLM real
- Pregunta fuera de dominio ("¿cuál es la capital de Mongolia?") al Conversador con contexto is_empty=true.
- Assert: la respuesta es EXACTAMENTE "No tengo esa información a mano, la averiguaré." (Gemini real, no mock).

### Nivel 3 — Simulador End-to-End con subgrafo REAL en SLDB
- Sembrar un store SLDB real `tests/knowledge/` con átomos reales de la pizzería Don Peppe:
  - DomainAtom horarios: "Don Peppe abre de martes a domingo, 19:00 a 23:30. Lunes cerrado."
  - DomainAtom carta: "Pizzas: Margherita 8900, Pepperoni 10500, Cuatro Quesos 11200. Napolitana 9800."
  - RuleAtom reservas: "Reservas mínimo 2 personas, máximo 8. No se aceptan reservas el mismo día."
  - ToolAtom crear_reserva: schema JSON {fecha, hora, personas, nombre}.
- Levantar el servidor real (uvicorn) y conversar de verdad vía POST /api/chat.

### Nivel 4 — Golden Transcript real (Shadow Mode)
- Correr una conversación real de 3 turnos y verificar el flujo completo router->ontologizador->conversador:
  - Turno 1 (dato real KB): "¿A qué hora abren el sábado?" -> respuesta DEBE contener "19:00" y "23:30" leídos del DomainAtom real (no inventados).
  - Turno 2 (fallback): "¿Tienen sucursal en París?" -> fallback canónico exacto (no está en el KB).
  - Turno 3 (tool-call real): "Quiero reservar mesa para 4 el próximo viernes a las 20:00" -> Conversador emite function_call estructurado real name=crear_reserva con args {personas:4, hora:"20:00", ...}.
- Guardar el transcript real (request+response de cada turno) como evidencia en runs/e2e/donpeppe-transcript.json.

## Regla dura
- PROHIBIDO mock, dummy, stub, monkeypatch del LLM, o fake del SLDBReader.
- Los 10 módulos nuevos se integran vía el runner E2E (tests/e2e/run_donpeppe.py y chat_donpeppe.py): SLDBReader real -> ContextCompiler real -> Conversador (Gemini real). Ese es el entrypoint de la nueva arquitectura.
- La corrida usa Gemini real vía Vertex ADC (ya funcional en este repo).
