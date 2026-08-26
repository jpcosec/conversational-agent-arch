"""Registry de tools: el negocio declara handlers en config; el orquestador solo despacha."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base
from kb_agent.models_sql.reservas import Reservas
from kb_agent.tools import execute_tool, load_tool_handlers, resolve_handler
from kb_agent.tools.reservas import crear_reserva
from tests.support.fakes import RecordingToolHandler


def test_resolve_handler_imports_module_colon_function() -> None:
    assert resolve_handler("kb_agent.tools.reservas:crear_reserva") is crear_reserva


@pytest.mark.parametrize("spec", ["", "sin-dos-puntos", ":solo_attr", "modulo.inexistente:f", "kb_agent.tools.reservas:no_existe"])
def test_resolve_handler_rejects_invalid_specs(spec: str) -> None:
    with pytest.raises((ValueError, ModuleNotFoundError)):
        resolve_handler(spec)


def test_load_tool_handlers_resolves_config_mapping() -> None:
    handlers = load_tool_handlers({"crear_reserva": "kb_agent.tools.reservas:crear_reserva"})
    assert handlers == {"crear_reserva": crear_reserva}
    assert load_tool_handlers(None) == {} and load_tool_handlers({}) == {}


def test_execute_tool_dispatches_and_builds_system_turn() -> None:
    handler = RecordingToolHandler("recordatorio")
    system_turn = execute_tool(None, 7, {"name": "agendar_recordatorio", "args": {"dia": "martes"}}, {"agendar_recordatorio": handler})
    assert system_turn == {"tool": "agendar_recordatorio", "status": "ok", "args": {"dia": "martes"}, "recordatorio_id": 1}
    assert handler.calls == [{"user_id": 7, "args": {"dia": "martes"}}]


def test_execute_tool_reports_unknown_tool_without_raising() -> None:
    assert execute_tool(None, None, {"name": "nope", "args": {}}, {}) == {"tool": "nope", "status": "unknown_tool", "args": {}}


def test_crear_reserva_handler_persists_row() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        result = crear_reserva(session, None, {"fecha": "viernes", "hora": "20:00", "personas": "4", "nombre": "Rojas"})
        row = session.get(Reservas, result["reserva_id"])
        assert (row.fecha, row.hora, row.personas, row.nombre) == ("viernes", "20:00", 4, "Rojas")
