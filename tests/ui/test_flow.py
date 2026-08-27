"""Test Playwright de la vista Flow (`/flow`, sirve frontends/flow_editor/index.html).

Verifica el estado objetivo de UI-GUIDE.md §3 (Flow) por `data-testid`:
grafo React Flow, paleta, panel de tools, toggle de layout LR/TB, node-toolbar,
subflows, y el endpoint `/api/tools`.

Requiere Chromium de Playwright (marker ``ui``). El runtime usa la KB real de
Antonia (que tiene ConversationSteps) + LLM fake (offline_orchestrator), asi
que el grafo debe renderizar nodos sin credenciales.

Ejecutar:
    SKIP_LLM_TESTS=1 python -m pytest tests/ui/test_flow.py -x -v
"""
from __future__ import annotations

import socket
import tempfile
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from frontends.chat.app import create_app
from kb_agent.project_config import load_project_config
from kb_agent.tools import load_tool_handlers
from tests.support.fakes import offline_orchestrator

pytestmark = pytest.mark.ui


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server():
    db = Path(tempfile.mkdtemp()) / "ui.sqlite"
    cfg = load_project_config(env={"CHAT_DB": str(db), "PROFILING_DB": str(db)})
    orch = offline_orchestrator(
        cfg.kb_root,
        cfg.chat_db_url,
        tool_handlers=load_tool_handlers(cfg.tool_handlers),
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
    assert srv.started
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    th.join(timeout=3)


@pytest.fixture
def page(server: str):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=["--no-sandbox"])
        except Exception as exc:  # chromium no instalado
            pytest.skip(f"chromium de playwright no disponible: {exc}")
        pg = browser.new_page()
        errors: list[str] = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.errors = errors  # type: ignore[attr-defined]
        pg.base_url = server  # type: ignore[attr-defined]
        yield pg
        browser.close()


def _open_flow(page):
    page.goto(f"{page.base_url}/flow", wait_until="networkidle")
    page.wait_for_timeout(3000)


# --------------------------------------------------------------------------
# Endpoint que alimenta el panel de tools
# --------------------------------------------------------------------------

def test_api_tools_responds_json(server: str):
    """`GET /api/tools` responde 200 con una lista JSON (§3.2, §8)."""
    import httpx

    r = httpx.get(f"{server}/api/tools", timeout=20)
    assert r.status_code == 200, f"/api/tools status {r.status_code}"
    data = r.json()
    assert isinstance(data, list), f"/api/tools no devolvio lista: {type(data)}"
    # Cada tool debe tener al menos name/tool_id
    for t in data:
        assert "name" in t or "tool_id" in t, f"tool sin name/tool_id: {t}"


def test_api_flow_responds_graph(server: str):
    """`GET /api/flow` devuelve nodes+edges (fuente del grafo)."""
    import httpx

    r = httpx.get(f"{server}/api/flow", timeout=20)
    assert r.status_code == 200, f"/api/flow status {r.status_code}"
    data = r.json()
    assert "nodes" in data and "edges" in data, f"/api/flow shape inesperado: {list(data)}"
    assert isinstance(data["nodes"], list)


# --------------------------------------------------------------------------
# Render de la pagina
# --------------------------------------------------------------------------

def test_flow_no_js_errors(page):
    """La vista carga sin errores de JavaScript en consola (§0)."""
    _open_flow(page)
    assert page.errors == [], f"errores JS en /flow: {page.errors}"


def test_flow_topbar_present(page):
    """Topbar unica global presente (§1)."""
    _open_flow(page)
    assert page.locator("[data-testid='nav-topbar']").is_visible()
    assert page.locator("[data-testid='nav-flow']").is_visible()


def test_flow_canvas_renders(page):
    """El canvas de React Flow renderiza (§3.1)."""
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    assert page.locator("[class*=react-flow]").count() > 0


def test_flow_graph_has_nodes(page):
    """El grafo NO esta vacio: Antonia tiene ConversationSteps (§3.1)."""
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    page.wait_for_timeout(2000)
    nodes = page.locator("[class*=react-flow__node]")
    assert nodes.count() > 0, "grafo de flow vacio (0 nodos) pese a que Antonia tiene steps"


def test_flow_layout_toggle(page):
    """Toggle de layout LR/TB visible (§3.1)."""
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    assert page.locator("[data-testid='flow-layout-toggle']").is_visible()


def test_flow_palette(page):
    """Paleta de tipos de nodo arrastrables presente con 4 tipos (§3.2)."""
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    palette = page.locator("[data-testid='flow-palette']")
    assert palette.is_visible()
    items = page.locator("[data-testid='flow-palette-item']")
    assert items.count() == 4, f"paleta con {items.count()} items, se esperaban 4"


def test_flow_tools_panel(page):
    """Panel de tools de la KB activa presente (§3.2)."""
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    assert page.locator("[data-testid='flow-tools-panel']").is_visible()


def test_flow_inspector_present(page):
    """Inspector lateral presente (§3.2)."""
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    assert page.locator("[data-testid='flow-inspector']").is_visible()


def test_flow_node_toolbar_on_select(page):
    """Al seleccionar un nodo aparece el NodeToolbar (§3.2).

    NOTA: en el HTML actual NodeToolbar se importa pero nunca se renderiza en
    el JSX -> se espera que este test FALLE hasta que se agregue el toolbar.
    """
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    page.wait_for_timeout(2000)
    node = page.locator("[class*=react-flow__node]").first
    node.click()
    page.wait_for_timeout(500)
    toolbar = page.locator("[data-testid='flow-node-toolbar']")
    assert toolbar.count() > 0 and toolbar.first.is_visible(), (
        "no aparece flow-node-toolbar al seleccionar nodo"
    )


def test_flow_node_click_opens_inspector(page):
    """Click en nodo llena el inspector con campos del step (§3.2)."""
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    page.wait_for_timeout(2000)
    node = page.locator("[class*=react-flow__node]").first
    node.click()
    page.wait_for_timeout(400)
    header = page.locator("[data-testid='flow-inspector']")
    assert header.inner_text().strip() != "", "inspector vacio tras click en nodo"


def test_flow_add_subflow(page):
    """Boton de añadir subflow presente y crea un contenedor (§3.3)."""
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    add = page.locator("[data-testid='flow-add-subflow']")
    assert add.is_visible(), "no existe boton flow-add-subflow"
    add.click()
    page.wait_for_timeout(300)
    subflows = page.locator("[data-testid^='flow-subflow-']")
    assert subflows.count() >= 1, "no se creo ningun subflow tras click"


def test_flow_screenshot(page):
    """Captura de estado para inspeccion visual manual."""
    _open_flow(page)
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    page.wait_for_timeout(1500)
    page.screenshot(path="/tmp/flow-test.png", full_page=True)
