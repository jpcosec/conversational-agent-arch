---
# pill-xxx
id: pill-pattern-modelación-de-átomos-psp-con-los-10-modelos-existentes
# e.g., language:python, library:pydantic
tags:
- system:antonia
- domain:psp
- topic:modelacion
---

# Pattern: Modelación de átomos PSP con los 10 modelos existentes

## What

_Define the context or guardrail this pill carries._

Mapa de modelación para las piezas PSP. Reglas clasificadoras de las 4 ramas -> RuleAtom (answer + conditions + applies_to, tags conversation:classification). Steps nuevos (medinfo, revision_humana, journey_operativo, validacion_policy_gate) -> ConversationStep (instructions, required_slots, allowed_transitions, grounding_atoms, completion_condition, tag conversation:steps.nombre). Criterios del policy gate -> GateCriterion, MODELO NUEVO de la familia gate (criterion, approval_condition, rejection_action, tags gate:*) — único modelo nuevo autorizado, decisión en atom-decisión-familia-gate-con-modelo-gatecriterion-para-el-policy-gate. Información MedInfo/FV/titulación/molécula de negocio -> DomainAtom (answer, tags domain:*). Límites nuevos -> extender CapabilityBoundary existente solo si la restricción es del agente conversacional (no del gate).

## Why

_Explain why this context matters for safe execution._

La heurística de modelation-guide dice crear modelo nuevo solo si hay forma de campo distinta, comportamiento de compilación distinto o validación distinta. Las piezas conversacionales PSP son variantes de RuleAtom, ConversationStep o DomainAtom distinguidas por tags. El gate SÍ cumple el criterio 2 (comportamiento de compilación distinto) — se activa post-draft sobre la respuesta redactada, un eje de activación que ninguna familia existente tiene; por eso GateCriterion es familia nueva. El compilador no itera el tipo gate en _MODEL_TYPES, así que sus átomos son invisibles al turno actual — cero regresión.

## When

_Describe when an agent should apply this pill._

Al crear cada átomo nuevo de la tarea PSP; consultar antes de decidir el atom_type.

## Where

_Name the files, surfaces, or scope this pill applies to._

knowledge/atoms/*.md; taxonomía en knowledge_base/taxonomy/modelation-guide.md y retrieval-architecture.md; los 5 ejes de activación: self:* siempre, domain:* por relevancia, conversation:* por estado, user:traits.* por identidad, source:* nunca.

## How

_Describe the correct way to apply this guidance._

Cada átomo lleva: id con prefijo del tipo (rule-antonia-*, step-antonia-*, atom-antonia-*), title claro, atom_type del modelo, tags con eje correcto, summary de una frase, y los campos del modelo en secciones Markdown (## Answer, ## Conditions, ## Instructions, etc.). Steps además llevan kind (interaccion_simple / obtencion_datos / llamado_tool / handout) y domain_ref: psp-selfix.

## How Not

_Describe the shortcut or failure mode to avoid._

No usar atom_type como tag (el Ontologizador filtra por modelo, no por tag). No mezclar dos formas de campo en un modelo con enum. No modelar los criterios del gate como RuleAtom ni CapabilityBoundary — RuleAtom es familia domain y contaminaría el contexto del Conversador en todos los turnos; CapabilityBoundary es familia self y _extract_persona usa boundaries[0], con riesgo de desplazar boundary-antonia-clinico. Usar el modelo GateCriterion de la familia gate (ver atom-decisión-familia-gate-con-modelo-gatecriterion-para-el-policy-gate). No crear ningún otro modelo más allá de GateCriterion. No dejar allowed_transitions colgando hacia steps inexistentes.
