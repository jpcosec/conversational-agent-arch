from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kb_agent.models_sql.identity import Base, Users
from kb_agent.models_sql.session import ChatHistory
from kb_agent.reflector.reader import InMemoryCheckpointStore, ReflectorBatchReaderJob


def _build_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return lambda: Session(engine)


def _seed_user(session: Session, external_id: str = "user-reflector") -> Users:
    user = Users(external_id=external_id, channel="web")
    session.add(user)
    session.flush()
    return user


def test_reader_returns_only_scrubbed_rows_from_mixed_history() -> None:
    session_factory = _build_session_factory()
    with session_factory() as session:
        user = _seed_user(session)
        base_time = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
        session.add_all(
            [
                ChatHistory(
                    user_id=user.id,
                    role="user",
                    content="hola limpio 1",
                    pii_scrubbed=True,
                    created_at=base_time,
                ),
                ChatHistory(
                    user_id=user.id,
                    role="user",
                    content="correo sin scrub",
                    pii_scrubbed=False,
                    created_at=base_time + timedelta(seconds=1),
                ),
                ChatHistory(
                    user_id=user.id,
                    role="assistant",
                    content="hola limpio 2",
                    pii_scrubbed=True,
                    created_at=base_time + timedelta(seconds=2),
                ),
            ]
        )
        session.commit()

    reader = ReflectorBatchReaderJob(
        session_factory,
        InMemoryCheckpointStore(),
        batch_size=1,
    )

    rows = reader.run(trigger="cron")

    assert [row.content for row in rows] == ["hola limpio 1", "hola limpio 2"]
    assert [row.role for row in rows] == ["user", "assistant"]


def test_reader_checkpoint_avoids_reprocessing_on_second_run() -> None:
    session_factory = _build_session_factory()
    checkpoint_store = InMemoryCheckpointStore()
    with session_factory() as session:
        user = _seed_user(session, external_id="user-checkpoint")
        base_time = datetime(2026, 8, 25, 13, 0, tzinfo=timezone.utc)
        session.add_all(
            [
                ChatHistory(
                    user_id=user.id,
                    role="user",
                    content="historial 1",
                    pii_scrubbed=True,
                    created_at=base_time,
                ),
                ChatHistory(
                    user_id=user.id,
                    role="assistant",
                    content="historial 2",
                    pii_scrubbed=True,
                    created_at=base_time + timedelta(seconds=1),
                ),
                ChatHistory(
                    user_id=user.id,
                    role="user",
                    content="historial 3",
                    pii_scrubbed=True,
                    created_at=base_time + timedelta(seconds=2),
                ),
            ]
        )
        session.commit()

    reader = ReflectorBatchReaderJob(session_factory, checkpoint_store, batch_size=2)

    first_run = reader.run(trigger="cron")
    second_run = reader.run(trigger="cron")

    assert [row.content for row in first_run] == ["historial 1", "historial 2", "historial 3"]
    assert second_run == []
    assert checkpoint_store.load().last_created_at == first_run[-1].created_at
