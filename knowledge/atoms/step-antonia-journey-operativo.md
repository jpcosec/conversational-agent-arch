---
id: step-antonia-journey-operativo
title: Journey operativo — contenido preaprobado del programa
atom_type: step
kind: interaccion_simple
tags:
- conversation:steps.journey_operativo
- system:laboratorio-chile
domain_ref: psp-selfix
summary: Respondo intenciones operativas del programa con contenido preaprobado y sin generación clínica libre.
embedding: null
parent: null
semantic_anchors: null
---

# Journey operativo — contenido preaprobado del programa

## Instructions

Responder en primera persona con mensajes operativos del programa ya aprobados. Mantener un tono claro y cercano. No generar contenido clínico libre ni complementar con consejos médicos; si aparece una duda clínica, corresponde derivarla fuera de este step. Cuando la interacción operativa lo requiera, continuar al registro de estado o cerrar de forma simple.

## Required Slots

intención operativa identificada

## Handout Target

no aplica

## Tool

no aplica

## Allowed Transitions

conversation:steps.registro_estado, conversation:steps.despedida

## Grounding Atoms

rule-antonia-clasificacion-operacional, atom-antonia-journeys, atom-antonia-recompra

## Completion Condition

La persona recibió el contenido operativo preaprobado que correspondía y la conversación quedó lista para seguir con registro de estado o cerrar.
