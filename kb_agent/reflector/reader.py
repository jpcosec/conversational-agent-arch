from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from kb_agent.models_sql.session import ChatHistory

BATCH_SIZE = 500
CRON_TRIGGER = "cron"


@dataclass(frozen=True)
class ReflectorHistoryRow:
    id: int
    user_id: int
    role: str
    content: str
    created_at: datetime


@dataclass
class ReaderCheckpoint:
    last_created_at: datetime | None = None


class CheckpointStore(Protocol):
    def load(self) -> ReaderCheckpoint:
        ...

    def save(self, checkpoint: ReaderCheckpoint) -> None:
        ...


class InMemoryCheckpointStore:
    def __init__(self, checkpoint: ReaderCheckpoint | None = None) -> None:
        self._checkpoint = checkpoint or ReaderCheckpoint()

    def load(self) -> ReaderCheckpoint:
        return ReaderCheckpoint(last_created_at=self._checkpoint.last_created_at)

    def save(self, checkpoint: ReaderCheckpoint) -> None:
        self._checkpoint = ReaderCheckpoint(last_created_at=checkpoint.last_created_at)


class ReflectorBatchReaderJob:
    """Read scrubbed chat history in paginated batches from a cron-triggered job."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        checkpoint_store: CheckpointStore,
        *,
        batch_size: int = BATCH_SIZE,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
        self._session_factory = session_factory
        self._checkpoint_store = checkpoint_store
        self._batch_size = batch_size

    def run(self, *, trigger: str = CRON_TRIGGER) -> list[ReflectorHistoryRow]:
        if trigger != CRON_TRIGGER:
            raise ValueError("ReflectorBatchReaderJob must be triggered by cron")

        checkpoint = self._checkpoint_store.load()
        processed: list[ReflectorHistoryRow] = []

        while True:
            with self._session_factory() as session:
                rows = list(self._fetch_batch(session, checkpoint.last_created_at))

            if not rows:
                break

            processed.extend(self._to_payload(row) for row in rows)
            checkpoint.last_created_at = rows[-1].created_at
            self._checkpoint_store.save(checkpoint)

        return processed

    def _fetch_batch(self, session: Session, after_created_at: datetime | None) -> list[ChatHistory]:
        statement = (
            select(ChatHistory)
            .where(ChatHistory.pii_scrubbed.is_(True))
            .order_by(ChatHistory.created_at.asc(), ChatHistory.id.asc())
            .limit(self._batch_size)
        )
        if after_created_at is not None:
            statement = statement.where(ChatHistory.created_at > after_created_at)
        return list(session.scalars(statement))

    @staticmethod
    def _to_payload(row: ChatHistory) -> ReflectorHistoryRow:
        return ReflectorHistoryRow(
            id=row.id,
            user_id=row.user_id,
            role=row.role,
            content=row.content,
            created_at=row.created_at,
        )
