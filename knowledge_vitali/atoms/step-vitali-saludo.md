---
id: step-vitali-saludo
title: Saludo y segmentacion
atom_type: step
kind: interaccion_simple
tags:
- conversation:steps.saludo
- agent:conversation-rule
- system:vitali
domain_ref: null
summary: Saludo corto que segmenta al lead en suite/broker/franquicia y avanza a calificacion
  o agenda.
embedding: null
parent: null
semantic_anchors: null
---

# Saludo y segmentacion

## Instructions

Abrir corto (2-5 palabras) con una sola pregunta. Identificar a que segmento pertenece el lead: Quiero una Suite (residente/familiar/inversion), Quiero ser Broker, o Quiero una Franquicia. Pregunta de apertura sugerida: '¿Para quien estas buscando la propiedad? ¿Para un familiar, o para ti?'. Avanzar a calificacion segun el segmento.

## Required Slots

segmento del lead (suite / broker / franquicia)

## Handout Target



## Tool



## Allowed Transitions

conversation:steps.calificacion, conversation:steps.agendar_visita

## Grounding Atoms

self-vitali, style-vitali, dom-contact-lead-segments, strategy-vitali-opening

## Completion Condition

Se identifico el segmento del lead.
