---
id: step-vitali-cierre
title: Cierre y confirmacion
atom_type: step
kind: interaccion_simple
tags:
- conversation:steps.cierre
- agent:booking-workflow
- system:vitali
domain_ref: null
summary: Confirma fecha/hora y avisa correo e invitacion de calendario; sin exponer
  procesos internos.
embedding: null
parent: null
semantic_anchors: null
---

# Cierre y confirmacion

## Instructions

Resumir la reserva completada: fecha y hora, duracion (30 min), y avisar 'recibiras un correo de confirmacion en breve' y 'recibiras una invitacion de calendario en breve'. No mencionar procesos internos ni correos internos. Cerrar de forma calida.

## Required Slots

(ninguno)

## Handout Target



## Tool



## Allowed Transitions

(ninguna, paso terminal)

## Grounding Atoms

boundary-vitali-customer-facing, dom-concept-value-proposition

## Completion Condition

Se confirmo la cita al cliente sin exponer procesos internos.
