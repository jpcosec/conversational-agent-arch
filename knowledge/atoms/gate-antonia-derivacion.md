---
id: gate-antonia-derivacion
title: Gate regulatorio — derivación correcta
atom_type: gate
tags:
- gate:derivacion
- system:laboratorio-chile
provenance: null
summary: Valido que la respuesta redactada derive efectivamente a farmacovigilancia o MedInfo/médico cuando el caso lo requiere.
embedding: null
parent: null
semantic_anchors: null
---

# Gate regulatorio — derivación correcta

## Criterion

Cuando el caso corresponde a derivación, la respuesta redactada efectivamente deriva al canal correcto: evento adverso a farmacovigilancia y consulta clínica a MedInfo o médico tratante.

## Approval Condition

Aprueba cuando la respuesta deja explícito el destino de derivación que corresponde y evita resolver por sí misma casos que deben pasar a farmacovigilancia, MedInfo, revisión humana o médico tratante.

## Rejection Action

Rechazar la respuesta, no emitirla y encolar a revisión humana con el borrador completo y el motivo de rechazo: omitió una derivación obligatoria o envió el caso a un canal incorrecto.
