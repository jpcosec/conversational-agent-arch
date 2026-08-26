"""Registry de handlers de tools del negocio.

Un ToolAtom de la KB declara el *schema* (nombre + parametros) de una tool.
Quien la *ejecuta* es un handler Python que el proyecto registra en
``project.config.yaml`` (seccion ``tools``), de la forma::

    tools:
      crear_reserva: kb_agent.tools.reservas:crear_reserva

El orquestador recibe el mapping ``{tool_name: handler}`` ya resuelto; no
conoce ningun negocio en particular. Un handler tiene la firma::

    def handler(session: Session, user_id: int | None, args: dict) -> dict

y devuelve un dict serializable que se agrega al System Turn.
"""
from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy.orm import Session

ToolHandler = Callable[[Session, "int | None", dict[str, Any]], dict[str, Any]]


def resolve_handler(spec: str) -> ToolHandler:
    """Resuelve ``"paquete.modulo:funcion"`` a un callable importado."""
    module_name, _, attr = spec.partition(":")
    if not module_name or not attr:
        raise ValueError(f"tool handler spec invalido: {spec!r} (esperado 'modulo:funcion')")
    module = importlib.import_module(module_name)
    handler = getattr(module, attr, None)
    if handler is None or not callable(handler):
        raise ValueError(f"tool handler no encontrado o no invocable: {spec!r}")
    return handler


def load_tool_handlers(specs: Mapping[str, str] | None) -> dict[str, ToolHandler]:
    """Resuelve el mapping de config ``{tool_name: "modulo:funcion"}``."""
    return {str(name): resolve_handler(str(spec)) for name, spec in (specs or {}).items()}


def execute_tool(
    session: Session,
    user_id: int | None,
    function_call: Mapping[str, Any],
    handlers: Mapping[str, ToolHandler],
) -> dict[str, Any]:
    """Ejecuta la tool via registry y devuelve el System Turn (JSON)."""
    name = function_call.get("name")
    args = dict(function_call.get("args", {}) or {})
    handler = handlers.get(str(name))
    if handler is None:
        return {"tool": name, "status": "unknown_tool", "args": args}
    result = handler(session, user_id, args)
    return {"tool": name, "status": "ok", "args": args, **result}


__all__ = ["ToolHandler", "execute_tool", "load_tool_handlers", "resolve_handler"]
