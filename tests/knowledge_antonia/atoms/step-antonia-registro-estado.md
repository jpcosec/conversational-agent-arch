---
id: step-antonia-registro-estado
title: Registro de estado — como va el tratamiento
atom_type: step
kind: obtencion_datos
summary: Pregunta con empatia como va la semana, registra dosis y estado; deriva a evento adverso si hay sintomas, o avanza a agendar recordatorio si todo va bien.
tags:
- conversation:steps.registro_estado
- system:laboratorio-chile
domain_ref: psp-selfix
---

# Registro de estado — como va el tratamiento

## Instructions

Preguntar con empatia como va la persona esta semana. Registrar en que semana va, si aplico su dosis y como se ha sentido. Validar emociones. Si reporta cualquier sintoma o reaccion adversa, derivar de inmediato al paso de evento adverso. Si todo va bien, avanzar a agendar el recordatorio.

## Required Slots

semana de tratamiento, si aplico la dosis, como se ha sentido

## Handout Target

no aplica

## Tool

no aplica

## Allowed Transitions

conversation:steps.evento_adverso, conversation:steps.agendar_recordatorio

## Grounding Atoms

atom-antonia-aplicacion, atom-antonia-primeras-semanas, rule-antonia-eventos-adversos

## Completion Condition

Quedo registrado el estado y se determino si hay un sintoma a derivar o si se avanza a agendar.
