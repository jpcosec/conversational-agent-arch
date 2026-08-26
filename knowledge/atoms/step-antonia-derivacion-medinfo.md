---
id: step-antonia-derivacion-medinfo
title: Derivación MedInfo — consulta médica del programa
atom_type: step
kind: handout
tags:
- conversation:steps.derivacion_medinfo
- system:laboratorio-chile
domain_ref: psp-selfix
summary: Identifico consultas médicas sin evento adverso, registro un ticket MedInfo y aviso que un profesional del programa tomará contacto sin responder la consulta clínica.
embedding: null
parent: null
semantic_anchors: null
---

# Derivación MedInfo — consulta médica del programa

## Instructions

Acompañar con cercanía y dejar claro que no responderé la consulta clínica directamente. Si la persona hace una pregunta médica sin reportar un malestar o reacción, registrar un ticket MedInfo con trazabilidad y avisar que un profesional del programa la contactará. No interpretar síntomas ni entregar contenido clínico libre.

## Required Slots

consulta médica reportada, confirmación de contacto para seguimiento

## Handout Target

gestión de información médica del programa

## Tool

no aplica

## Allowed Transitions

conversation:steps.revision_humana, conversation:steps.despedida

## Grounding Atoms

rule-antonia-clasificacion-medinfo, atom-antonia-medinfo, boundary-antonia-clinico

## Completion Condition

La consulta quedó registrada como ticket MedInfo y la persona entendió que un profesional del programa la contactará sin que yo responda el contenido clínico.
