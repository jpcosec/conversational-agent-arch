from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- metadata de los modelos del agente -----------------------------------
# Hay una unica Base declarativa (kb_agent.models_sql.identity.Base). Los
# demas modulos (session, reservas, recordatorios) importan esa MISMA Base
# y solo hace falta importarlos una vez para que sus tablas queden
# registradas en Base.metadata antes del autogenerate/upgrade.
from kb_agent.models_sql.identity import Base  # noqa: E402
from kb_agent.models_sql import session as _session_models  # noqa: E402,F401
from kb_agent.models_sql import reservas as _reservas_models  # noqa: E402,F401
from kb_agent.models_sql import recordatorios as _recordatorios_models  # noqa: E402,F401

target_metadata = Base.metadata


def _resolve_db_url() -> str:
    """URL de la base a migrar.

    Precedencia (igual que el resto del runtime, ver kb_agent/project_config.py):
      1. DATABASE_URL (env) — URL de SQLAlchemy completa, tal cual.
      2. CHAT_DB (env) — path a un sqlite; resuelto via ProjectConfig.
      3. project.config.yaml / defaults de ProjectConfig (chat_db_url).

    Nunca se hardcodea en alembic.ini: la app resuelve la ruta de la base
    en runtime (project_config.chat_db_url) y las migraciones deben apuntar
    a la MISMA base que use el proceso que las corre.
    """
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    from kb_agent.project_config import load_project_config

    return load_project_config().chat_db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = _resolve_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _resolve_db_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
