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

Ambigüedad resuelta — reparto SM vs agente:
- La TRANSICIÓN a `breakpoint_miss` la hace el router (core SM) cuando payload.is_empty==true. Esta tarea NO define el nodo, solo el comportamiento del Conversador DENTRO de él.
- Estando en breakpoint_miss, el Conversador emite una frase de desconocimiento y NO intenta responder el fondo (cero parámetrico).
- Frase canónica única (usar EXACTA para test determinista): `"No tengo esa información a mano, la averiguaré."`
- El system prompt prohibe explícitamente responder fuera de domain_facts/rules recibidos.

## Validation

- Test de matriz (promptfoo/DeepEval): inyectar payload con is_empty=true y afirmar salida == la frase canónica exacta; FALLA si aparece cualquier intento de responder el fondo.
- Inyectar payload con domain_facts y afirmar que la respuesta usa esos hechos (no la frase canónica).

## Done When

En breakpoint_miss el Conversador emite la frase canónica exacta y nunca alucina.
