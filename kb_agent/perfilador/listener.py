from __future__ import annotations

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from kb_agent.pii.scrubber import scrub


@dataclass(frozen=True)
class TurnClosedEvent:
    user_id: int | None
    turn_text_scrubbed: str


class EventBus(ABC):
    @abstractmethod
    def publish_turn_closed(self, *, user_id: int | None, turn_text: str) -> TurnClosedEvent:
        """Publish a scrubbed turn-closed event without blocking the caller."""

    @abstractmethod
    async def get(self) -> TurnClosedEvent:
        """Read the next event for background processing."""

    @abstractmethod
    def task_done(self) -> None:
        """Acknowledge the last processed event."""


class InProcessEventBus(EventBus):
    def __init__(self, queue: asyncio.Queue[TurnClosedEvent] | None = None) -> None:
        self._queue: asyncio.Queue[TurnClosedEvent] = queue or asyncio.Queue()

    def publish_turn_closed(self, *, user_id: int | None, turn_text: str) -> TurnClosedEvent:
        event = TurnClosedEvent(user_id=user_id, turn_text_scrubbed=scrub(turn_text))
        self._queue.put_nowait(event)
        return event

    async def get(self) -> TurnClosedEvent:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()


Handler = Callable[[int | None, str], Awaitable[None] | None]


class AsyncProfilingListener:
    def __init__(
        self,
        *,
        event_bus: EventBus,
        handler: Handler,
        logger: logging.Logger | None = None,
        retry_backoff_seconds: Sequence[float] = (0.05, 0.1, 0.2),
    ) -> None:
        self.event_bus = event_bus
        self.handler = handler
        self.logger = logger or logging.getLogger(__name__)
        self.retry_backoff_seconds = tuple(retry_backoff_seconds)

    async def run(self) -> None:
        while True:
            event = await self.event_bus.get()
            try:
                await self._dispatch_with_retries(event)
            finally:
                self.event_bus.task_done()

    async def _dispatch_with_retries(self, event: TurnClosedEvent) -> None:
        max_attempts = len(self.retry_backoff_seconds) + 1
        for attempt in range(1, max_attempts + 1):
            try:
                await self._invoke_handler(event)
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception(
                    "Perfilador listener handler failed",
                    extra={
                        "user_id": event.user_id,
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                    },
                )
                if attempt >= max_attempts:
                    return
                await asyncio.sleep(self.retry_backoff_seconds[attempt - 1])

    async def _invoke_handler(self, event: TurnClosedEvent) -> None:
        outcome = self.handler(event.user_id, event.turn_text_scrubbed)
        if inspect.isawaitable(outcome):
            await outcome


def publish_turn_closed(event_bus: EventBus, *, user_id: int | None, turn_text: str) -> TurnClosedEvent:
    """Convenience wrapper for router producers.

    The scrubber runs inline before the event is handed off to the asynchronous
    listener, so the profilador never receives raw PII.
    """

    return event_bus.publish_turn_closed(user_id=user_id, turn_text=turn_text)
