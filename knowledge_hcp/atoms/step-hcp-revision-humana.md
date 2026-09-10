---
id: step-hcp-revision-humana
title: Revisión humana
atom_type: step
kind: interaccion_simple
tags:
- conversation:steps.revision_humana
- system:teva-hcp
domain_ref: null
summary: Entrega de la conversación a revisión humana cuando una respuesta no pasó
  la validación; el médico recibe un mensaje de espera sin el borrador rechazado.
---

# Revisión humana

## Instructions

Cuando una respuesta no pasó la validación: no enviar el borrador rechazado. Decirle al médico que su consulta requiere revisión y que el equipo le responderá a la brevedad. Entregar la conversación con el borrador y el motivo del rechazo para que una persona la continúe.

## Required Slots

ninguno

## Completion Condition