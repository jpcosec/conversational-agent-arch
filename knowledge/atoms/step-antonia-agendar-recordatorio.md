---
id: step-antonia-agendar-recordatorio
title: Agendar recordatorio de aplicacion
atom_type: step
kind: llamado_tool
summary: Confirma dia y hora del recordatorio semanal y llama a la tool agendar_recordatorio; luego avanza al seguimiento de recompra.
tags:
- conversation:steps.agendar_recordatorio
- system:laboratorio-chile
domain_ref: psp-selfix
---

# Agendar recordatorio de aplicacion

## Instructions

Confirmar el dia y hora del recordatorio semanal. Llamar a la tool agendar_recordatorio solo cuando se tienen confirmados dia y hora. Explicar que le llegara un mensaje ese dia. Luego avanzar al seguimiento de recompra.

## Required Slots

dia de recordatorio, hora de recordatorio

## Handout Target

no aplica

## Tool

agendar_recordatorio

## Allowed Transitions

conversation:steps.recompra

## Grounding Atoms

atom-antonia-aplicacion

## Completion Condition

La tool se ejecuto correctamente y la persona sabe cuando recibira su recordatorio.
