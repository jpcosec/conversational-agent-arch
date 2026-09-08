---
id: atom-un-negocio-por-rama
title: Un negocio por rama
five_wh_one_plus: what
tags:
- layer:business
- family:concepts
provenance: decision del owner, 2026-09-08
---

# Un negocio por rama

## Answer

Cada rama del repo es UN solo negocio; no existen negocios activos ni un switch entre ellos. project.config.yaml declara el negocio de la rama (nombre, kb_root, tools, deploy) y knowledge/ es su unica KB. Otro negocio es otra rama con su propia KB y su propio yaml (Antonia en dev/main, Vitali en su worktree); el runtime, kb_agent/, no lleva nada del negocio.
