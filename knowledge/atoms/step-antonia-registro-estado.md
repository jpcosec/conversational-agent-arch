---
id: step-antonia-registro-estado
title: Registro de estado — como va el tratamiento
atom_type: step
kind: obtencion_datos
tags:
- conversation:steps.registro_estado
- system:laboratorio-chile
domain_ref: psp-selfix
summary: Pregunta con empatia como va la semana, registra dosis y estado; deriva a
  evento adverso si hay sintomas, o avanza a agendar recordatorio si todo va bien.
---

# Registro de estado — como va el tratamiento

## Instructions

Preguntar con empatia como va la persona esta semana. Registrar en que semana va, si aplico su dosis y como se ha sentido. Validar emociones sin valorar ni calificar lo que cuenta: un cambio de apetito, de peso o de animo se anota ('gracias por contarme, lo registro') y no se presenta como beneficio, mejora ni senal de nada. Si reporta cualquier sintoma o reaccion adversa, derivar de inmediato al paso de evento adverso. Si hace una pregunta medica, derivar a MedInfo. Si resulta que no esta inscrita en el programa, pasar a enrolamiento. Si todo va bien, avanzar a agendar el recordatorio.

## Required Slots

semana de tratamiento, si aplico la dosis, como se ha sentido

## Handout Target



## Completion Condition

Quedo registrado el estado y se determino si hay un sintoma a derivar o si se avanza a agendar.
