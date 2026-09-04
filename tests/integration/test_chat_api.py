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
from frontends.chat.app import create_app
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
    # El mock estatico murio: el dashboard consume /api/metrics (UI-GUIDE 2c).
    assert 'data-testid="dashboard-mock-chip"' not in res.text
    assert "/api/metrics" in res.text and 'data-testid="metrics-kpis"' in res.text


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
    # El turn_id ahora es el uuid que genera y persiste el orquestador (un
    # turno, un identificador), no un contador "tN" por sesion.
    assert body["session_id"] == "s1"
    assert turn["turn_id"] and len(turn["turn_id"]) == 12
    assert turn["context"]["context_id"] == f"ctx-{turn['turn_id']}"
    assert turn["kind"] == "nl" and turn["assistant_message"].startswith("[nl]")
    assert turn["state_trace"] == ["idle", "evaluating_context", "drafting_response", "idle"]
    assert "atom-donpeppe-carta" in turn["context"]["atom_ids"]
    assert turn["flow_node"] == "conversation:steps.onboarding"

    second = client.post("/api/chat", json={"message": "soy vegetariano", "session_id": "s1"}).json()["turn"]
    # turnos distintos -> ids distintos
    assert second["turn_id"] != turn["turn_id"] and second["traits_after"] == ["trait-vegetariano"]

    anonymous = client.post("/api/chat", json={"message": "hola"}).json()
    assert anonymous["session_id"] and anonymous["turn"]["turn_id"]
    assert client.post("/api/chat", json={"message": "   "}).status_code == 400


def test_live_turn_id_matches_persisted_turn_id_in_history(client: TestClient) -> None:
    """El turn_id en vivo (/api/chat) debe ser el mismo que /api/history: un
    turno, un identificador. Antes /api/chat devolvia 'tN' (contador) y
    /api/history el uuid persistido -- no matcheaban."""
    live = client.post(
        "/api/chat", json={"message": "que pizzas tienen?", "session_id": "s-idmatch"}
    ).json()["turn"]
    hist = client.get("/api/history", params={"external_id": "ui:s-idmatch"}).json()
    persisted_ids = [t["turn_id"] for t in hist["turns"]]
    assert live["turn_id"] in persisted_ids


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


def test_lead_card_collects_contact_and_visit_preference(client: TestClient) -> None:
    """/api/lead: paso activo en orden de flujo, perfil y datos capturados del
    mensaje crudo (chat_history queda scrubbeado, la ficha no)."""
    sid = "lead-card-1"
    client.post("/api/chat", json={"message": "hola, quiero reservar el jueves en la tarde", "session_id": sid})
    r = client.post("/api/chat", json={"message": "mi correo es ana@test.cl y mi telefono +56 9 8765 4321", "session_id": sid})
    assert r.status_code == 200
    turn = r.json()["turn"]
    assert turn["collected"]["email"] == "ana@test.cl" and turn["collected"]["telefono"] == "+56987654321"

    lead = client.get("/api/lead", params={"session_id": sid}).json()
    assert lead["collected"] == {"email": "ana@test.cl", "telefono": "+56987654321", "preferencia_visita": "jueves en la tarde"}
    tags = [s["tag"] for s in lead["steps"]]
    assert tags[0] == "conversation:steps.onboarding"  # raiz del grafo primero (Don Peppe: onboarding -> booking)
    assert lead["step"] is not None and lead["step"]["tag"] == turn["flow_node"]
    assert {s["state"] for s in lead["steps"]} <= {"done", "active", "pending"}
    assert all({"trait_id", "title", "category"} <= set(t) for t in lead["traits"])

    # el historial persistido NO expone el email ni el telefono (scrub PII)
    hist = client.get("/api/history", params={"session_id": sid}).json()
    joined = " ".join(m["content"] for m in hist["messages"] if m["role"] == "user")
    assert "ana@test.cl" not in joined and "87654321" not in joined

    assert client.get("/api/lead").status_code == 400


def test_lead_state_classifies_by_what_the_lead_already_gave() -> None:
    """Estado comercial (UI-GUIDE 2c): lo que decide es si se puede confirmar
    la visita, no en que step del runtime quedo la conversacion."""
    from frontends.chat.app import lead_state

    assert lead_state(None) == "nuevo"
    assert lead_state({}, []) == "nuevo"
    assert lead_state({}, [{"trait_id": "t"}]) == "calificado"
    assert lead_state({"preferencia_visita": "jueves"}) == "con_preferencia"
    assert lead_state({"modalidad": "presencial", "email": "a@b.cl"}) == "con_preferencia"
    # contacto sin pedir visita todavia no es una visita por confirmar
    assert lead_state({"email": "a@b.cl", "telefono": "+569"}) == "nuevo"
    assert lead_state({"preferencia_visita": "jueves", "email": "a@b.cl", "telefono": "+569"}) == "datos_completos"


def test_ordered_flow_steps_starts_at_the_graph_root() -> None:
    """El stepper y la ficha ordenan por el GRAFO (raiz primero), no alfabetico:
    con Vitali el orden alfabetico arrancaba en 'agendar'."""
    from frontends.chat.app import ordered_flow_steps

    flow = {
        "nodes": [
            {"id": "s-agendar", "step_tag": "c:agendar", "title": "Agendar", "kind": "obtencion_datos"},
            {"id": "s-saludo", "step_tag": "c:saludo", "title": "Saludo", "kind": "interaccion_simple"},
            {"id": "s-cierre", "step_tag": "c:cierre", "title": "Cierre", "kind": "interaccion_simple"},
            {"id": "s-suelto", "step_tag": "c:suelto", "title": "Suelto", "kind": "interaccion_simple"},
        ],
        "edges": [
            {"source": "s-saludo", "target": "s-agendar"},
            {"source": "s-agendar", "target": "s-cierre"},
            {"source": "s-cierre", "target": "s-suelto"},
        ],
    }
    assert [s["title"] for s in ordered_flow_steps(flow)] == ["Saludo", "Agendar", "Cierre", "Suelto"]
    assert ordered_flow_steps({"nodes": [], "edges": []}) == []


def test_leads_endpoint_groups_by_state_and_queues_visits(client: TestClient) -> None:
    """/api/leads: estado por lead, conteos y cola de visitas por confirmar."""
    client.post("/api/chat", json={"message": "hola", "session_id": "lead-nuevo"})
    client.post("/api/chat", json={"message": "quiero reservar el martes en la tarde", "session_id": "lead-pref"})
    client.post("/api/chat", json={"message": "reservar el lunes, mi correo es c@d.cl y mi fono +56 9 3333 2222", "session_id": "lead-full"})

    d = client.get("/api/leads").json()
    by_id = {l["external_id"]: l for l in d["leads"]}
    assert by_id["ui:lead-pref"]["estado"] == "con_preferencia"
    assert by_id["ui:lead-full"]["estado"] == "datos_completos"
    # 'falta' es lo que le queda por dar; un lead completo puede no haber
    # elegido modalidad todavia (el estado solo exige contacto + intencion).
    assert "email" not in by_id["ui:lead-full"]["falta"] and "telefono" not in by_id["ui:lead-full"]["falta"]
    assert "email" in by_id["ui:lead-pref"]["falta"]

    ids = [l["external_id"] for l in d["queue"]]
    assert "ui:lead-full" in ids and "ui:lead-pref" in ids
    # Los completos van primero: se pueden confirmar sin volver a escribirle a nadie.
    estados = [l["estado"] for l in d["queue"]]
    assert estados == sorted(estados, key=lambda e: e != "datos_completos")
    assert d["counts"]["datos_completos"] >= 1
    # y nadie que no haya pedido visita entra a la cola
    assert all(l["estado"] in ("con_preferencia", "datos_completos") for l in d["queue"])


def test_metrics_endpoint_reports_real_counters(client: TestClient) -> None:
    """/api/metrics: contadores del sqlite, sin mock (UI-GUIDE 2c)."""
    client.post("/api/chat", json={"message": "hola", "session_id": "metricas-1"})
    m = client.get("/api/metrics").json()
    assert m["turnos"] >= 1 and m["usuarios"] >= 1
    assert sum(m["kinds"].values()) == m["turnos"]
    assert sum(x["turnos"] for x in m["por_dia"]) == m["turnos"]
    assert 0 <= m["fallback_pct"] <= 100 and 0 <= m["derivados_pct"] <= 100
    # la latencia sale de turns.duration_ms, que el orquestador persiste por turno
    assert m["latencia_ms"]["n"] >= 1 and m["latencia_ms"]["mediana"] is not None
    assert set(m["leads"]) == {"nuevo", "calificado", "con_preferencia", "datos_completos"}


def test_product_chat_uses_phone_as_identity_and_records_declared_contact(client: TestClient) -> None:
    """El chat de producto (/chat) declara telefono y nombre: con identity_key
    phone el usuario es el MISMO que escribiria por WhatsApp, y ambos entran a
    la ficha del lead."""
    r = client.post("/api/chat", json={"message": "hola", "phone": "+56 9 4444 1111", "nombre": "Ana Ruiz"})
    assert r.status_code == 200
    turn = r.json()["turn"]
    assert turn["collected"]["telefono"] == "+56944441111" and turn["collected"]["nombre"] == "Ana Ruiz"

    lead = client.get("/api/lead", params={"external_id": "web:+56944441111"}).json()
    assert lead["collected"]["nombre"] == "Ana Ruiz"
    leads = {l["external_id"]: l for l in client.get("/api/leads").json()["leads"]}
    assert leads["web:+56944441111"]["channel"] == "web"


@pytest.mark.parametrize("path", ["/chat", "/leads"])
def test_new_views_are_served(client: TestClient, path: str) -> None:
    r = client.get(path)
    assert r.status_code == 200 and len(r.text) > 200


def test_shared_nav_script_is_served(client: TestClient) -> None:
    r = client.get("/static/nav.js")
    assert r.status_code == 200 and "appNav" in r.text
