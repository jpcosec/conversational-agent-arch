---
id: step-antonia-validacion-policy-gate
title: Validación policy gate — autochequeo post-draft
atom_type: step
kind: interaccion_simple
tags:
- conversation:steps.validacion_policy_gate
- system:laboratorio-chile
domain_ref: psp-selfix
summary: Antes de emitir una respuesta redactada, la autovalido contra los criterios regulatorios del gate y derivo si alguno falla.
embedding: null
parent: null
semantic_anchors: null
---

# Validación policy gate — autochequeo post-draft

## Instructions

Antes de emitir una respuesta redactada, autovalidarla contra los criterios del gate: no dosis, no diagnóstico, solo corpus aprobado, derivación cuando corresponde y sin prometer resultados. Si cualquier criterio falla, no emitir la respuesta y derivar el caso a revisión humana con el borrador y el motivo. Si todo cumple, la respuesta queda lista para emitirse fuera de este checkpoint.

## Required Slots

ninguno

## Handout Target

no aplica

## Tool

no aplica

## Allowed Transitions

conversation:steps.revision_humana

## Grounding Atoms

gate-antonia-dosis, gate-antonia-diagnostico, gate-antonia-corpus, gate-antonia-derivacion, gate-antonia-promesas

## Completion Condition

La respuesta redactada cumple todos los criterios del gate o el caso fue derivado a revisión humana por rechazo.
