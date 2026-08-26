---
id: step-antonia-booking
title: Seguimiento de aplicación y recompra
atom_type: step
tags:
- conversation:steps.booking
- system:laboratorio-chile
domain_ref: psp-selfix
---

# Seguimiento de aplicación y recompra

## Instructions

Recordar la aplicación semanal según el día de la persona. Preguntar cómo va con el tratamiento. Reforzar la adherencia. Recordar la recompra o renovación de receta antes de que se acabe el producto. Ayudar a prepararse para los controles médicos.

## Required Slots

día de aplicación, semanas de tratamiento, stock restante

## Allowed Transitions

conversation:steps.onboarding

## Grounding Atoms

atom-antonia-aplicacion, atom-antonia-recompra

## Completion Condition

La persona confirma que tiene su dosis y sabe cuándo será el próximo control.