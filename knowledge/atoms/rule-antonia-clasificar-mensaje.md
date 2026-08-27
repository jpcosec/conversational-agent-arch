---
id: rule-antonia-clasificar-mensaje
title: Clasificar cada mensaje entrante
five_wh_one_plus: when
atom_type: rule
tags:
- domain:pharma.patient_support.triage
- topic:rules.triage
conditions: Llega cualquier mensaje del usuario al inicio del turno.
summary: Todo mensaje se enruta a una de 3 colas (evento adverso / producto / logística).
  Ante ambigüedad, gana seguridad.
parent: domain-triage-categorias
---

# Clasificar cada mensaje entrante

## Answer

Clasifica cada mensaje entrante en una de tres colas antes de responder: (1) EVENTO ADVERSO o señal de seguridad → protocolo de escalada; (2) CONSULTA de producto/tratamiento → responde con grounding de la KB o deriva si no hay; (3) LOGÍSTICA → agenda, recordatorios, horarios. Si un mensaje es ambiguo entre seguridad y otra cosa, trátalo como seguridad.
