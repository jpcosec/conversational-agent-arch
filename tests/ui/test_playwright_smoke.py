"""Smoke de las UIs con Playwright contra la app FastAPI levantada in-process (sin red LLM).

El servidor corre uvicorn en un hilo, en un puerto libre, con el orquestador
de LLM fake: el turno de chat es real (compilador + SQL + tools), solo el
texto NL es determinista. Requiere Chromium de Playwright (marker ``ui``); las
UIs cargan Tailwind/React desde CDN, asi que necesitan salida a internet.
"""
from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest

from kb_agent.project_config import load_project_config
from kb_agent.tools import load_tool_handlers
from frontends.chat.app import create_app
from tests.support.fakes import offline_orchestrator

pytestmark = pytest.mark.ui


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    import uvicorn

    db = tmp_path_factory.mktemp("ui") / "ui.sqlite"
    cfg = load_project_config(mode="test", env={"CHAT_DB": str(db), "PROFILING_DB": str(db)})
    orch = offline_orchestrator(cfg.kb_root, cfg.chat_db_url, tool_handlers=load_tool_handlers(cfg.tool_handlers))
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(cfg, orch), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "uvicorn no levanto"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)
    orch.close()


@pytest.fixture(scope="module")
def page(base_url: str):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=["--no-sandbox"])
        except Exception as exc:  # chromium no instalado
            pytest.skip(f"chromium de playwright no disponible: {exc}")
        page = browser.new_page()
        page.errors = []  # type: ignore[attr-defined]
        page.on("pageerror", lambda e: page.errors.append(str(e)))  # type: ignore[attr-defined]
        yield page
        browser.close()


def test_chat_dashboard_runs_a_turn_and_shows_atomic_context(page, base_url: str) -> None:
    cfg = page.request.get(f"{base_url}/api/config").json()
    page.goto(base_url, wait_until="networkidle")
    assert cfg["runtime_title"] in page.content()
    assert cfg["name"] in page.inner_text("body")  # marca desde /api/config, no del HTML

    box = page.query_selector("textarea, input[type=text]")
    assert box is not None
    box.fill("que pizzas tienen?")
    btn = page.query_selector("button[type=submit]") or page.query_selector("button")
    (btn.click() if btn else box.press("Enter"))
    page.wait_for_function("document.body.innerText.includes('[nl]')", timeout=20000)
    page.wait_for_function("typeof selectedTurnId!=='undefined' && selectedTurnId && selectedTurnId.startsWith('t')", timeout=20000)
    page.wait_for_timeout(500)
    assert "Carta Don Peppe" in page.content()  # atom real del contexto del turno (KB de prueba)


def test_flow_editor_renders_graph_from_api(page, base_url: str) -> None:
    flow = page.request.get(f"{base_url}/api/flow").json()
    assert flow["nodes"] and flow["edges"]
    page.goto(f"{base_url}/conversation_flow_editor", wait_until="networkidle")
    page.wait_for_selector("[class*=node], svg, canvas", timeout=20000)


def test_profiling_viewer_lists_users(page, base_url: str) -> None:
    profiles = page.request.get(f"{base_url}/api/profiles").json()
    assert profiles["users"] and profiles["missing_fichas"] == []
    page.goto(f"{base_url}/profiling_viewer", wait_until="networkidle")
    assert len(page.content()) > 200
    assert page.errors == [], page.errors  # type: ignore[attr-defined]


def test_viz_graph_renders_from_active_kb(page, base_url: str) -> None:
    graph = page.request.get(f"{base_url}/api/viz/graph").json()
    assert graph["nodes"]
    page.goto(f"{base_url}/viz", wait_until="networkidle")
    page.wait_for_selector(".react-flow__node, svg", timeout=20000)
    assert page.errors == [], page.errors  # type: ignore[attr-defined]


def test_chat_sidebar_links_to_viz(page, base_url: str) -> None:
    page.goto(base_url, wait_until="networkidle")
    assert page.query_selector("a[href='/viz']") is not None
