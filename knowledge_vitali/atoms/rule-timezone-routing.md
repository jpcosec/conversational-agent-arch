---
id: rule-timezone-routing
title: 'Regla: zona horaria y oficina'
five_wh_one_plus: how
atom_type: rule
tags:
- domain:booking
- agent:conversation-rule
- system:vitali
applies_to: null
provenance: null
summary: 'Las herramientas de agenda usan por defecto calendario ''primary'' y zona
  America/Santiago. Los leads pueden estar en Mexico, Colombia, Bolivia o USA (oficina
  Doral). Regla: confirma'
embedding: null
parent: null
semantic_anchors: null
---

# Regla: zona horaria y oficina

## Answer

Las herramientas de agenda usan por defecto calendario 'primary' y zona America/Santiago. Los leads pueden estar en Mexico, Colombia, Bolivia o USA (oficina Doral). Regla: confirmar temprano el pais/ciudad del lead, ofrecer horarios en su zona local y derivar a la oficina mas cercana (Santiago para Chile/LatAm sur; Doral para USA/norte). PENDIENTE con el negocio: si existen calendarios separados por oficina; hasta entonces usar primary pero indicar la zona horaria explicitamente.

## Conditions

El lead puede estar en un pais o zona horaria distinta a Chile.
