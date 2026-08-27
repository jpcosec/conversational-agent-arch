"""E2E Playwright del MODO DEMO (flag ``app.demo_mode``).

Recorre las 4 vistas contra la app in-process levantada SIN orquestador
(demo mode): todos los ``/api/*`` responden datos prefabricados de
``frontends/chat/demo_data.py`` y el chat usa el state machine determinista
``DemoStateMachineConversador`` (``tests/support/fakes.py``). No requiere
credenciales de Gemini ni SLDB: solo Chromium de Playwright (marker ``ui``,
se salta si no esta -- ver tests/conftest.py).

Valida exactamente lo que la demo dice mostrar (HANDOFF-DEMO.md + banners
``demo-guide`` de GUI-USAGE-GUIDE.md), incluyendo la maquina de estados del
chat (saludo -> consulta, recordatorio -> obtencion_datos -> tool_call).
"""
from __future__ import annotations

import socket
import threading
import time

import pytest

from frontends.chat.app import create_app
from kb_agent.project_config import load_project_config

pytestmark = pytest.mark.ui


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server():
    import uvicorn

    # mode="serving" + DEMO_MODE=1 => create_app arranca en demo (sin Orchestrator).
    cfg = load_project_config(mode="serving", env={"DEMO_MODE": "1"})
    app = create_app(cfg)
    assert getattr(app, "demo_mode", False) is True, "la app no arranco en modo demo"

    port = _free_port()
    srv = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    assert srv.started, "uvicorn no levanto"
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    th.join(timeout=3)


@pytest.fixture
def page(server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=["--no-sandbox"])
        except Exception as exc:
            pytest.skip(f"Chromium de Playwright no disponible: {exc}")
        pg = browser.new_page()
        yield pg
        browser.close()


def _send(page, message: str):
    page.locator("[data-testid='chat-input']").fill(message)
    page.locator("[data-testid='chat-send']").click()


# ── Chat ──────────────────────────────────────────────────────────────────────

def test_chat_demo_guides_and_config(page, server):
    page.goto(server, wait_until="networkidle")
    # banner pedagogico visible
    assert page.locator("[data-testid='chat-demo-guide']").is_visible()
    # config demo: brand y placeholder vienen de /api/config
    assert page.locator("[data-testid='nav-brand']").inner_text().strip() == "Demo Agent"
    ph = page.locator("[data-testid='chat-input']").get_attribute("placeholder")
    assert ph == "Escribe algo…", ph


def test_chat_nl_turn_populates_inspector(page, server):
    page.goto(server, wait_until="networkidle")
    _send(page, "me da miedo la aguja")
    page.wait_for_function(
        "document.querySelectorAll('[data-testid^=\"context-atom-\"]').length > 0",
        timeout=20000,
    )
    # el turno se autoselecciona -> Summary con Step del flujo
    assert page.locator("[data-testid='inspector-summary']").is_visible()
    assert page.locator("[data-testid='inspector-context']").is_visible()

    # motivos reales por card (no vacios)
    motivos = page.locator("[data-testid^='context-motivo-']")
    assert motivos.count() > 0
    texts = [motivos.nth(i).inner_text().strip() for i in range(motivos.count())]
    assert all(t and t != "—" for t in texts), texts

    # Razonamiento con los 5 agentes reales del pipeline
    rows = page.locator("[data-testid='agent-row']")
    assert rows.count() == 5, rows.count()
    joined = " ".join(rows.nth(i).inner_text() for i in range(rows.count()))
    for name in ("Ruteador", "Orquestador", "Conversador", "Gate", "Perfilador"):
        assert name in joined, f"falta agente {name} en el razonamiento: {joined}"


def test_chat_reminder_reaches_tool_call(page, server):
    page.goto(server, wait_until="networkidle")
    # turno 1: pide recordatorio -> obtencion_datos. Esperar a que el bot
    # responda (input se re-habilita al terminar el POST) antes del turno 2.
    _send(page, "quiero un recordatorio")
    page.wait_for_function(
        "document.querySelectorAll('[data-testid^=\"context-atom-\"]').length > 0",
        timeout=20000,
    )
    page.wait_for_function(
        "!document.querySelector('[data-testid=\"chat-send\"]').disabled",
        timeout=20000,
    )
    # turno 2: da dia + hora -> tool_call. El footer del ultimo turno assistant
    # muestra el badge 'tool_call' (kind del turno), fuente estable e
    # independiente del auto-select del inspector.
    _send(page, "el lunes a las 20")
    # textContent (no innerText): el footer del turno lleva el badge kind aunque
    # su render no esté en viewport; innerText de Playwright puede omitirlo.
    page.wait_for_function(
        "(() => {"
        "const c=document.querySelectorAll('[data-turn-id]');"
        "if(!c.length) return false;"
        "return c[c.length-1].textContent.includes('tool_call');"
        "})()",
        timeout=20000,
    )
    # abrir el inspector de ese turno y verificar la tool en el Summary
    page.locator("[data-turn-id]").last.click()
    page.wait_for_function(
        "(() => {"
        "const s=document.querySelector('[data-testid=\"inspector-summary\"]');"
        "return s && s.textContent.includes('agendar_recordatorio');"
        "})()",
        timeout=20000,
    )
    summary = page.locator("[data-testid='inspector-summary']").text_content()
    assert "tool_call" in summary
    assert "agendar_recordatorio" in summary


def test_chat_atom_modal_opens(page, server):
    page.goto(server, wait_until="networkidle")
    _send(page, "cómo me aplico Selfix")
    page.wait_for_function(
        "document.querySelectorAll('[data-testid^=\"context-atom-\"]').length > 0",
        timeout=20000,
    )
    page.locator("[data-testid^='context-atom-']").first.click()
    page.wait_for_selector("[data-testid='atom-modal']:not(.hidden)", timeout=10000)
    assert page.locator("[data-testid='atom-modal']").is_visible()


# ── Flow ────────────────────────────────────────────────────────────────────

def test_flow_demo_renders_prefab_graph(page, server):
    page.goto(server + "/flow", wait_until="networkidle")
    assert page.locator("[data-testid='flow-demo-guide']").is_visible()
    page.wait_for_function(
        "document.querySelectorAll('.react-flow__node').length >= 5",
        timeout=20000,
    )
    # tools prefabricadas listadas
    assert page.locator("[data-testid='flow-tool-item']").count() >= 2
    # click en un nodo -> inspector con guia de campos
    page.locator(".react-flow__node").first.click()
    page.wait_for_selector("[data-testid='flow-inspector-guide']", timeout=10000)
    assert page.locator("[data-testid='flow-inspector-guide']").is_visible()


# ── Mindmap ─────────────────────────────────────────────────────────────────

def test_mindmap_demo_renders_and_layouts(page, server):
    page.goto(server + "/mindmap", wait_until="networkidle")
    assert page.locator("[data-testid='mindmap-demo-guide']").is_visible()
    page.wait_for_function(
        "document.querySelectorAll('.react-flow__node').length > 0",
        timeout=20000,
    )
    before = page.locator(".react-flow__node").count()
    assert before > 0
    # cambiar a layout embeddings (usa /api/viz/graph prefabricado)
    page.locator("[data-testid='mindmap-layout-embeddings']").click()
    page.wait_for_timeout(800)
    assert page.locator(".react-flow__node").count() == before


# ── Users ───────────────────────────────────────────────────────────────────

def test_users_demo_profiles_and_views(page, server):
    page.goto(server + "/users", wait_until="networkidle")
    assert page.locator("[data-testid='users-demo-guide']").is_visible()
    page.wait_for_function(
        "document.querySelectorAll('[data-testid^=\"user-item-\"]').length >= 3",
        timeout=20000,
    )
    # perfil del primer usuario: KPIs + traits
    assert page.locator("[data-testid='profile-kpis']").is_visible()
    assert page.locator("[data-testid='profile-traits']").is_visible()
    # vista eventos
    page.locator("[data-testid='view-events']").click()
    page.wait_for_selector("[data-testid='users-events']", timeout=10000)
    assert page.locator("[data-testid='users-events']").is_visible()
    # vista conversaciones
    page.locator("[data-testid='view-conversations']").click()
    page.wait_for_function(
        "document.querySelectorAll('[data-testid^=\"conversation-\"]').length > 0",
        timeout=10000,
    )
    assert page.locator("[data-testid^='conversation-']").count() > 0
