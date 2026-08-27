---
id: step-vitali-agendar-visita
title: Agendar la visita
atom_type: step
kind: llamado_tool
tags:
- conversation:steps.agendar_visita
- agent:booking-workflow
- system:vitali
domain_ref: null
summary: Revisa disponibilidad y presenta opciones de horario (sin preguntar fecha
  primero); el lead elige un bloque.
embedding: null
parent: null
semantic_anchors: null
---

# Agendar la visita

## Instructions

Cuando el lead exprese interes en agendar ('quiero agendar', '¿que hay disponible?'), NO preguntar '¿que fecha/hora?': primero revisar disponibilidad y presentar opciones. Inferir fechas automaticamente ('esta semana', 'la proxima', 'manana'; sin fecha = proximos 5-7 dias habiles). Ofrecer solo horarios dentro del horario de atencion y en la zona horaria del lead. Presentar 5-7 opciones (2-3 dias, 2-3 bloques) con horas limpias y preguntar cual sirve. Confirmar el pais/ciudad del lead para la zona horaria y la oficina.

## Required Slots

fecha y hora elegidas por el lead

## Handout Target



## Tool



## Allowed Transitions

conversation:steps.datos_contacto

## Grounding Atoms

rule-business-hours, rule-timezone-routing, rule-visit-modality, strategy-vitali-slot-presentation, dom-contact-offices

## Completion Condition

El lead eligio una fecha y hora dentro del horario de atencion.
