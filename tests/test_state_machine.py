import logging

import pytest

from kb_chat_ui.state_machine import DEBOUNCE_MS, CronTriggerPayload, RouterNode, RouterStateMachine


def test_user_turn_flows_idle_eval_draft_idle():
    compiler_calls = []
    drafted_contexts = []

    def compile_context(**payload):
        compiler_calls.append(payload)
        return {
            "scenario": payload["scenario"],
            "question": payload["question"],
            "user_id": payload["user_id"],
            "is_empty": False,
        }

    def draft_response(compiled_context):
        drafted_contexts.append(compiled_context)
        return "respuesta"

    sm = RouterStateMachine(compile_context=compile_context, draft_response=draft_response)

    result = sm.handle_user_message("hola", user_id=7)

    assert result.response == "respuesta"
    assert compiler_calls == [
        {
            "question": "hola",
            "user_id": 7,
            "scenario": None,
            "trigger": "user",
        }
    ]
    assert drafted_contexts == [
        {
            "scenario": None,
            "question": "hola",
            "user_id": 7,
            "is_empty": False,
        }
    ]
    assert sm.current_node is RouterNode.IDLE
    assert sm.state_trace == [
        RouterNode.IDLE,
        RouterNode.EVALUATING_CONTEXT,
        RouterNode.DRAFTING_RESPONSE,
        RouterNode.IDLE,
    ]


@pytest.mark.parametrize("start_node", [RouterNode.EVALUATING_CONTEXT, RouterNode.DRAFTING_RESPONSE, RouterNode.BUFFERING, RouterNode.WAITING_TOOL, RouterNode.BREAKPOINT_MISS])
def test_cron_trigger_is_dropped_when_not_idle(caplog, start_node):
    compiler_calls = []

    def compile_context(**payload):
        compiler_calls.append(payload)
        return {"is_empty": False}

    sm = RouterStateMachine(compile_context=compile_context, draft_response=lambda _: "ok")
    sm.current_node = start_node
    sm.state_trace = [RouterNode.IDLE, start_node]

    with caplog.at_level(logging.INFO):
        result = sm.handle_cron_trigger(CronTriggerPayload(scenario="pizza", user_id=42))

    assert result is None
    assert sm.current_node is start_node
    assert sm.state_trace == [RouterNode.IDLE, start_node]
    assert sm.pending_events == []
    assert compiler_calls == []
    assert "Dropping CRON trigger because router is not idle" in caplog.text


def test_cron_trigger_in_idle_propagates_scenario_to_compiler():
    compiler_calls = []

    def compile_context(**payload):
        compiler_calls.append(payload)
        return {
            "scenario": payload["scenario"],
            "question": payload["question"],
            "user_id": payload["user_id"],
            "is_empty": False,
        }

    sm = RouterStateMachine(compile_context=compile_context, draft_response=lambda _: "proactive")

    result = sm.handle_cron_trigger(CronTriggerPayload(scenario="pizza", user_id=9))

    assert result is not None
    assert result.compiled_context["scenario"] == "pizza"
    assert compiler_calls == [
        {
            "question": "",
            "user_id": 9,
            "scenario": "pizza",
            "trigger": "cron",
        }
    ]
    assert sm.state_trace == [
        RouterNode.IDLE,
        RouterNode.EVALUATING_CONTEXT,
        RouterNode.DRAFTING_RESPONSE,
        RouterNode.IDLE,
    ]


def test_debounce_enters_buffering_and_fires_once_for_burst_messages():
    compiler_calls = []
    clock = {"now": 0}

    def compile_context(**payload):
        compiler_calls.append(payload)
        return {
            "question": payload["question"],
            "user_id": payload["user_id"],
            "scenario": payload["scenario"],
            "is_empty": False,
        }

    sm = RouterStateMachine(
        compile_context=compile_context,
        draft_response=lambda _: "respuesta",
        debounce_enabled=True,
        now_ms=lambda: clock["now"],
    )

    assert sm.handle_user_message("m1", user_id=7) is None
    assert sm.current_node is RouterNode.BUFFERING
    assert sm.session_state.buffer["debounce"] == ["m1"]
    first_deadline = sm._debounce_deadline_ms
    assert first_deadline == DEBOUNCE_MS

    for index, at_ms in enumerate([100, 250, 400, 700], start=2):
        clock["now"] = at_ms
        assert sm.handle_user_message(f"m{index}", user_id=7) is None
        assert sm.current_node is RouterNode.BUFFERING
        assert sm._debounce_deadline_ms == at_ms + DEBOUNCE_MS

    clock["now"] = 1699
    assert sm.process_timeouts() is None
    assert compiler_calls == []

    clock["now"] = 1700
    result = sm.process_timeouts()

    assert result is not None
    assert compiler_calls == [
        {
            "question": "m1 m2 m3 m4 m5",
            "user_id": 7,
            "scenario": None,
            "trigger": "user",
        }
    ]
    assert sm.current_node is RouterNode.IDLE
    assert sm.session_state.buffer["debounce"] == []
    assert sm.process_timeouts() is None
    assert len(compiler_calls) == 1


def test_debounce_isolated_message_flushes_after_exactly_one_second():
    compiler_calls = []
    clock = {"now": 0}

    def compile_context(**payload):
        compiler_calls.append(payload)
        return {"question": payload["question"], "is_empty": False}

    sm = RouterStateMachine(
        compile_context=compile_context,
        draft_response=lambda _: "ok",
        debounce_enabled=True,
        now_ms=lambda: clock["now"],
    )

    assert sm.handle_user_message("hola", user_id=3) is None
    assert sm.current_node is RouterNode.BUFFERING

    clock["now"] = DEBOUNCE_MS - 1
    assert sm.process_timeouts() is None
    assert compiler_calls == []
    assert sm.current_node is RouterNode.BUFFERING

    clock["now"] = DEBOUNCE_MS
    result = sm.process_timeouts()

    assert result is not None
    assert compiler_calls == [
        {
            "question": "hola",
            "user_id": 3,
            "scenario": None,
            "trigger": "user",
        }
    ]
    assert sm.current_node is RouterNode.IDLE
    assert sm.session_state.buffer["debounce"] == []
