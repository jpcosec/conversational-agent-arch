"""Playwright del Turn Inspector del chat (`/`, sirve frontends/chat/index.html).

Fase 1.5: el compilador ya no arma el contexto del turno como "todo domain+rule"
con score 1.0 hardcodeado, sino un bundle JUSTIFICADO (~12 documentos, cada uno
con un ``motivo`` -- piso de seguridad, grounding, trait del usuario, similitud
-- y un ``score`` real que puede ser ``None``). Estos tests verifican que el
Turn Inspector MUESTRA ese motivo (contenido, no solo la presencia del
data-testid) -- los tests previos de UI solo afirmaban presencia de
data-testid, por eso ningun bug de layout/contenido quedaba atrapado.

Levanta la app FastAPI in-process (uvicorn en un hilo, puerto libre) con el
orquestador LLM fake (``offline_orchestrator``): no requiere credenciales de
Gemini, solo el Chromium de Playwright (se salta via marker ``ui`` si no esta
disponible, ver tests/conftest.py).
"""
from __future__ import annotations

import socket
import tempfile
import threading
import time
from pathlib import Path

import pytest

from frontends.chat.app import create_app
from kb_agent.project_config import load_project_config
from kb_agent.tools import load_tool_handlers
from tests.support.fakes import offline_orchestrator

pytestmark = pytest.mark.ui

# Dispara el step de onboarding: el bundle entra por grounding, sin similitud
# (motivo determinista: "grounding de steps.onboarding", score null) --
# no depende del ranking semantico del embedder fake.
ONBOARDING_MESSAGE = "hola, quiero pedir una pizza"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server():
    import uvicorn

    db = Path(tempfile.mkdtemp()) / "ui.sqlite"
    cfg = load_project_config(mode="test", env={"CHAT_DB": str(db), "PROFILING_DB": str(db)})
    orch = offline_orchestrator(
        cfg.kb_root, cfg.chat_db_url, tool_handlers=load_tool_handlers(cfg.tool_handlers)
    )
    port = _free_port()
    srv = uvicorn.Server(
        uvicorn.Config(create_app(cfg, orch), host="127.0.0.1", port=port, log_level="warning")
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
    orch.close()


@pytest.fixture
def page(server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=["--no-sandbox"])
        except Exception as exc:  # chromium no instalado
            pytest.skip(f"Chromium de Playwright no disponible: {exc}")
        pg = browser.new_page()
        yield pg
        browser.close()


def _send_and_open_inspector(page, server, message: str):
    page.goto(server, wait_until="networkidle")
    page.locator("[data-testid='chat-input']").fill(message)
    page.locator("[data-testid='chat-send']").click()
    page.wait_for_function(
        "document.querySelectorAll('[data-testid^=\"context-atom-\"]').length > 0",
        timeout=20000,
    )


def test_inspector_context_card_shows_motivo_content(page, server):
    """La card del contexto muestra el MOTIVO real (contenido), no solo el testid.

    Antes del bundle justificado no habia ``motivo`` en el payload; este test
    falla si `renderInspector` deja de pintar el texto (p.ej. si vuelve a
    quedar solo `atom_id · role` como antes de esta fase).
    """
    _send_and_open_inspector(page, server, ONBOARDING_MESSAGE)

    motivo_nodes = page.locator("[data-testid^='context-motivo-']")
    count = motivo_nodes.count()
    assert count > 0, "el inspector no renderizo ninguna card de motivo"

    texts = [motivo_nodes.nth(i).inner_text().strip() for i in range(count)]
    assert all(t and t != "—" for t in texts), f"motivo vacio en alguna card: {texts}"
    # El mensaje de onboarding entra siempre por grounding del step activo
    # (doctrina: piso -> grounding -> traits -> similitud), determinista sin
    # depender del ranking del embedder fake.
    assert any("grounding" in t for t in texts), f"esperaba 'grounding' en algun motivo: {texts}"


def test_inspector_context_card_motivo_matches_atom(page, server):
    """El motivo se ata a SU card (no un bloque global desconectado de cada atom)."""
    _send_and_open_inspector(page, server, ONBOARDING_MESSAGE)

    atom_id = page.locator("[data-testid^='context-atom-']").first.get_attribute("data-atom")
    assert atom_id, "no se encontro ninguna card de contexto"

    motivo = page.locator(f"[data-testid='context-motivo-{atom_id}']")
    assert motivo.count() == 1, f"la card de {atom_id} no tiene su propio nodo de motivo"
    assert motivo.inner_text().strip(), f"motivo vacio para {atom_id}"
