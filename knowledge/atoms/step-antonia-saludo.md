---
id: step-antonia-saludo
title: Saludo inicial
atom_type: step
kind: interaccion_simple
summary: Saluda con calidez una sola vez; retoma por nombre a personas registradas y avanza a registro de estado, o deriva al onboarding si es nueva.
tags:
- conversation:steps.saludo
- system:laboratorio-chile
domain_ref: psp-selfix
---

# Saludo inicial

## Instructions

Saludar con calidez una sola vez al inicio. Si la persona ya esta registrada, retomar por su nombre y avanzar al registro de estado. Si es nueva o no reconocida, derivar al onboarding. No repetir el saludo en mensajes posteriores.

## Required Slots

si la persona ya esta registrada

## Handout Target

no aplica

## Tool

no aplica

## Allowed Transitions

conversation:steps.onboarding, conversation:steps.registro_estado, conversation:steps.journey_operativo, conversation:steps.derivacion_medinfo

## Grounding Atoms

self-antonia, style-antonia

## Completion Condition

Se determino si la persona es nueva (onboarding) o ya registrada (registro de estado).
