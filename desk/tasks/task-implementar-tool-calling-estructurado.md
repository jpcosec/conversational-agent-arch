---
id: task-implementar-tool-calling-estructurado
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-tool-calling-estructurado
current_node: checklist-task-implementar-tool-calling-estructurado-execution-ready
history: []
references: []
depends_on:
- task-implementar-compilador-de-contexto
pills: []
files: []
checklists:
- checklist-task-implementar-tool-calling-estructurado-execution-ready
- checklist-task-implementar-tool-calling-estructurado-testing-ready
- checklist-task-implementar-tool-calling-estructurado-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-apis-externas-integracion
---

# Implementar Tool Calling Estructurado

## Rationale

Permite que el Conversador invoque APIs externas emitiendo JSON estructurado en vez de texto libre.

## Goal

_Describe the concrete result this task must produce._

Emitir function_call JSON en lugar de texto si hay ToolAtoms.

## Scope

EN: Convertir los ToolAtoms del payload en function_declarations y emitir function_call.
FUERA: pausa de la SM (router) y ejecución real de la API.

## Implementation Path

`kb_agent/agent.py` + `kb_agent/kb_tools.py`

Ambigüedad resuelta — shape del function_call emitido:
```
{ "function_call": { "name": str, "args": { ... } } }
```
- `name` debe coincidir con el id del ToolAtom.
- `args` valida contra el JSON schema del ToolAtom; si faltan args obligatorios, el Conversador pregunta al usuario en vez de emitir.
- Cuando el payload trae tools relevantes y la intención las requiere, emite function_call; si no, responde NL.

## Validation

- Test de matriz: payload con ToolAtom de Calendar + "reserva mañana" → afirmar output es function_call JSON válido (no texto).
- Afirmar que si falta un arg obligatorio, el bot lo pide y NO emite function_call.

## Done When

El Conversador emite function_call válido contra el schema y pide args faltantes.
