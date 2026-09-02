"""Migracion d4e5f6a7b8c9 (inbound_messages + backfill users.phone).

Sobre una base SQLite real con usuarios creados ANTES de identity_key='phone'
(phone NULL): el upgrade crea inbound_messages con su UNIQUE de proveedor y
rellena users.phone desde el external_id para los canales con telefono; el
downgrade deja users intacto y elimina la tabla.
"""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

REPO_ROOT = Path(__file__).resolve().parents[2]
REVISION = "d4e5f6a7b8c9"
PREVIOUS = "c1a2b3d4e5f6"


def _alembic_config(db_path: Path, monkeypatch) -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    return cfg


def test_upgrade_creates_inbound_messages_and_backfills_phone(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "migration.sqlite"
    cfg = _alembic_config(db_path, monkeypatch)
    command.upgrade(cfg, PREVIOUS)

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        for external_id, channel in [
            ("whatsapp:+56 9 1111 1111", "whatsapp"),   # telefono con espacios
            ("sms:+56922222222", "sms"),
            ("+56933333333", "unknown"),                # SMS pelado viejo: sin prefijo
            ("ui:devsession-1", "ui"),
            ("web-anon-1234", "web"),
        ]:
            conn.execute(text("INSERT INTO users (external_id, channel) VALUES (:e, :c)"),
                         {"e": external_id, "c": channel})
    engine.dispose()

    command.upgrade(cfg, REVISION)

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.connect() as conn:
        phones = {r.external_id: r.phone for r in conn.execute(text("SELECT external_id, phone FROM users"))}
    assert phones == {
        "whatsapp:+56 9 1111 1111": "+56911111111",
        "sms:+56922222222": "+56922222222",
        "+56933333333": None,      # sin prefijo de canal no se infiere nada
        "ui:devsession-1": None,
        "web-anon-1234": None,
    }
    assert "inbound_messages" in inspect(engine).get_table_names()

    # UNIQUE(provider, provider_message_id): el reintento de Twilio choca.
    with engine.begin() as conn:
        ins = text("INSERT INTO inbound_messages (provider, provider_message_id, channel, external_id, "
                   "body, num_media, payload, status) VALUES ('twilio', :m, 'sms', 'sms:+1', '', 0, '{}', 'received')")
        conn.execute(ins, {"m": "SM1"})
    try:
        with engine.begin() as conn:
            conn.execute(ins, {"m": "SM1"})
        raised = False
    except IntegrityError:
        raised = True
    assert raised
    engine.dispose()

    command.downgrade(cfg, "-1")
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    assert "inbound_messages" not in inspect(engine).get_table_names()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM users")).scalar_one() == 5
    engine.dispose()
