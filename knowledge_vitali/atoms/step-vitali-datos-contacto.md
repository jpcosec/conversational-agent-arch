---
id: step-vitali-datos-contacto
title: Datos de contacto
atom_type: step
kind: obtencion_datos
tags:
- conversation:steps.datos_contacto
- agent:booking-workflow
- system:vitali
domain_ref: null
summary: Reune email, telefono y proposito en un mensaje conciso antes de confirmar
  la reserva.
embedding: null
parent: null
semantic_anchors: null
---

# Datos de contacto

## Instructions

Una vez que el lead elige un horario, reunir en un solo mensaje conciso: proposito/titulo de la reunion (si no se dio), email (imprescindible para la invitacion de calendario) y telefono. Pedirlo conversacionalmente, no como checklist. No cerrar la reserva hasta tener todos los campos requeridos.

## Required Slots

email; telefono; proposito/titulo de la reunion

## Handout Target



## Tool



## Allowed Transitions

conversation:steps.cierre

## Grounding Atoms

dom-contact-lead-qualification, strategy-vitali-respond-first

## Completion Condition

Se reunieron email, telefono y proposito de la reunion.
