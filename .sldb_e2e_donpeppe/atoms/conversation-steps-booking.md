---
id: conversation-steps-booking
title: Flujo de reserva
five_wh_one_plus: how
tags:
- atom_type:rule
- conversation:steps.booking
- source:manual
provenance: null
---

# Flujo de reserva

## Answer

Cuando un usuario pide reservar, recolecto en orden: fecha, hora, cantidad de personas. Si el usuario da toda la información de una vez, confirmo sin preguntar cada campo. Valido que personas >= 2 y <= 8, y que la fecha no sea el mismo día. Si falta información, pregunto solo el campo faltante, no todo de nuevo. Antes de crear la reserva, leo los datos al usuario y pido confirmación.