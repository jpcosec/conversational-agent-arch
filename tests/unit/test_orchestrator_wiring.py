"""Cableado completo del orquestador SIN red: router -> compilador -> policy -> LLM (fake)
-> tools (registry) -> SQL -> perfilador (fake).

Usa la KB de prueba del repo (negocio_kb, store SLDB tipado) y SQLite temporal. Los LLM son
fakes inyectados por los puertos ``Conversador``/``TraitMapper``, asi que aqui
se prueba TODO el runtime salvo la calidad del texto generado (eso vive en e2e).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from kb_agent.agent import DEFAULT_FALLBACK_MESSAGE
from kb_agent.models_sql.identity import Users
from kb_agent.models_sql.reservas import Reservas
from kb_agent.models_sql.session import ChatHistory, SessionState
from kb_agent.orchestrator import Orchestrator, channel_from_external_id
from kb_agent.pii.scrubber import scrub
from kb_agent.project_config import load_project_config
from kb_agent.tools import load_tool_handlers
from tests.support.fakes import (
    FakeConversador,
    FakeEmbedder,
    FakeGate,
    FakeOrchestratorAgent,
    FakeRouterAgent,
    FakeTraitMapper,
    RecordingToolHandler,
    VEGETARIAN_MATCH,
    offline_orchestrator,
)
from tests.support.sldb_seed import minimal_business_atoms, seed_store

RESERVA_MSG = "reservar mesa para 4 el viernes a las 20:00 a nombre de Rojas"
NL_TRACE = ["idle", "evaluating_context", "drafting_response", "idle"]


@pytest.fixture()
def orch(negocio_kb: Path, tmp_db_url: str) -> Orchestrator:
    o = offline_orchestrator(negocio_kb, tmp_db_url, tool_handlers=load_tool_handlers(load_project_config(mode="test").tool_handlers))
    yield o
    o.close()


def test_nl_turn_is_grounded_in_kb_and_traced(orch: Orchestrator) -> None:
    turn = orch.handle_turn(external_id="wa:+56911111111", message="que pizzas tienen?")

    assert turn["kind"] == "nl"
    assert turn["state_trace"] == NL_TRACE
    assert turn["reply"].startswith("[nl]") and turn["reply_text"] == turn["reply"]
    assert turn["system_turn"] is None
    assert turn["used_traits_in_context"] == [] and turn["traits_after"] == []
    assert turn["flow_node"] == "conversation:steps.onboarding"
    assert turn["allowed_transitions"] == ["conversation:steps.booking"]

    ctx = turn["context"]
    assert "domain-menu" in ctx["atom_ids"]
    carta = next(i for i in ctx["items"] if i["atom_id"] == "domain-menu")
    assert carta["title"] == "Domain Menu" and carta["role"] == "domain_fact" and carta["grounds_step"] is True
    assert "domain:catalogo" in ctx["include_tags"]

    # el conversador recibio persona/estrategia/fallback desde la KB, no hardcodeados
    [compiled] = orch.conversador.calls
    assert compiled["persona"]["whoami"].startswith("Soy el asistente de la pizzeria")
    assert compiled["fallback_text"].startswith("Uy, eso no lo tengo a mano")
    assert compiled["question"] == "que pizzas tienen?"

    # Bundle justificado (tarea 1.3): domain-menu entra con motivo de
    # grounding del step activo (onboarding). rule-reservas
    # (que solo groundea "booking") ya NO entra "porque estaba todo incluido"
    # como antes de 1.3 -- el contexto es justificado por turno, no total.
    bundle_by_id = {b["doc_id"]: b for b in compiled["bundle"]}
    assert bundle_by_id["domain-menu"]["motivo"] == "grounding de steps.onboarding"
    assert "rule-reservas" not in bundle_by_id


def test_tool_turn_executes_registered_handler_and_persists(orch: Orchestrator) -> None:
    turn = orch.handle_turn(external_id="wa:+56922222222", message=RESERVA_MSG)

    assert turn["kind"] == "tool_call"
    assert turn["system_turn"]["status"] == "ok" and turn["system_turn"]["tool"] == "crear_reserva"
    assert turn["system_turn"]["args"] == {"fecha": "viernes", "hora": "20:00", "personas": 4, "nombre": "Rojas"}
    assert "waiting_tool" in turn["state_trace"] and turn["state_trace"][-1] == "idle"
    assert turn["reply"].startswith("[tool-ok]") and "reserva_id" in turn["reply"]
    assert orch.count_reservas() == 1

    # decidir != redactar: el conversador solo redacta DESPUES del resultado de la tool
    assert len(orch.conversador.calls) == 1
    assert orch.conversador.calls[0]["system_turn"]["role"] == "system"

    with orch.SessionLocal() as s:
        row = s.scalars(select(Reservas)).one()
        assert (row.fecha, row.hora, row.personas, row.nombre) == ("viernes", "20:00", 4, "Rojas")
        assert row.user_id == turn["user_id"]


def test_tool_without_registered_handler_yields_unknown_tool(negocio_kb: Path, tmp_db_url: str) -> None:
    o = offline_orchestrator(negocio_kb, tmp_db_url, tool_handlers={})
    try:
        turn = o.handle_turn(external_id="wa:+1", message=RESERVA_MSG)
        assert turn["kind"] == "tool_call"
        assert turn["system_turn"]["status"] == "unknown_tool"
        assert o.count_reservas() == 0
    finally:
        o.close()


def test_handlers_can_be_injected_for_any_kb(antonia_kb: Path, tmp_db_url: str) -> None:
    handler = RecordingToolHandler("recordatorio")
    o = offline_orchestrator(antonia_kb, tmp_db_url, tool_handlers={"agendar_recordatorio": handler}, trait_mapper=FakeTraitMapper())
    try:
        turn = o.handle_turn(external_id="whatsapp:+56900000001", message="quiero agendar un recordatorio los martes a las 9:00")
        assert turn["kind"] == "tool_call"
        assert turn["system_turn"]["status"] == "ok"
        assert handler.calls == [{"user_id": turn["user_id"], "args": {"dia": "martes", "hora": "9:00"}}]
    finally:
        o.close()


@pytest.mark.parametrize(
    "with_fallback,project_fallback,expected",
    [
        pytest.param(True, "config", "Si no hay contexto suficiente, pide una aclaración.", id="kb-FallbackRule"),
        pytest.param(False, "Desde config.", "Desde config.", id="project-config"),
        pytest.param(False, None, DEFAULT_FALLBACK_MESSAGE, id="runtime-constant"),
    ],
)
def test_fallback_text_precedence_kb_then_config_then_constant(tmp_path: Path, with_fallback: bool, project_fallback: str | None, expected: str) -> None:
    atoms = [a for a in minimal_business_atoms(with_fallback=with_fallback) if a["type"] not in {"domain", "rule"}]
    root = seed_store(tmp_path / "kb", atoms)
    o = offline_orchestrator(root, fallback_message=project_fallback if project_fallback != "config" else "ignorado", trait_mapper=FakeTraitMapper())
    try:
        turn = o.handle_turn(external_id="ui:x", message="¿tienen promos?")
        assert turn["kind"] == "fallback"
        assert turn["reply"] == expected
        assert "breakpoint_miss" in turn["state_trace"]
        assert o.conversador.calls == []  # el fallback no pasa por el LLM
    finally:
        o.close()


def test_profiler_learns_trait_and_next_turn_uses_it(orch: Orchestrator) -> None:
    first = orch.handle_turn(external_id="wa:+56933333333", message="Hola, soy vegetariano, ¿qué me recomiendan?")
    assert first["traits_before"] == [] and first["traits_after"] == ["trait-vegetariano"]
    assert first["used_traits_in_context"] == []  # el perfil recien aprendido entra al SIGUIENTE turno

    second = orch.handle_turn(external_id="wa:+56933333333", message="¿y para hoy?")
    # used_traits_in_context / user_traits ahora son dicts resueltos contra
    # el TraitAtom (trait_id, title, description, category, confidence,
    # source), no solo el id.
    assert [t["trait_id"] for t in second["used_traits_in_context"]] == ["trait-vegetariano"]
    assert second["used_traits_in_context"][0]["description"].startswith("La persona es vegetariana")
    assert [t["trait_id"] for t in orch.conversador.calls[-1]["user_traits"]] == ["trait-vegetariano"]
    assert "(perfil: trait-vegetariano)" in second["reply"]

    # el perfilador ve el texto scrubbeado y el catalogo de TraitAtoms de la KB
    call = orch.trait_mapper.calls[0]
    assert call["turn_text"] == scrub("Hola, soy vegetariano, ¿qué me recomiendan?")
    assert {c.id for c in call["candidates"]} == {"trait-vegetariano", "trait-sin-gluten"}


def test_channel_is_derived_from_external_id_unless_explicit(orch: Orchestrator) -> None:
    orch.handle_turn(external_id="whatsapp:+56944444444", message="hola")
    orch.handle_turn(external_id="sin-prefijo", message="hola")
    orch.handle_turn(external_id="ui:abc", message="hola", channel="web-ui")
    with orch.SessionLocal() as s:
        channels = {u.external_id: u.channel for u in s.scalars(select(Users))}
    assert channels == {"whatsapp:+56944444444": "whatsapp", "sin-prefijo": "unknown", "ui:abc": "web-ui"}
    assert channel_from_external_id("local:demo") == "local"


def test_chat_history_is_scrubbed_for_user_and_assistant(negocio_kb: Path, tmp_db_url: str) -> None:
    leaky = FakeConversador(lambda c: "Escribeme a test@example.com o al +56912345678.")
    o = offline_orchestrator(negocio_kb, tmp_db_url, conversador=leaky)
    try:
        turn = o.handle_turn(external_id="wa:+56955555555", message="Soy Juan Pérez, mi correo es juan@example.com")
        with o.SessionLocal() as s:
            rows = s.scalars(select(ChatHistory).where(ChatHistory.user_id == turn["user_id"]).order_by(ChatHistory.id)).all()
        assert [r.role for r in rows] == ["user", "assistant"]
        assert all(r.pii_scrubbed for r in rows)
        assert "juan@example.com" not in rows[0].content and "<EMAIL_1>" in rows[0].content
        assert "test@example.com" not in rows[1].content and "<PHONE_" in rows[1].content
    finally:
        o.close()


def test_state_and_data_survive_orchestrator_restart(negocio_kb: Path, tmp_db_url: str) -> None:
    handlers = load_tool_handlers({"crear_reserva": "kb_agent.tools.reservas:crear_reserva"})
    a = offline_orchestrator(negocio_kb, tmp_db_url, tool_handlers=handlers)
    t1 = a.handle_turn(external_id="wa:+56966666666", message="soy vegetariano", scenario="pizzeria")
    a.handle_turn(external_id="wa:+56966666666", message=RESERVA_MSG)
    assert t1["scenario_source"] == "argument" and t1["scenario_effective"] == "pizzeria"
    a.close()

    b = offline_orchestrator(negocio_kb, tmp_db_url, tool_handlers=handlers)
    try:
        t3 = b.handle_turn(external_id="wa:+56966666666", message="¿y para hoy?")
        assert t3["scenario_source"] == "session_state" and t3["scenario_effective"] == "pizzeria"
        assert [t["trait_id"] for t in t3["used_traits_in_context"]] == ["trait-vegetariano"]
        assert b.count_reservas() == 1
        with b.SessionLocal() as s:
            state = s.get(SessionState, t3["user_id"])
            assert state.active_domain == "pizzeria"
            assert state.flow_node == "conversation:steps.onboarding"
            assert state.flow_slots["allowed_transitions"] == ["conversation:steps.booking"]
    finally:
        b.close()


def test_from_config_wires_business_declared_in_yaml(tmp_db_url: str) -> None:
    cfg = load_project_config(mode="test")
    o = Orchestrator.from_config(
        cfg,
        db_url=tmp_db_url,
        conversador=FakeConversador(),
        trait_mapper=FakeTraitMapper(VEGETARIAN_MATCH),
        gate=FakeGate(),
        orchestrator_agent=FakeOrchestratorAgent(),
        router_agent=FakeRouterAgent(),
    )
    o.knowledge_ops._embedder_cache = FakeEmbedder()
    try:
        assert o.kb_root == cfg.kb_root
        assert o.model == cfg.model
        assert set(o.tool_handlers) == set(cfg.tool_handlers)
        assert o.handle_turn(external_id="ui:cfg", message=RESERVA_MSG)["system_turn"]["status"] == "ok"
    finally:
        o.close()


# ── concurrencia: SELECT-then-INSERT sin lock (regresion) ──────────────────
#
# Antes: dos requests simultaneas de un usuario NUEVO pasaban ambas el SELECT
# de ensure_user/_load_or_create_session_state y el segundo INSERT reventaba
# con IntegrityError (UNIQUE users.external_id / PK session_state.user_id),
# perdiendo el turno con un 500. Ademas el turn_id lo daba un contador
# compartido que colisionaba. Estos tests ejercen concurrencia real (threads
# contra un SQLite de archivo); antes no habia ninguno.

def test_concurrent_first_contact_does_not_lose_turns(negocio_kb: Path, tmp_db_url: str) -> None:
    import threading

    o = offline_orchestrator(negocio_kb, tmp_db_url, trait_mapper=FakeTraitMapper())
    n = 8
    results: list[dict] = []
    errors: list[Exception] = []
    barrier = threading.Barrier(n)

    def worker(i: int) -> None:
        try:
            barrier.wait()  # maximizar el solapamiento
            turn = o.handle_turn(external_id="wa:+concurrent-new", message=f"hola {i}")
            results.append(turn)
        except Exception as exc:  # noqa: BLE001 -- el test decide si fallar
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    try:
        assert errors == [], f"requests concurrentes fallaron: {errors!r}"
        assert len(results) == n
        with o.SessionLocal() as s:
            users = s.scalars(select(Users).where(Users.external_id == "wa:+concurrent-new")).all()
            assert len(users) == 1  # un solo usuario, no N
            states = s.scalars(
                select(SessionState).where(SessionState.user_id == users[0].id)
            ).all()
            assert len(states) == 1  # un solo estado de sesion
            msgs = s.scalars(
                select(ChatHistory).where(ChatHistory.user_id == users[0].id)
            ).all()
            # cada turno persiste user+assistant: N turnos -> 2N mensajes
            assert len(msgs) == 2 * n
    finally:
        o.close()


def test_concurrent_turns_get_unique_turn_ids(negocio_kb: Path, tmp_db_url: str) -> None:
    import threading

    o = offline_orchestrator(negocio_kb, tmp_db_url, trait_mapper=FakeTraitMapper())
    n = 12
    turn_ids: list[str] = []
    lock = threading.Lock()
    barrier = threading.Barrier(n)

    def worker(i: int) -> None:
        barrier.wait()
        turn = o.handle_turn(external_id="wa:+concurrent-ids", message=f"hola {i}")
        with lock:
            turn_ids.append(turn["turn_id"])

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    try:
        assert len(turn_ids) == n
        assert len(set(turn_ids)) == n  # todos unicos, no colisionan
    finally:
        o.close()
