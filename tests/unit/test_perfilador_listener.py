from __future__ import annotations

import asyncio
import contextlib

from kb_agent.perfilador.listener import AsyncProfilingListener, InProcessEventBus, publish_turn_closed
from kb_agent.pii.scrubber import scrub


def test_publish_turn_closed_scrubs_inline_and_dispatches_to_handler():
    async def scenario() -> None:
        event_bus = InProcessEventBus()
        received: list[tuple[int | None, str]] = []
        handled = asyncio.Event()

        async def handler(user_id: int | None, turn_text: str) -> None:
            received.append((user_id, turn_text))
            handled.set()

        listener = AsyncProfilingListener(
            event_bus=event_bus,
            handler=handler,
            retry_backoff_seconds=(0.001,),
        )
        worker = asyncio.create_task(listener.run())

        try:
            raw_turn = "Hola, soy Juan Pérez y mi correo es juan@example.com"
            published = publish_turn_closed(event_bus, user_id=7, turn_text=raw_turn)

            await asyncio.wait_for(handled.wait(), timeout=1)

            expected_turn = scrub(raw_turn)
            assert published.turn_text_scrubbed == expected_turn
            assert received == [(7, expected_turn)]
            assert "juan@example.com" not in received[0][1]
        finally:
            worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker

    asyncio.run(scenario())


def test_handler_exception_does_not_propagate_to_producer():
    async def scenario() -> None:
        event_bus = InProcessEventBus()
        attempts: list[tuple[int | None, str]] = []
        handled = asyncio.Event()

        async def flaky_handler(user_id: int | None, turn_text: str) -> None:
            attempts.append((user_id, turn_text))
            if len(attempts) == 1:
                raise RuntimeError("boom")
            handled.set()

        listener = AsyncProfilingListener(
            event_bus=event_bus,
            handler=flaky_handler,
            retry_backoff_seconds=(0.001,),
        )
        worker = asyncio.create_task(listener.run())

        try:
            raw_turn = "Mi teléfono es +56 9 1234 5678"
            published = publish_turn_closed(event_bus, user_id=9, turn_text=raw_turn)

            await asyncio.wait_for(handled.wait(), timeout=1)

            assert len(attempts) == 2
            assert attempts[0] == attempts[1] == (9, published.turn_text_scrubbed)
        finally:
            worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker

    asyncio.run(scenario())
