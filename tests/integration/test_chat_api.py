"""API FastAPI (``frontends.chat.app.create_app``) sobre el orquestador con LLM fake.

Cubre el contrato que consumen las UIs (chat dashboard, flow editor, perfilado)
y el canal Twilio (firma valida/invalida/no configurado). Sin red.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from kb_agent.project_config import load_project_config
from kb_agent.tools import load_tool_handlers
from frontends.chat.app import OLD_ROUTES, create_app
from tests.support.fakes import offline_orchestrator

TOKEN = "twilio-test-token"


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory, donpeppe_kb: Path) -> TestClient:
    db = tmp_path_factory.mktemp("api") / "chat.sqlite"
    cfg = load_project_config(mode="test", env={"CHAT_DB": str(db), "PROFILING_DB": str(db)})
    orch = offline_orchestrator(cfg.kb_root, cfg.chat_db_url, tool_handlers=load_tool_handlers(cfg.tool_handlers))
    with TestClient(create_app(cfg, orch)) as c:
        yield c
    orch.close()


def test_health_and_config_reflect_project_config(client: TestClient) -> None:
    health = client.get("/api/health").json()
    cfg = client.app.state.cfg
    assert health == {"status": "ok", "kb_root": str(cfg.kb_root), "model": cfg.model}
    assert client.get("/api/config").json() == cfg.to_public_dict()


VIEW_ROUTES = ["/", "/flow", "/mindmap", "/users", "/dashboard"]


@pytest.mark.parametrize("path", VIEW_ROUTES)
def test_static_uis_are_served(client: TestClient, path: str) -> None:
    res = client.get(path)
    assert res.status_code == 200 and "<!doctype html>" in res.text.lower()


@pytest.mark.parametrize("path", ["/dashboard", "/dashboard/"])
def test_dashboard_route_serves_html(client: TestClient, path: str) -> None:
    res = client.get(path)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert 'data-testid="dashboard-mock-chip"' in res.text


def test_shared_theme_css_is_served(client: TestClient) -> None:
    res = client.get("/static/theme.css")
    assert res.status_code == 200
    assert "--bg" in res.text


NAV_LINKS = ["/", "/flow", "/mindmap", "/users", "/dashboard"]


@pytest.mark.parametrize("path", VIEW_ROUTES)
def test_pages_link_shared_theme_and_nav(client: TestClient, path: str) -> None:
    html = client.get(path).text
    assert '/static/theme.css' in html
    for link in NAV_LINKS:
        assert f'href="{link}"' in html


def test_old_routes_redirect_301(client: TestClient) -> None:
    """Las rutas viejas (con y sin barra final) responden 301 al destino nuevo, sin seguir el redirect."""
    assert OLD_ROUTES  # el mapeo vive en frontends/chat/app.py; si desaparece, este test deja de tener sentido
    for old, new in OLD_ROUTES.items():
        for path in (old, old + "/"):
            res = client.get(path, follow_redirects=False)
            assert res.status_code == 301, f"{path} -> {res.status_code}"
            assert res.headers["location"] == new, f"{path} -> {res.headers.get('location')}"


def test_atom_endpoint_reads_store(client: TestClient) -> None:
    atom = client.get("/api/atom/atom-donpeppe-carta").json()
    assert atom["atom_id"] == "atom-donpeppe-carta" and "Margherita" in atom["body"] and "domain:catalogo" in atom["tags"]
    assert client.get("/api/atom/atom-no-existe").status_code == 404


def test_flow_graph_exposes_steps_and_transitions(client: TestClient) -> None:
    flow = client.get("/api/flow").json()
    by_id = {n["id"]: n for n in flow["nodes"]}
    assert by_id["step-donpeppe-onboarding"]["step_tag"] == "conversation:steps.onboarding"
    assert {"source": "step-donpeppe-onboarding", "target": "step-donpeppe-booking", "relation": "flows_to"} in flow["edges"]


def test_viz_graph_is_built_from_active_kb(client: TestClient) -> None:
    graph = client.get("/api/viz/graph").json()
    cfg = client.app.state.cfg
    assert graph["kb"] == cfg.name
    assert graph["nodes"]
    node_ids = {n["id"] for n in graph["nodes"]}
    assert "atom-donpeppe-carta" in node_ids
    assert graph["edges"]
    for edge in graph["edges"]:
        assert edge["source"] in node_ids and edge["target"] in node_ids

    limited = client.get("/api/viz/graph", params={"max_edges_per_node": 1}).json()
    counts: dict[str, int] = {}
    for edge in limited["edges"]:
        counts[edge["source"]] = counts.get(edge["source"], 0) + 1
    assert counts and max(counts.values()) <= 1


def test_chat_turn_contract_and_session_continuity(client: TestClient) -> None:
    res = client.post("/api/chat", json={"message": "que pizzas tienen?", "session_id": "s1"})
    assert res.status_code == 200
    body = res.json()
    turn = body["turn"]
    assert body["session_id"] == "s1" and turn["turn_id"] == "t1"
    assert turn["kind"] == "nl" and turn["assistant_message"].startswith("[nl]")
    assert turn["state_trace"] == ["idle", "evaluating_context", "drafting_response", "idle"]
    assert "atom-donpeppe-carta" in turn["context"]["atom_ids"]
    assert turn["context"]["context_id"] == "ctx-t1"
    assert turn["flow_node"] == "conversation:steps.onboarding"

    second = client.post("/api/chat", json={"message": "soy vegetariano", "session_id": "s1"}).json()["turn"]
    assert second["turn_id"] == "t2" and second["traits_after"] == ["trait-vegetariano"]

    anonymous = client.post("/api/chat", json={"message": "hola"}).json()
    assert anonymous["session_id"] and anonymous["turn"]["turn_id"] == "t1"
    assert client.post("/api/chat", json={"message": "   "}).status_code == 400


def test_chat_tool_turn_and_profiles_endpoint(client: TestClient) -> None:
    turn = client.post("/api/chat", json={"message": "reservar mesa para 4 el viernes a las 20:00 a nombre de Rojas", "session_id": "s-tool"}).json()["turn"]
    assert turn["kind"] == "tool_call" and turn["system_turn"]["status"] == "ok"

    profiles = client.get("/api/profiles").json()
    users = {u["external_id"]: u for u in profiles["users"]}
    assert users["ui:s1"]["channel"] == "ui"
    assert [t["trait_id"] for t in users["ui:s1"]["traits"]] == ["trait-vegetariano"]
    assert "trait-vegetariano" in profiles["fichas"] and profiles["missing_fichas"] == []


# ── Twilio ────────────────────────────────────────────────────────────────────

def _post_twilio(client: TestClient, form: dict[str, str], signature: str):
    return client.post("/webhooks/twilio", data=form, headers={"X-Twilio-Signature": signature})


def test_twilio_valid_signature_runs_turn_and_replies_twiml(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    form = {"From": "whatsapp:+56912345678", "To": "whatsapp:+14155238886", "Body": "  que pizzas tienen?  ", "MessageSid": "SM1"}
    url = str(client.base_url) + "/webhooks/twilio"
    res = _post_twilio(client, form, RequestValidator(TOKEN).compute_signature(url, form))

    assert res.status_code == 200 and res.headers["content-type"].startswith("application/xml")
    assert "<Message>[nl]" in res.text
    users = {u["external_id"]: u["channel"] for u in client.get("/api/profiles").json()["users"]}
    assert users["whatsapp:+56912345678"] == "whatsapp"


def test_twilio_invalid_signature_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    calls = len(client.app.state.orchestrator.conversador.calls)
    res = _post_twilio(client, {"From": "whatsapp:+1", "Body": "hola"}, "firma-invalida")
    assert res.status_code == 403 and res.json() == {"detail": "invalid twilio signature"}
    assert len(client.app.state.orchestrator.conversador.calls) == calls


def test_twilio_unconfigured_returns_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    assert _post_twilio(client, {"From": "whatsapp:+1", "Body": "hola"}, "x").status_code == 503
