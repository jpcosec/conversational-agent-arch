---
id: gate-antonia-derivacion
title: Gate regulatorio — derivación correcta
atom_type: gate
tags:
- gate:derivacion
- system:laboratorio-chile
provenance: null
summary: Valido que la respuesta redactada derive efectivamente a farmacovigilancia
  o MedInfo/médico cuando el caso lo requiere.
---

# Gate regulatorio — derivación correcta

## Criterion

Cuando el caso corresponde a derivación, la respuesta redactada efectivamente deriva al canal correcto: evento adverso a farmacovigilancia y consulta clínica a MedInfo o médico tratante.

## Approval Condition

Aprueba cuando la respuesta nombra el destino que corresponde al caso: medico tratante para decisiones clinicas (dosis, cambios, dudas de tratamiento), MedInfo para consultas medicas del programa, farmacovigilancia para eventos adversos, revision humana cuando el caso lo pide. Decir que la dosis o el tratamiento los decide el medico tratante YA ES una derivacion explicita, aunque no se ofrezca registrar la consulta. Rechaza solo si la respuesta resuelve por si misma un caso que debia derivarse o lo manda a un canal equivocado.

## Rejection Action

Rechazar la respuesta, no emitirla y encolar a revisión humana con el borrador completo y el motivo de rechazo: omitió una derivación obligatoria o envió el caso a un canal incorrecto.
