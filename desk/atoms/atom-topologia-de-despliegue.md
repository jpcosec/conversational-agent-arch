---
id: atom-topologia-de-despliegue
title: Topología de Despliegue (Modal)
five_wh_one_plus: what
tags:
- layer:ops
- role:boundary
provenance: architecture-audit
---

# Topología de Despliegue (Modal)

## Answer

Despliegue serverless en Modal (`deploy/modal_app.py`). El runtime completo (ASGI de FastAPI sirviendo las 5 UIs — `/`, `/flow`, `/mindmap`, `/users`, `/dashboard` — y los endpoints webhooks) se empaqueta junto con la Base de Conocimiento activa y se expone a internet, escalando desde cero. La infra sale del bloque `deploy` de project.config.yaml (`ProjectConfig.deploy` — `modal_app_name`, `gcp_secret_name`, `twilio_secret_name`, `min_containers`, `serve_timeout_s`), con `MODAL_APP_NAME` como override — así existe un endpoint dev separado (`MODAL_APP_NAME=kb-agent-runtime-dev modal deploy deploy/modal_app.py`) sin copiar el archivo. El Volume `<app>-data` (montado en `/data`) persiste el sqlite de sesiones, historial y UserTraits entre deploys; al arrancar `serve()` corre `_migrate_data_volume()` (alembic `upgrade head`, con stamp del baseline para bases pre-migraciones). Mantenimiento del volumen con `modal run deploy/modal_app.py::inspect_db` (sólo lectura) y `::clean_and_seed` (borra conversaciones y resiembra usuarios demo). La rama `production` + tag `release-YYYYMMDD-<sha>` registran lo desplegado (`deploy/release.sh`).
