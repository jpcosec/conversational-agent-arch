---
id: atom-deploy-dev-y-mantenimiento-del-volumen
title: Deploy dev y mantenimiento del volumen
five_wh_one_plus: how
tags:
- layer:ops
- role:boundary
- topic:deploy
provenance: deploy/README.md
---

# Deploy dev y mantenimiento del volumen

## Answer

Para un endpoint de desarrollo separado no se copia deploy/modal_app.py — el nombre de la app sale de la variable `MODAL_APP_NAME` (prioridad sobre `deploy.modal_app_name` del yaml) y el volumen es `<app>-data`. `MODAL_APP_NAME=kb-agent-runtime-dev modal deploy deploy/modal_app.py` crea la app `kb-agent-runtime-dev` y el Volume `kb-agent-runtime-dev-data` (montado en `/data`, con el sqlite `ui-chat.sqlite` de sesiones, historial y UserTraits), con el mismo secret GCP; logs con `modal app logs kb-agent-runtime-dev`. El override viaja a la imagen (`.env({"MODAL_APP_NAME": APP_NAME})`) porque el contenedor re-importa el módulo y debe resolver el mismo app/volumen; modal_app.py resuelve la raíz del repo también dentro del contenedor (`_CFG_ROOT` cae a `REMOTE_APP_DIR=/root/app` cuando no encuentra `kb_agent/` al lado). Mantenimiento del sqlite del volumen con funciones que viven en el mismo archivo (Modal no monta deploy/ como paquete) — `modal run deploy/modal_app.py::inspect_db` (sólo lectura — tablas, usuarios, primeros mensajes) y `modal run deploy/modal_app.py::clean_and_seed` (BORRA conversaciones y resiembra los usuarios demo; el esquema lo deja alembic al arrancar `serve`). Detalle de secrets, imagen y qué se empaqueta en deploy/README.md.
