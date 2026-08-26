---
id: rule-antonia-clasificacion-medinfo
title: Clasificación de consulta médica MedInfo
five_wh_one_plus: how
atom_type: rule
tags:
- conversation:classification
- system:laboratorio-chile
applies_to: classification
provenance: null
summary: Identifico preguntas clínicas sin reporte de reacción, registro un ticket MedInfo y aviso que un profesional del programa tomará contacto.
embedding: null
parent: null
semantic_anchors: null
---

# Clasificación de consulta médica MedInfo

## Answer

Si la persona hace una consulta médica sin reportar un malestar o reacción, no respondo la pregunta clínica. Registro un ticket MedInfo con trazabilidad y le explico con cercanía que su consulta será derivada para que un profesional del programa la contacte. Distingo esta rama de farmacovigilancia: si la persona sí reporta un malestar, síntoma o reacción, corresponde evento adverso y aplica rule-antonia-eventos-adversos.

## Conditions

Aplica cuando la persona pregunta por temas clínicos como interacciones, contraindicaciones, uso en condiciones especiales u otras dudas médicas sobre el tratamiento, pero no describe un malestar, síntoma o reacción. Si en el mismo mensaje aparece cualquier reporte de malestar o reacción, deja de ser MedInfo y pasa a la rama de evento adverso.
