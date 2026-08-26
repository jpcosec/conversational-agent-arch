---
id: step-donpeppe-onboarding
title: Onboarding — atención general
atom_type: step
kind: interaccion_simple
tags:
- conversation:steps.onboarding
- system:donpeppe
domain_ref: don-peppe
---

# Onboarding — atención general

## Instructions

Saludar una vez y ponerse a disposición. Responder consultas sobre la carta, horarios, ubicación y promociones usando la base de conocimiento. Si la persona muestra intención de reservar una mesa, transicionar al paso de reserva.

## Required Slots

consulta de la persona

## Allowed Transitions

conversation:steps.booking

## Grounding Atoms

atom-donpeppe-carta, atom-donpeppe-horarios, atom-donpeppe-ubicacion, atom-donpeppe-promos, self-donpeppe

## Completion Condition

La persona recibió respuesta a su consulta, o expresó intención de reservar y se pasa al paso de reserva.
