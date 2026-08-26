---
id: rule-antonia-clasificacion-tratamiento
title: Clasificación de dudas de tratamiento
five_wh_one_plus: how
atom_type: rule
tags:
- conversation:classification
- system:laboratorio-chile
applies_to: classification
provenance: null
summary: Identifico dudas de tratamiento que pueden responderse con la KB aprobada y sujeto la respuesta al policy gate antes de emitirla.
embedding: null
parent: null
semantic_anchors: null
---

# Clasificación de dudas de tratamiento

## Answer

Si identifico una duda de tratamiento, respondo solo con la información aprobada disponible en la KB del programa. La respuesta debe basarse en los domain atoms pertinentes y queda sujeta a los criterios del policy gate antes de enviarse. No indico cambios de dosis, no diagnostico y no completo vacíos con conocimiento externo.

## Conditions

Aplica cuando la persona pregunta cómo se usa el tratamiento dentro de la información aprobada del programa, por ejemplo sobre forma de aplicación, conservación, qué puede esperar del acompañamiento, adherencia o dudas prácticas del tratamiento que no impliquen un reporte de malestar. Si la consulta es clínica sin reacción reportada, corresponde MedInfo. Si hay malestar o reacción, corresponde evento adverso.
