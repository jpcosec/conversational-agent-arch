---
id: rule-business-hours
title: 'Regla: horario de atencion'
five_wh_one_plus: when
atom_type: rule
tags:
- domain:booking
- agent:conversation-rule
- system:vitali
applies_to: null
provenance: null
summary: 'Lunes a Viernes 9:00 - 19:00; Sabado 9:00 - 14:00; Domingo cerrado. Solo
  ofrecer horarios de cita dentro de este rango. Zona horaria: America/Santiago. Si
  piden un horario fuera de'
embedding: null
parent: null
semantic_anchors: null
---

# Regla: horario de atencion

## Answer

Lunes a Viernes 9:00 - 19:00; Sabado 9:00 - 14:00; Domingo cerrado. Solo ofrecer horarios de cita dentro de este rango. Zona horaria: America/Santiago. Si piden un horario fuera de rango, explicar amablemente la disponibilidad real.

## Conditions

Se ofrecen o discuten horarios de cita.
