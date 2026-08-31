---
id: task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security
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

# Vitali no tiene piso de seguridad: ningun RuleAtom conversation:security

ID: task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184452-suggestion-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security.md`.

## Scope

Goal: que el bundle de Vitali tenga el piso de seguridad que el compilador espera.
Scope: knowledge_vitali no tiene ningun RuleAtom con tag 'conversation:security'. El compilador (kb_agent/ontologizador/compiler.py) mete ese piso en TODOS los bundles como garantia minima, independiente del retrieval; en Vitali ese piso esta vacio. Se noto al diagnosticar los embeddings: con la KB sin vectores el bundle quedaba reducido al piso de seguridad + grounding_atoms del step, y el piso no aportaba nada. Los embeddings ya se arreglaron, pero el hueco de contenido sigue: falta definir que reglas de seguridad/limite aplican a un negocio de senior-living (que NO se promete, derivaciones, datos sensibles de un adulto mayor, limites de la venta) y escribirlas como RuleAtom en la KB. Comparar con el piso equivalente de knowledge/ (Antonia).
Validation: assert de que el bundle de Vitali incluye al menos un RuleAtom conversation:security; escenario e2e que verifique el limite en conversacion.

## Source

- `desk/inbox/20260827-184452-suggestion-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security.md`

## Done When

- The message is resolved, answered, or promoted into active work.
