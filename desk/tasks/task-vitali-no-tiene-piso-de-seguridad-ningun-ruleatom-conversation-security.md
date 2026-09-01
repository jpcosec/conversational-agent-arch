---
id: task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security
status: ready_for_testing
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security
current_node: checklist-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-closeout-ready
history:
- operator-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-activate
- operator-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-ready-for-testing
references:
- desk/drawer/tasks/task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security.md
depends_on: []
pills: []
files: []
checklists:
- checklist-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-execution-ready
- checklist-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-testing-ready
- checklist-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
closeout_evidence_verified: false
pill_graduation_verified: true
---

# Vitali no tiene piso de seguridad: ningun RuleAtom conversation:security

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184452-suggestion-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security.md`.

## Scope

_State what is in scope and what is out of scope._

Goal: que el bundle de Vitali tenga el piso de seguridad que el compilador espera.
Scope: knowledge_vitali no tiene ningun RuleAtom con tag 'conversation:security'. El compilador (kb_agent/ontologizador/compiler.py) mete ese piso en TODOS los bundles como garantia minima, independiente del retrieval; en Vitali ese piso esta vacio. Se noto al diagnosticar los embeddings: con la KB sin vectores el bundle quedaba reducido al piso de seguridad + grounding_atoms del step, y el piso no aportaba nada. Los embeddings ya se arreglaron, pero el hueco de contenido sigue: falta definir que reglas de seguridad/limite aplican a un negocio de senior-living (que NO se promete, derivaciones, datos sensibles de un adulto mayor, limites de la venta) y escribirlas como RuleAtom en la KB. Comparar con el piso equivalente de knowledge/ (Antonia).
Validation: assert de que el bundle de Vitali incluye al menos un RuleAtom conversation:security; escenario e2e que verifique el limite en conversacion.

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security.md.

## Validation

_List the checks required before this task can close._

- pytest

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
