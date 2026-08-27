---
id: domain-triage-categorias
title: Categorías de la cola
five_wh_one_plus: how
atom_type: domain
tags:
- domain:pharma.patient_support.triage.queues
- topic:triage
summary: 'Tres canales de clasificación: evento adverso (a humano), consulta de producto
  (grounding KB), logística (auto: horarios, recordatorios).'
parent: domain-triage-root
---

# Categorías de la cola

## Answer

Antonia clasifica cada mensaje entrante en una de tres colas: (1) EVENTO ADVERSO / seguridad → escala a profesional humano con prioridad; (2) CONSULTA DE PRODUCTO / tratamiento → responde con grounding de la KB si existe, si no deriva; (3) LOGÍSTICA → agendamiento, recordatorios, horarios, resuelve automáticamente. La cola 1 siempre gana si hay ambigüedad.
