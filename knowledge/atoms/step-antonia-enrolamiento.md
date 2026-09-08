---
id: step-antonia-enrolamiento
title: Enrolamiento — inscripción al programa
atom_type: step
kind: llamado_tool
tags:
- conversation:steps.enrolamiento
- system:laboratorio-chile
domain_ref: psp-selfix
summary: Inscribe a personas no reconocidas pidiendo nombre, teléfono y correo, o
  las deriva a un profesional del programa si prefieren no inscribirse por acá.
---

# Enrolamiento — inscripción al programa

## Instructions

Cuando la persona no está inscrita en el programa, explicar brevemente en qué consiste el acompañamiento y ofrecer inscribirla. Pedir, una pregunta a la vez, su nombre, un teléfono de contacto y un correo electrónico. Explicar con calidez que esos datos los usa el equipo del programa para contactarla y hacerle seguimiento, no para tomar decisiones clínicas. Si la persona prefiere no entregar sus datos por acá, no tiene claro si le corresponde el programa, o pide hablar primero con alguien, derivar sin insistir. Al tener nombre, teléfono y correo confirmados, ejecutar la tool registrar_enrolamiento. El médico tratante sigue siendo la autoridad clínica; inscribirse en el acompañamiento no reemplaza esa relación.

## Required Slots

nombre de la persona, teléfono de contacto, correo electrónico

## Handout Target



## Completion Condition

La tool registrar_enrolamiento se ejecutó con nombre, teléfono y correo confirmados, o la persona fue derivada a un profesional del programa sin completar la inscripción.
