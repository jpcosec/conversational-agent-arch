---
id: rule-visit-modality
title: 'Regla: modalidad de la visita'
five_wh_one_plus: what
atom_type: rule
tags:
- domain:booking
- agent:conversation-rule
- system:vitali
applies_to: null
provenance: null
summary: La cita agendada es una VISITA / reunion comercial, no una reserva de suite.
  Como los proyectos abren entre 2026 y 2034, la mayoria de los sitios aun no son
  visitables fisicamente.
embedding: null
parent: null
semantic_anchors: null
---

# Regla: modalidad de la visita

## Answer

La cita agendada es una VISITA / reunion comercial, no una reserva de suite. Como los proyectos abren entre 2026 y 2034, la mayoria de los sitios aun no son visitables fisicamente. El sitio enmarca las visitas como citas de oficina ('Agenda una cita en cualquiera de nuestras oficinas'). Modalidad por defecto: reunion en oficina (Santiago: Av. La Dehesa 440, Piso 3, Lo Barnechea; o Doral, USA: 8333 NW 53rd St, Suite 450) o llamada virtual, segun ubicacion y preferencia del lead. Al crear el evento, SIEMPRE fijar una ubicacion (direccion de oficina o link de videollamada). PENDIENTE confirmar: si hay tours en terreno para proyectos en Set-up (Chicureo, Mantagua).

## Conditions

Se agenda o describe una visita/reunion.
