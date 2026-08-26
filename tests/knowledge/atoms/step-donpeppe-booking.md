---
id: step-donpeppe-booking
title: Reserva de mesa
atom_type: step
tags:
- conversation:steps.booking
- system:donpeppe
domain_ref: don-peppe
---

# Reserva de mesa

## Instructions

Guiar la reserva de mesa recolectando fecha, hora y cantidad de personas, una pregunta a la vez. Validar la regla de reservas (2 a 8 personas, no para el mismo día). Confirmar los datos con la persona antes de crear la reserva. Al tener todo confirmado, ejecutar la tool crear_reserva.

## Required Slots

fecha, hora, personas, nombre

## Allowed Transitions

conversation:steps.onboarding

## Grounding Atoms

atom-donpeppe-regla-reservas, atom-donpeppe-promos, crear_reserva

## Completion Condition

La reserva fue creada con éxito mediante la tool, o la persona decide no continuar con la reserva.
