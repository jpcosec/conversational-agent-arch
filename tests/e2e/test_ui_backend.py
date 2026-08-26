"""E2E del backend FastAPI de la UI, conectado al orquestador REAL.

Prueba que la UI vuelve a estar conectada a la arquitectura nueva:
POST /api/chat corre un turno real (Gemini + SLDB + SQL) y devuelve el
contexto atomico que la UI inspecciona. GET /api/atom sirve atoms del store.

Sin mock: usa Gemini real (Vertex ADC via .env) y el store real Don Peppe.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from fastapi.testclient import TestClient

import kb_chat_ui.server as server


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(server.app)


def test_health_reports_kb_root(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "donpeppe" in body["kb_root"].lower()


def test_index_serves_html(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "<!doctype html>" in res.text.lower()
    # la UI nueva consume 'context', no 'mesa'
    assert "turn.context" in res.text


def test_get_atom_returns_store_document(client: TestClient) -> None:
    res = client.get("/api/atom/atom-donpeppe-carta")
    assert res.status_code == 200
    atom = res.json()
    assert atom["atom_id"] == "atom-donpeppe-carta"
    assert "Margherita" in atom["body"]
    assert "domain:catalogo" in atom["tags"]


def test_get_unknown_atom_is_404(client: TestClient) -> None:
    res = client.get("/api/atom/atom-no-existe")
    assert res.status_code == 404


def test_chat_runs_real_turn_and_exposes_atomic_context(client: TestClient) -> None:
    res = client.post(
        "/api/chat",
        json={"message": "que pizzas tienen?", "session_id": "e2e-ui", "scenario": "pizzeria"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["session_id"] == "e2e-ui"

    turn = body["turn"]
    # respuesta real fundamentada (no fallback)
    assert turn["kind"] == "nl"
    assert turn["assistant_message"]
    assert turn["scenario"] == "pizzeria"

    # traza real de la maquina de estados
    assert turn["state_trace"] == ["idle", "evaluating_context", "drafting_response", "idle"]

    # contexto atomico: los atoms REALES que fundamentaron la respuesta
    ctx = turn["context"]
    assert "atom-donpeppe-carta" in ctx["atom_ids"]
    assert ctx["items"], "el contexto debe exponer items con los atoms usados"
    carta = next(i for i in ctx["items"] if i["atom_id"] == "atom-donpeppe-carta")
    assert carta["title"] == "Carta Don Peppe"
    assert carta["role"] == "domain_fact"
    assert "domain:catalogo" in carta["tags"]
    assert "domain:catalogo" in ctx["include_tags"]
