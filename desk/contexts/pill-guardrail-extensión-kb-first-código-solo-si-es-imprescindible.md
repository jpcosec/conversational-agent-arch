---
# pill-xxx
id: pill-guardrail-extensión-kb-first-código-solo-si-es-imprescindible
# e.g., language:python, library:pydantic
tags:
- system:antonia
- domain:psp
- topic:doctrina
---

# Guardrail: Extensión KB-first, código solo si es imprescindible

## What

_Define the context or guardrail this pill carries._

Doctrina de trabajo para la tarea PSP: todo lo que pueda expresarse como átomos tipados de knowledge/ (reglas de clasificación, steps de flujo, criterios de policy gate, domain atoms de MedInfo/FV) se modela en la KB. El código del runtime (decide_turn, compiler, state_machine) queda intacto en esta fase.

## Why

_Explain why this context matters for safe execution._

El runtime actual ya compila y entrega toda la KB al LLM por turno; agregar conocimiento bien redactado cambia el comportamiento sin riesgo de regresión. Las garantías duras (ruteo forzado, gate post-draft bloqueante) requieren código, pero son fase posterior — primero se valida el diseño conversacional en KB.

## When

_Describe when an agent should apply this pill._

Durante toda la ejecución de la tarea de extensión del flujo conversacional PSP. Antes de proponer cualquier cambio de código, verificar si el mismo efecto se logra con un átomo.

## Where

_Name the files, surfaces, or scope this pill applies to._

knowledge/atoms/ (KB real de Antonia). NUNCA tests/knowledge/ (fixture Don Peppe). Modelos disponibles en kb_agent/models/knowledge/: DomainAtom, RuleAtom, ConversationStep, CapabilityBoundary, FallbackRule, StrategyRule, ToolAtom, TraitAtom, SelfDeclaration, StyleGuide.

## How

_Describe the correct way to apply this guidance._

Crear átomos .md con frontmatter tipado (atom_type correcto + campos del modelo). Reindexar el store SLDB tras cada lote. Verificar con el CLI knowledge (explore/self/step/show) que los átomos se recuperan. Probar conversaciones reales con python -m kb_agent.cli contra la KB extendida.

## How Not

_Describe the shortcut or failure mode to avoid._

No modificar kb_agent fuera de models/knowledge — la única excepción autorizada es crear gate.py con el modelo GateCriterion y su export, según atom-decisión-familia-gate-con-modelo-gatecriterion-para-el-policy-gate. No crear otros modelos SLDB más allá de GateCriterion (heurística de modelation-guide — RuleAtom con tags cubre clarificación, confirmación y recovery). No meter roles del pipeline en la familia self. No tocar la KB de Don Peppe. No inventar contenido clínico — todo texto médico sale del corpus aprobado (folleto ISP / material Medical).
