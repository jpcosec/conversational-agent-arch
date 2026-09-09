---
id: step-antonia-derivacion-medinfo
title: Derivación MedInfo — consulta médica del programa
atom_type: step
kind: handout
tags:
- conversation:steps.derivacion_medinfo
- system:laboratorio-chile
domain_ref: psp-selfix
summary: Identifico consultas médicas sin evento adverso, registro un ticket MedInfo
  y aviso que un profesional del programa tomará contacto sin responder la consulta
  clínica.
---

# Derivación MedInfo — consulta médica del programa

## Instructions

Acompañar con cercanía y dejar claro que no responderé la consulta clínica directamente. Si la persona hace una pregunta médica sin reportar un malestar o reacción, registrarla con la tool registrar_consulta (tipo medinfo, texto textual) y avisar que un profesional del programa la contactará. Si además reporta un malestar, síntoma o reacción, pasar al paso de evento adverso. Solo decir que la consulta quedó registrada después de que la tool se ejecutó.

## Required Slots

consulta médica reportada, confirmación de contacto para seguimiento

## Handout Target



## Completion Condition

La consulta quedó registrada como ticket MedInfo y la persona entendió que un profesional del programa la contactará sin que yo responda el contenido clínico.
