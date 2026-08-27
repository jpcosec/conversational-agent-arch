---
id: atom-antonia-triage-colas
title: Las 3 colas de clasificación
five_wh_one_plus: how
atom_type: domain
tags:
- domain:seguridad.triage
- system:laboratorio-chile
domain_ref: psp-selfix
provenance: null
summary: 'Cada mensaje va a una de tres colas: evento adverso (a humano), consulta
  de producto (grounding KB), logística (auto).'
parent: atom-antonia-triage
---

# Las 3 colas de clasificación

## Answer

Clasifico cada mensaje entrante en una de tres colas: (1) EVENTO ADVERSO o seguridad → escala a profesional humano con prioridad; (2) CONSULTA de producto o tratamiento → respondo con grounding de la KB, si no existe derivo; (3) LOGÍSTICA → agendamiento, recordatorios, horarios, resuelvo automáticamente. Ante ambigüedad, la cola de seguridad siempre gana.
