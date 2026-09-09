---
id: step-antonia-saludo
title: Saludo inicial
atom_type: step
kind: interaccion_simple
tags:
- conversation:steps.saludo
- system:laboratorio-chile
domain_ref: psp-selfix
summary: Saluda con calidez una sola vez; retoma por nombre a personas registradas
  y avanza a registro de estado, o deriva al onboarding si es nueva.
---

# Saludo inicial

## Instructions

Saludar con calidez una sola vez al inicio. Si la persona ya esta registrada, retomar por su nombre y avanzar al registro de estado. Si es nueva o no reconocida, derivar al onboarding. Si dice que tiene una duda o consulta sin decir cual, preguntar cual es antes de derivar a ningun lado. No repetir el saludo en mensajes posteriores.

## Required Slots

si la persona ya esta registrada

## Handout Target



## Completion Condition

Se determino si la persona es nueva (onboarding) o ya registrada (registro de estado).
