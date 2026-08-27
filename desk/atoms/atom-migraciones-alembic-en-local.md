---
id: atom-migraciones-alembic-en-local
title: Migraciones alembic en local
five_wh_one_plus: how
tags:
- layer:ops
- topic:alembic
provenance: alembic/env.py
---

# Migraciones alembic en local

## Answer

El schema SQL vive en `kb_agent/models_sql/` (una sola `Base` declarativa — `identity.py` la define; `session.py`, `reservas.py` y `recordatorios.py` la importan). El `Orchestrator` corre `Base.metadata.create_all()` al arrancar, y eso crea tablas que faltan pero nunca altera una tabla existente — si un modelo gana o cambia una columna, una base vieja se queda atrás en silencio y explota recién en el primer INSERT/SELECT real con un `OperationalError` de `no such column` opaco (así se descubrió el problema — en `runs/local-chat.sqlite` faltaban `flow_node`/`flow_slots` de `SessionState`). Por eso el schema se versiona con Alembic (`alembic/`, `alembic.ini`). `alembic/env.py` no hardcodea la URL de la base — la resuelve en runtime con la misma precedencia que kb_agent/project_config.py, `DATABASE_URL` (env, URL completa) > `CHAT_DB` (env, path a sqlite) > `project.config.yaml` / defaults de `ProjectConfig`; expone el `target_metadata` combinado (importa `identity`, `session`, `reservas` y `recordatorios` para que sus tablas queden en la única `Base.metadata`) y habilita `render_as_batch=True`, imprescindible porque SQLite no soporta `ALTER COLUMN` nativo (Alembic lo emula recreando la tabla). Crear una migración nueva (después de tocar un modelo en `kb_agent/models_sql/`) — `DATABASE_URL="sqlite:////ruta/a/una/base/vacia/o/de/prueba.sqlite" python -m alembic revision --autogenerate -m "descripción corta"`; nunca apuntar el autogenerate a `runs/local-chat.sqlite` ni a ninguna base con datos reales (compara el modelo contra ESA base, conviene que arranque vacía o ya al día), y siempre revisar a mano el archivo generado en `alembic/versions/` antes de commitear (el autogenerate a veces mete constraints o índices que no corresponden). Aplicar migraciones pendientes — `CHAT_DB=runs/local-chat.sqlite python -m alembic upgrade head` (o `DATABASE_URL=sqlite:///runs/local-chat.sqlite ...`; sin ninguna de las dos, toma la base resuelta por `project.config.yaml`). Base preexistente que ya tiene el esquema al día (creada con `create_all()` antes de que existieran las migraciones, como `runs/local-chat.sqlite`) — no correr `upgrade` (sin `alembic_version` intentaría recrear tablas que ya existen y fallaría); marcarla como al día sin ejecutar DDL con `CHAT_DB=runs/local-chat.sqlite python -m alembic stamp head`. Chequeo automático al arrancar — `kb_agent/cli.py` llama a `kb_agent.db_check.check_db_revision()` antes de crear el `Orchestrator` y, si la base no está en `head` (o no tiene `alembic_version`), imprime un `[WARNING]` con el diagnóstico y el comando a correr; nunca frena el arranque ni lanza excepción.
