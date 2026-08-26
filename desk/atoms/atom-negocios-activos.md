---
id: atom-negocios-activos
title: Negocios Activos (KBs)
five_wh_one_plus: what
tags:
- layer:business
- family:concepts
provenance: architecture-audit
---

# Negocios Activos (KBs)

## Answer

El sistema soporta múltiples negocios aislados. Actualmente conviven dos KBs principales: 'Antonia' (asistente clínico, producción) que vive en `knowledge/`, y 'Don Peppe' (pizzería, pruebas) que vive en `tests/knowledge/`. El archivo `project.config.yaml` actúa como el switch que define cuál está activo.
