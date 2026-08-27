---
id: step-vitali-calificacion
title: Calificacion del lead
atom_type: step
kind: obtencion_datos
tags:
- conversation:steps.calificacion
- agent:conversation-rule
- system:vitali
domain_ref: null
summary: Califica al lead segun su segmento (suite/broker/franquicia) y fija el proposito
  de la reunion.
embedding: null
parent: null
semantic_anchors: null
---

# Calificacion del lead

## Instructions

Reunir conversacionalmente las senales de calificacion segun el segmento. Suite: '¿Para quien es?' (para mi / un familiar / inversion), rango etario y comuna; proposito de la reunion = visita/informacion de residencia. Broker: empresa y venta mensual; proposito = comercializacion/brokerage. Franquicia: empresa/capacidad de inversion y sitio web; proposito = desarrollo de franquicia. No pedir todo como checklist; conversar. Todos agendan el mismo bloque de 30 min 'Reu Vitali', pero el titulo/agenda de la reunion debe reflejar el segmento.

## Required Slots

senales de calificacion del segmento; proposito de la reunion

## Handout Target



## Tool



## Allowed Transitions

conversation:steps.agendar_visita

## Grounding Atoms

dom-contact-lead-qualification, dom-contact-lead-segments, rule-visit-modality

## Completion Condition

Se reunieron las senales de calificacion y el proposito de la reunion.
