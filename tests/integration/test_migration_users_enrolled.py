"""Migracion 07c82d1aebbf (users.enrolled): backfill sobre datos existentes.

Verifica, sobre una base SQLite real (no in-memory) con filas ya sembradas
antes de la migracion:
  - el upgrade agrega la columna y marca enrolled=True solo para los
    external_id que vienen del PSP (wa-*, web-anon-*); cualquier otro
    (p.ej. ui:* de la UI de desarrollo) queda en False.
  - no se pierden filas.
  - el downgrade revierte limpio (la columna desaparece, las filas quedan).
"""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

REPO_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(db_path: Path, monkeypatch) -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    return cfg


def test_upgrade_backfills_enrolled_by_external_id_prefix_and_downgrade_is_clean(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "migration.sqlite"
    cfg = _alembic_config(db_path, monkeypatch)

    # Esquema previo a la migracion bajo prueba (head anterior), con datos
    # ya existentes -- la base "con datos" que pide la verificacion.
    command.upgrade(cfg, "8df38d93ccd7")

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        for external_id, channel in [
            ("wa-56900000001", "whatsapp"),
            ("web-anon-1234", "web"),
            ("ui:devsession-1", "ui"),
        ]:
            conn.execute(
                text("INSERT INTO users (external_id, channel) VALUES (:e, :c)"),
                {"e": external_id, "c": channel},
            )
    engine.dispose()

    # Upgrade a head: agrega la columna y corre el backfill.
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.connect() as conn:
        rows = {
            row.external_id: row.enrolled
            for row in conn.execute(text("SELECT external_id, enrolled FROM users"))
        }
    engine.dispose()

    assert len(rows) == 3  # ninguna fila se perdio
    assert rows["wa-56900000001"] == 1
    assert rows["web-anon-1234"] == 1
    assert rows["ui:devsession-1"] == 0

    # Downgrade revierte limpio: la columna desaparece, las filas quedan.
    command.downgrade(cfg, "-1")

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM users")).scalar_one()
    engine.dispose()

    assert "enrolled" not in cols
    assert count == 3
