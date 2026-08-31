---
id: task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente
status: deferred
summary: ''
tags:
- workspace:desk
- artifact:task
- source:inbox
routine: ''
current_node: ''
history: []
references: []
depends_on: []
pills: []
files: []
checklists: []
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Verificar si el known_gap donpeppe_saludo_unico sigue vigente

ID: task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184454-suggestion-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente.md`.

## Scope

Goal: que los known_gap del repo describan defectos reales y no queden como xfail zombie.
Scope: tests/e2e/simulation/scenarios.py:175 (donpeppe_saludo_unico) justifica el known_gap diciendo que el conversador saluda en cada turno 'sin historial de conversacion', pero hoy kb_agent/llm.py:90-103 SI inyecta history_prompt al draft NL. El gap puede estar ya resuelto y el xfail sin actualizar -- y un known_gap es xfail estricto, asi que si paso empieza a fallar como XPASS. No se pudo verificar en el diagnostico porque requiere LLM real (fuera del alcance de SKIP_LLM_TESTS). Nota: el known_gap vecino scenarios.py:212 (donpeppe_reserva_paso_a_paso) SI sigue vigente -- decide_turn/_select_relevant_tool (kb_agent/agent.py:109-140) solo leen compiled_context['question'], nunca el historial, asi que el slot-filling multi-turno no puede completarse. Ojo: la KB de ejemplo Don Peppe se va a recrear, asi que verificar el mecanismo, no el atom.
Validation: set -a; source .env; set +a; python -m pytest tests/e2e/simulation -m simulation -k saludo_unico -q (2 corridas); si pasa, quitar la marca known_gap.

## Source

- `desk/inbox/20260827-184454-suggestion-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente.md`

## Done When

- The message is resolved, answered, or promoted into active work.
