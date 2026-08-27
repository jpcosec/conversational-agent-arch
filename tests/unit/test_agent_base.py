"""Tests de ``kb_agent.agents.base.Agent``, todos sin red (cliente fake).

Cubre el contrato minimo de la fase 2.1: system_instruction combinado,
include_contents, encadenado de before/after_model (cortocircuito y
reescritura), output_schema parseado a Pydantic, y veto/reescritura de tools
por before/after_tool_callback.
"""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from kb_agent.agents import Agent, LlmRequest, LlmResponse, Tool, ToolCall


class _Resp:
    """Respuesta cruda minima, con la forma que expone google-genai."""

    def __init__(self, text: str = "", parsed: Any = None, function_calls: list[Any] | None = None) -> None:
        self.text = text
        self.parsed = parsed
        self.function_calls = function_calls or []


class _FakeModels:
    def __init__(self, responder) -> None:
        self._responder = responder
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> _Resp:
        self.calls.append(kwargs)
        return self._responder(kwargs)


class _FakeClient:
    def __init__(self, responder=None, text: str = "ok") -> None:
        if responder is None:
            def responder(_kwargs: dict[str, Any]) -> _Resp:
                return _Resp(text=text)
        self.models = _FakeModels(responder)

    @property
    def calls(self) -> list[dict[str, Any]]:
        return self.models.calls


class Bundle(BaseModel):
    doc_id: str
    motivo: str


def make_agent(**overrides: Any) -> tuple[Agent, _FakeClient]:
    client = overrides.pop("client", None) or _FakeClient()
    defaults: dict[str, Any] = dict(
        name="test-agent",
        client=client,
        model="gemini-test",
    )
    defaults.update(overrides)
    return Agent(**defaults), client


# ── 1. static_instruction + instruction -> system_instruction ──────────────
def test_static_and_dynamic_instruction_reach_system_instruction() -> None:
    agent, client = make_agent(static_instruction="Sos el Gate.", instruction="Evalua los 5 criterios.")
    agent.run({"respuesta": "hola"})

    assert len(client.calls) == 1
    system_instruction = client.calls[0]["config"]["system_instruction"]
    assert "Sos el Gate." in system_instruction
    assert "Evalua los 5 criterios." in system_instruction


# ── 2. include_contents controla el envio de historial ─────────────────────
def test_include_contents_false_omits_history() -> None:
    agent, client = make_agent(include_contents=False)
    history = [{"role": "user", "text": "turno anterior"}]
    agent.run({"q": "actual"}, history=history)

    contents = client.calls[0]["contents"]
    assert len(contents) == 1
    joined = str(contents)
    assert "turno anterior" not in joined


def test_include_contents_true_sends_history() -> None:
    agent, client = make_agent(include_contents=True)
    history = [{"role": "user", "text": "turno anterior"}]
    agent.run({"q": "actual"}, history=history)

    contents = client.calls[0]["contents"]
    assert len(contents) == 2
    assert contents[0]["parts"][0]["text"] == "turno anterior"


# ── 3. before_model_callback devuelve respuesta -> cortocircuita ───────────
def test_before_model_callback_short_circuits_model_call() -> None:
    injected = LlmResponse(text="respuesta cortocircuitada")

    def veto(_agent: Agent, _request: LlmRequest) -> LlmResponse | None:
        return injected

    agent, client = make_agent(before_model_callback=veto)
    result = agent.run({"q": "hola"})

    assert result == "respuesta cortocircuitada"
    assert client.calls == []  # el modelo NUNCA se llamo


# ── 4. before_model_callback devuelve None -> deja pasar y puede mutar ─────
def test_before_model_callback_none_lets_through_and_can_mutate_request() -> None:
    def mutate(_agent: Agent, request: LlmRequest) -> LlmResponse | None:
        request.config["temperature"] = 0.1
        request.contents.append({"role": "user", "parts": [{"text": "extra"}]})
        return None

    agent, client = make_agent(before_model_callback=mutate)
    agent.run({"q": "hola"})

    assert len(client.calls) == 1  # el modelo SI se llamo
    assert client.calls[0]["config"]["temperature"] == 0.1
    assert client.calls[0]["contents"][-1]["parts"][0]["text"] == "extra"


# ── 5. cadena de dos after_model_callback ───────────────────────────────────
def test_after_model_callback_chain_sees_previous_result() -> None:
    seen: list[str | None] = []

    def first(_agent: Agent, _request: LlmRequest, response: LlmResponse) -> LlmResponse | None:
        seen.append(response.text)
        return LlmResponse(text="primero")

    def second(_agent: Agent, _request: LlmRequest, response: LlmResponse) -> LlmResponse | None:
        seen.append(response.text)
        return LlmResponse(text="segundo")

    agent, _client = make_agent(
        client=_FakeClient(text="original"),
        after_model_callback=[first, second],
    )
    result = agent.run({"q": "hola"})

    assert seen == ["original", "primero"]  # el 2do vio lo que devolvio el 1ro
    assert result == "segundo"


# ── 6. output_schema parsea a instancia Pydantic ────────────────────────────
def test_output_schema_parses_to_pydantic_instance_from_parsed() -> None:
    parsed = Bundle(doc_id="domain-x", motivo="coincide con la pregunta")
    client = _FakeClient(responder=lambda _kw: _Resp(text="{}", parsed=parsed))
    agent, _client = make_agent(client=client, output_schema=Bundle)

    result = agent.run({"pregunta": "?"})

    assert isinstance(result, Bundle)
    assert result is parsed


def test_output_schema_parses_to_pydantic_instance_from_text_when_no_parsed() -> None:
    raw_json = '{"doc_id": "domain-y", "motivo": "texto crudo"}'
    client = _FakeClient(responder=lambda _kw: _Resp(text=raw_json, parsed=None))
    agent, _client = make_agent(client=client, output_schema=Bundle)

    result = agent.run({"pregunta": "?"})

    assert isinstance(result, Bundle)
    assert result.doc_id == "domain-y"
    assert result.motivo == "texto crudo"


# ── 7. before_tool_callback veta la tool ────────────────────────────────────
def test_before_tool_callback_vetoes_tool_execution() -> None:
    handler_calls: list[dict[str, Any]] = []

    def handler(args: dict[str, Any]) -> dict[str, Any]:
        handler_calls.append(args)
        return {"resultado": "real"}

    def veto(_agent: Agent, call: ToolCall) -> dict[str, Any] | None:
        assert call.name == "buscar_kb"
        return {"resultado": "vetado"}

    tool = Tool(name="buscar_kb", description="busca en la KB", parameters={}, handler=handler)
    agent, _client = make_agent(tools=[tool], before_tool_callback=veto)

    result = agent.call_tool("buscar_kb", {"query": "algo"})

    assert result == {"resultado": "vetado"}
    assert handler_calls == []  # el handler NUNCA se ejecuto


# ── 8. after_tool_callback reescribe el resultado ───────────────────────────
def test_after_tool_callback_rewrites_tool_result() -> None:
    def handler(_args: dict[str, Any]) -> dict[str, Any]:
        return {"resultado": "real"}

    def rewrite(_agent: Agent, call: ToolCall, result: dict[str, Any]) -> dict[str, Any] | None:
        assert call.name == "buscar_kb"
        assert result == {"resultado": "real"}
        return {"resultado": "reescrito", "original": result}

    tool = Tool(name="buscar_kb", description="busca en la KB", parameters={}, handler=handler)
    agent, _client = make_agent(tools=[tool], after_tool_callback=rewrite)

    result = agent.call_tool("buscar_kb", {"query": "algo"})

    assert result == {"resultado": "reescrito", "original": {"resultado": "real"}}


# ── extra: veto sin tool no ejecuta handler y falla claro si no hay veto ────
def test_call_tool_unknown_tool_without_veto_raises() -> None:
    agent, _client = make_agent()
    with pytest.raises(KeyError):
        agent.call_tool("no_existe", {})


# ── extra: run() ejecuta el loop modelo->tool->modelo cuando hay function_call
def test_run_executes_tool_loop_when_model_requests_function_call() -> None:
    tool_calls: list[dict[str, Any]] = []

    def handler(args: dict[str, Any]) -> dict[str, Any]:
        tool_calls.append(args)
        return {"disponible": True}

    tool = Tool(name="chequear_disponibilidad", description="", parameters={}, handler=handler)

    responses = [
        _Resp(text="", function_calls=[{"name": "chequear_disponibilidad", "args": {"fecha": "hoy"}}]),
        _Resp(text="listo, hay lugar"),
    ]

    def responder(_kwargs: dict[str, Any]) -> _Resp:
        return responses.pop(0)

    client = _FakeClient(responder=responder)
    agent, _client = make_agent(client=client, tools=[tool])

    result = agent.run({"q": "hay lugar hoy?"})

    assert result == "listo, hay lugar"
    assert tool_calls == [{"fecha": "hoy"}]
    assert len(client.calls) == 2  # la segunda llamada incluye el tool result


def test_multiple_function_calls_answer_in_one_content_with_matching_parts() -> None:
    """Dos tools en un turno -> UN content de respuesta con DOS partes.

    Gemini exige que el turno de respuestas tenga tantas partes como partes
    tuvo el turno de llamadas; mandar un content por respuesta devuelve
    400 INVALID_ARGUMENT ("the number of function response parts is equal to
    the number of function call parts"). Solo se manifiesta cuando el modelo
    pide DOS O MAS tools a la vez, por eso no aparecio en local y si en el
    deploy: el RouterAgent caia al fallback deterministico en produccion.
    """
    def handler_a(args: dict[str, Any]) -> dict[str, Any]:
        return {"a": 1}

    def handler_b(args: dict[str, Any]) -> dict[str, Any]:
        return {"b": 2}

    tools = [
        Tool(name="buscar", description="", parameters={}, handler=handler_a),
        Tool(name="mostrar", description="", parameters={}, handler=handler_b),
    ]

    responses = [
        _Resp(text="", function_calls=[
            {"name": "buscar", "args": {"q": "x"}},
            {"name": "mostrar", "args": {"id": "y"}},
        ]),
        _Resp(text="ok"),
    ]

    def responder(_kwargs: dict[str, Any]) -> _Resp:
        return responses.pop(0)

    client = _FakeClient(responder=responder)
    agent, _client = make_agent(client=client, tools=tools)

    assert agent.run({"q": "?"}) == "ok"

    contents = client.calls[-1]["contents"]
    call_turn = [c for c in contents if any("function_call" in p for p in c["parts"])]
    resp_turn = [c for c in contents if any("function_response" in p for p in c["parts"])]

    assert len(call_turn) == 1 and len(call_turn[0]["parts"]) == 2
    # Un solo content de respuesta, con una parte por llamada y en el mismo orden.
    assert len(resp_turn) == 1
    assert len(resp_turn[0]["parts"]) == len(call_turn[0]["parts"])
    assert [p["function_response"]["name"] for p in resp_turn[0]["parts"]] == ["buscar", "mostrar"]
