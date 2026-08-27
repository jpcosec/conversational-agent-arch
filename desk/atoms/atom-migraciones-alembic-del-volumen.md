---
id: atom-migraciones-alembic-del-volumen
title: Migraciones alembic del volumen
five_wh_one_plus: how
tags:
- layer:ops
- role:data
- topic:alembic
provenance: deploy/modal_app.py
---

# Migraciones alembic del volumen

## Answer

`_migrate_data_volume()` en deploy/modal_app.py corre al arrancar `serve()`, antes de importar la app. Motivo — el Volume `/data` persiste el sqlite entre deploys, así que una base creada por un deploy viejo conserva el esquema viejo, y `create_all()` crea tablas que faltan pero NUNCA altera una existente (el primer turno tras un cambio de modelo reventaba con "no such column"). La función usa las migraciones de `alembic/` (versiones en `alembic/versions/`, config en `alembic.ini` copiados a la imagen, `DATABASE_URL` apuntando a `CHAT_DB`) y distingue tres casos — la base no existe => `upgrade head` la crea completa; existe sin tabla `alembic_version` (creada con `create_all()` antes de que hubiera migraciones) => `command.stamp(cfg, BASELINE_REVISION)` con la primera revisión (`b77575dcdf9b`, baseline del esquema) y después `upgrade head`; existe versionada => `upgrade head`. Si falla no frena el arranque — loguea la excepción y el turno fallará de forma visible. En local, `kb_agent/db_check.py` (`check_db_revision`) compara la revisión de la base contra HEAD de forma no bloqueante.
