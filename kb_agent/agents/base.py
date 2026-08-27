"""Clase base ``Agent``: envoltorio delgado sobre ``google-genai``.

Motivacion (fase 2.1 del plan de unificacion): los 4 agentes del sistema
(Conversador, Ruteador de contexto, Orquestador, Gate) hoy son piezas sueltas
que arman prompts a mano y llaman ``client.models.generate_content`` directo
(ver ``kb_agent/llm.py``). Esta clase les da una superficie COMUN, pero SIN
adoptar ``google-adk``: usa los MISMOS NOMBRES y la MISMA semantica de campos
y callbacks que ``google.adk.agents.LlmAgent`` (paquete instalado, 2.3.0, sin
uso en el repo), para que una eventual migracion a ADK sea cambiar el import,
no rediseñar. Lo que NO se adopta es el ``Runner``/``SessionService`` de ADK:
ese quiere ser dueño del estado de sesion, y ese estado ya vive en
``RouterStateMachine`` + ``session_state`` (SQL).

Diferencias verificadas frente a la API REAL de ``google.adk.agents.LlmAgent``
(leida del fuente instalado, no de memoria):

- ``instruction`` en ADK es DINAMICA (acepta placeholders resueltos en
  runtime) y su destino depende de si hay ``static_instruction``: si
  ``static_instruction`` es ``None``, ``instruction`` -> ``system_instruction``;
  si ``static_instruction`` esta seteado, ``instruction`` pasa a ser CONTENIDO
  DE USUARIO (no va a ``system_instruction``). Esta clase simplifica a proposito
  (pedido explicito): ``static_instruction`` + ``instruction`` se concatenan y
  AMBOS van siempre a ``system_instruction``. Revisar este punto si se migra.
- ``include_contents`` en ADK es ``Literal["default", "none"]``. Aca es
  ``bool`` (``True`` == ``"default"``, ``False`` == ``"none"``) por pedido
  explicito.
- ``output_schema`` en ADK acepta ``SchemaType`` (``type[BaseModel]``,
  ``list[BaseModel]``, ``list[primitivo]``, ``dict`` crudo o
  ``google.genai.types.Schema``). Aca se restringe a ``type[BaseModel] | None``:
  alcanza para los 4 agentes de la tabla del plan.
- Los callbacks de ADK reciben tipos propios del Runner (``CallbackContext``,
  ``LlmRequest``/``LlmResponse`` de ADK, ``BaseTool``, ``ToolContext``) que
  vienen con el ``Runner`` que NO se adopta. Aca los callbacks reciben el
  ``Agent`` y los tipos propios de este modulo (``LlmRequest``, ``LlmResponse``,
  ``ToolCall``, ambos definidos abajo). La SEMANTICA de encadenado es
  IDENTICA a la real de ADK (confirmada en el fuente):
    * ``before_model_callback``: se acepta una funcion o una lista; se llaman
      en orden HASTA que una devuelva algo distinto de ``None``; si una
      devuelve una respuesta, esa respuesta se usa y el modelo NO se llama
      (cortocircuito); si todas devuelven ``None``, se llama al modelo (y
      cualquier mutacion que hayan hecho sobre el ``LlmRequest`` persiste).
    * ``after_model_callback``: misma idea; cada callback ve la respuesta que
      dejo el anterior (o la real del modelo si es el primero); si devuelve
      algo, esa reemplaza a la respuesta corriente.
    * ``before_tool_callback``: si alguna devuelve un resultado (dict), la
      tool NO se ejecuta y ese resultado es el resultado final.
    * ``after_tool_callback``: puede reescribir el resultado ya obtenido
      (de la tool real o del veto de ``before_tool_callback``).
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from pydantic import BaseModel

__all__ = [
    "Agent",
    "LlmRequest",
    "LlmResponse",
    "Tool",
    "ToolCall",
    "BeforeModelCallback",
    "AfterModelCallback",
    "BeforeToolCallback",
    "AfterToolCallback",
]


@dataclass(slots=True)
class ToolCall:
    """Invocacion de una tool: nombre + argumentos.

    Se usa tanto para lo que pide el modelo (function call en la respuesta)
    como para lo que recibe el ``before_tool_callback``/``after_tool_callback``
    al ejecutarla.
    """

    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmRequest:
    """Request MUTABLE que antecede a la llamada al modelo.

    Espeja (con nombres propios, sin depender de ``google.genai.types``) al
    ``LlmRequest`` de ADK: ``contents`` ya resueltos (historial + turno
    actual) y la ``config`` que se le pasa a
    ``client.models.generate_content``. Un ``before_model_callback`` puede
    mutar cualquiera de estos campos in-place; ``Agent._call_model`` los usa
    tal cual quedaron para armar la llamada real (o la siguiente, en el loop
    de tools).
    """

    model: str
    contents: list[dict[str, Any]]
    system_instruction: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LlmResponse:
    """Respuesta del modelo, real o inyectada por un ``before_model_callback``."""

    text: str | None = None
    parsed: BaseModel | None = None
    function_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None


@dataclass(slots=True)
class Tool:
    """Declaracion + handler de una tool disponible para el agente.

    ``parameters`` es un JSON Schema plano (``type``/``properties``/``required``),
    la misma forma que ya usan los ``ToolAtom`` de la KB
    (ver ``kb_agent/agent.py::build_function_declarations``). ``handler``
    recibe los argumentos ya extraidos y devuelve el resultado como dict.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]


# ── callbacks: firmas propias, misma semantica de encadenado que ADK ───────
_SingleBeforeModelCallback: TypeAlias = Callable[["Agent", LlmRequest], "LlmResponse | None"]
_SingleAfterModelCallback: TypeAlias = Callable[["Agent", LlmRequest, LlmResponse], "LlmResponse | None"]
_SingleBeforeToolCallback: TypeAlias = Callable[["Agent", ToolCall], "dict[str, Any] | None"]
_SingleAfterToolCallback: TypeAlias = Callable[["Agent", ToolCall, dict[str, Any]], "dict[str, Any] | None"]

#: Una funcion o una lista de funciones (se encadenan en orden).
BeforeModelCallback: TypeAlias = "_SingleBeforeModelCallback | Sequence[_SingleBeforeModelCallback]"
AfterModelCallback: TypeAlias = "_SingleAfterModelCallback | Sequence[_SingleAfterModelCallback]"
BeforeToolCallback: TypeAlias = "_SingleBeforeToolCallback | Sequence[_SingleBeforeToolCallback]"
AfterToolCallback: TypeAlias = "_SingleAfterToolCallback | Sequence[_SingleAfterToolCallback]"


def _as_callback_list(callback: Any) -> list[Callable[..., Any]]:
    """Normaliza ``None | callable | lista`` a una lista (posiblemente vacia)."""
    if callback is None:
        return []
    if isinstance(callback, (list, tuple)):
        return list(callback)
    return [callback]


def _render_dynamic_context(dynamic_context: Any) -> str:
    """Renderiza el contexto dinamico del turno a texto para el content de usuario.

    Un ``str`` se usa tal cual (ya redactado por el llamador); cualquier otra
    cosa (dict/list con el bundle de documentos, perfil, contexto del
    ruteador, etc.) se serializa a JSON, igual que ya hace el runtime con el
    ``system_turn`` en ``kb_agent/llm.py::build_nl_prompt``.
    """
    if dynamic_context is None:
        return ""
    if isinstance(dynamic_context, str):
        return dynamic_context
    return json.dumps(dynamic_context, ensure_ascii=False, sort_keys=True, default=str)


def _content_from_turn(role: str, text: str) -> dict[str, Any]:
    return {"role": role, "parts": [{"text": text}]}


def _function_call_content(calls: Sequence[ToolCall]) -> dict[str, Any]:
    return {"role": "model", "parts": [{"function_call": {"name": c.name, "args": c.args}} for c in calls]}


def _function_response_content(name: str, result: Mapping[str, Any]) -> dict[str, Any]:
    return {"role": "user", "parts": [{"function_response": {"name": name, "response": dict(result)}}]}


def _extract_function_calls(raw: Any) -> list[ToolCall]:
    """Extrae function calls de la respuesta cruda del cliente (real o fake).

    El cliente real ``google-genai`` expone ``response.function_calls`` (lista
    de ``FunctionCall`` con ``.name``/``.args``). Los fakes de test pueden dar
    esa misma forma, o directamente una lista de dicts ``{"name", "args"}``.
    """
    raw_calls = getattr(raw, "function_calls", None)
    if not raw_calls:
        return []
    calls: list[ToolCall] = []
    for raw_call in raw_calls:
        if isinstance(raw_call, Mapping):
            name = raw_call.get("name")
            args = raw_call.get("args")
        else:
            name = getattr(raw_call, "name", None)
            args = getattr(raw_call, "args", None)
        if name:
            calls.append(ToolCall(name=str(name), args=dict(args or {})))
    return calls


def _tool_declaration(tool: Tool) -> dict[str, Any]:
    return {"name": tool.name, "description": tool.description, "parameters": tool.parameters}


@dataclass(slots=True)
class Agent:
    """Agente LLM delgado sobre ``google-genai``, con la superficie de ADK.

    Instanciable directo para los 4 agentes del sistema (ver docstring del
    modulo). El cliente (``client``) se INYECTA — nunca lo crea esta clase —
    para poder testear sin red ni credenciales, igual que
    ``GeminiConversador``/``GeminiTraitMapper`` en ``kb_agent/llm.py``.

    Atributos:
        name: identificador del agente (para logs/errores).
        client: cliente ``google-genai`` (o un fake con la misma interfaz
            ``client.models.generate_content(model=..., contents=..., config=...)``).
        model: id del modelo Gemini.
        instruction: prompt base (dinamico en ADK; aca texto plano).
        static_instruction: contexto fijo cargado al arrancar (persona,
            estrategia, criterios de gate, etc., segun el agente).
        tools: tools disponibles (declaracion + handler).
        include_contents: si ``True``, ``run`` incluye el historial en
            ``contents``; si ``False``, el modelo solo ve el turno actual.
        output_schema: si esta seteado, ``run`` devuelve una instancia de
            este modelo Pydantic (parseada de ``response.parsed`` o, si el
            cliente no la da, de ``response.text`` via ``model_validate_json``).
        before_model_callback / after_model_callback: ver semantica en el
            docstring del modulo.
        before_tool_callback / after_tool_callback: idem, por tool.
        max_tool_iterations: tope del loop modelo->tool->modelo (evita loops
            infinitos si el modelo insiste en pedir tools).
    """

    name: str
    client: Any
    model: str
    instruction: str = ""
    static_instruction: str = ""
    tools: list[Tool] = field(default_factory=list)
    include_contents: bool = True
    output_schema: type[BaseModel] | None = None
    before_model_callback: BeforeModelCallback | None = None
    after_model_callback: AfterModelCallback | None = None
    before_tool_callback: BeforeToolCallback | None = None
    after_tool_callback: AfterToolCallback | None = None
    max_tool_iterations: int = 4

    _tools_by_name: dict[str, Tool] = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._tools_by_name = {tool.name: tool for tool in self.tools}

    # ── API publica ─────────────────────────────────────────────────────
    def run(self, dynamic_context: Any, history: Sequence[Mapping[str, Any]] | None = None) -> Any:
        """Corre un turno completo: arma el request, llama al modelo (con
        callbacks y, si el modelo pide tools, el loop tool->modelo), y
        devuelve texto o la instancia Pydantic de ``output_schema``.
        """
        request = self._build_request(dynamic_context, history)
        response = self._call_model(request)

        iterations = 0
        while response.function_calls and iterations < self.max_tool_iterations:
            iterations += 1
            request.contents.append(_function_call_content(response.function_calls))
            for call in response.function_calls:
                result = self.call_tool(call.name, call.args)
                request.contents.append(_function_response_content(call.name, result))
            response = self._call_model(request)

        if self.output_schema is not None:
            return self._parse_output(response)
        return response.text

    def call_tool(self, name: str, args: Mapping[str, Any]) -> dict[str, Any]:
        """Ejecuta una tool por nombre, respetando el veto/reescritura de los callbacks."""
        call = ToolCall(name=name, args=dict(args))
        result = self._run_before_tool(call)
        if result is None:
            tool = self._tools_by_name.get(name)
            if tool is None:
                raise KeyError(f"Agent {self.name!r}: tool desconocida {name!r}")
            result = tool.handler(dict(call.args))
        result = self._run_after_tool(call, result)
        return result

    # ── construccion del request ────────────────────────────────────────
    def _build_request(self, dynamic_context: Any, history: Sequence[Mapping[str, Any]] | None) -> LlmRequest:
        contents: list[dict[str, Any]] = []
        if self.include_contents and history:
            for turn in history:
                contents.append(_content_from_turn(str(turn.get("role") or "user"), str(turn.get("text") or "")))
        contents.append(_content_from_turn("user", _render_dynamic_context(dynamic_context)))
        return LlmRequest(
            model=self.model,
            contents=contents,
            system_instruction=self._system_instruction() or None,
        )

    def _system_instruction(self) -> str:
        parts = [p for p in (self.static_instruction, self.instruction) if p]
        return "\n\n".join(parts)

    def _build_config(self, request: LlmRequest) -> dict[str, Any]:
        config: dict[str, Any] = dict(request.config)
        if request.system_instruction and "system_instruction" not in config:
            config["system_instruction"] = request.system_instruction
        if self.tools and "tools" not in config:
            config["tools"] = [{"function_declarations": [_tool_declaration(t) for t in self.tools]}]
        if self.output_schema is not None:
            config.setdefault("response_schema", self.output_schema)
            config.setdefault("response_mime_type", "application/json")
        return config

    # ── llamada al modelo + callbacks ───────────────────────────────────
    def _call_model(self, request: LlmRequest) -> LlmResponse:
        response = self._run_before_model(request)
        if response is None:
            raw = self.client.models.generate_content(
                model=request.model,
                contents=request.contents,
                config=self._build_config(request),
            )
            response = LlmResponse(
                text=getattr(raw, "text", None),
                parsed=getattr(raw, "parsed", None),
                function_calls=_extract_function_calls(raw),
                raw=raw,
            )
        return self._run_after_model(request, response)

    def _run_before_model(self, request: LlmRequest) -> LlmResponse | None:
        for callback in _as_callback_list(self.before_model_callback):
            result = callback(self, request)
            if result is not None:
                return result
        return None

    def _run_after_model(self, request: LlmRequest, response: LlmResponse) -> LlmResponse:
        current = response
        for callback in _as_callback_list(self.after_model_callback):
            result = callback(self, request, current)
            if result is not None:
                current = result
        return current

    def _run_before_tool(self, call: ToolCall) -> dict[str, Any] | None:
        for callback in _as_callback_list(self.before_tool_callback):
            result = callback(self, call)
            if result is not None:
                return result
        return None

    def _run_after_tool(self, call: ToolCall, result: dict[str, Any]) -> dict[str, Any]:
        current = result
        for callback in _as_callback_list(self.after_tool_callback):
            replacement = callback(self, call, current)
            if replacement is not None:
                current = replacement
        return current

    # ── salida estructurada ─────────────────────────────────────────────
    def _parse_output(self, response: LlmResponse) -> BaseModel:
        schema = self.output_schema
        assert schema is not None
        if isinstance(response.parsed, schema):
            return response.parsed
        return schema.model_validate_json(response.text or "")
