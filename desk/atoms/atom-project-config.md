---
id: atom-project-config
title: "Configuraci\xF3n del Negocio"
five_wh_one_plus: what
tags:
- layer:knowledge
- role:boundary
provenance: architecture-audit
---

# Configuración del Negocio

## Answer

Archivo `project.config.yaml`. Separa el código duro del dominio del negocio. Configura dinámicamente la identidad visible del bot (name, slug), la ruta al store SLDB (`kb_root`), el modelo LLM subyacente y el mapeo de los handlers de tools permitidos.
