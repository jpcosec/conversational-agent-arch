---
id: task-implementar-fallback-estricto-del-conversador
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-fallback-estricto-del-conversador
current_node: checklist-task-implementar-fallback-estricto-del-conversador-execution-ready
history: []
references: []
depends_on:
- task-implementar-compilador-de-contexto
pills:
- desk/contexts/pill-conversador-jamas-alucina-sin-contexto.md
files: []
checklists:
- checklist-task-implementar-fallback-estricto-del-conversador-execution-ready
- checklist-task-implementar-fallback-estricto-del-conversador-testing-ready
- checklist-task-implementar-fallback-estricto-del-conversador-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-agente-conversador
---

# Implementar Fallback Estricto del Conversador

## Rationale

Garantiza cero alucinación: si no hay contexto, el bot admite no saber en lugar de inventar.

## Goal

_Describe the concrete result this task must produce._

Forzar salida 'No sé' si el contexto es vacío (cero alucinación).

## Scope

EN: Lógica de fallback cuando el Contexto Compilado llega con `is_empty=true`.
FUERA: emisión de tools (tarea aparte), compilación de contexto.

## Implementation Path

`kb_agent/agent.py` (conversador_apos)

Ambigüedad resuelta:
- Detonante exacto: payload.is_empty == true (NO heurística de confianza del LLM).
- Comportamiento: responder con un mensaje de desconocimiento honesto ("no lo sé / lo averiguaré"), sin intentar responder la pregunta de fondo.
- El system prompt debe prohibir explícitamente responder fuera del domain_facts/rules recibidos.

## Validation

- Test de matriz (promptfoo/DeepEval): inyectar payload con is_empty=true y afirmar por regex que la respuesta es de desconocimiento; FALLA si intenta responder el fondo.
- Inyectar payload con domain_facts y afirmar que la respuesta usa esos hechos.

## Done When

El fallback se dispara SOLO por is_empty y el test de no-alucinación pasa.
