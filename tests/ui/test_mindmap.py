"""Playwright para la vista mindmap (`/mindmap`, sirve frontends/taxonomy/index.html).

Levanta la app FastAPI in-process con uvicorn en un hilo, sobre la KB real de
Antonia (serving) y el LLM fake. Verifica el estado objetivo definido en
frontends/UI-GUIDE.md §4 usando exclusivamente selectores ``data-testid``
(nunca texto/clase). Requiere Chromium de Playwright y salida a internet
(React/@xyflow/dagre desde CDN via importmap).

Este archivo RECABA informacion de bugs: cada aspecto de §4 es un test
independiente para que un fallo aislado no oculte el resto.
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
def server(tmp_path_factory: pytest.TempPathFactory):
    import uvicorn

    db = tmp_path_factory.mktemp("ui") / "ui.sqlite"
    # Sin mode="test": usa la KB real de Antonia (serving); LLM sigue fake.
    cfg = load_project_config(env={"CHAT_DB": str(db), "PROFILING_DB": str(db)})
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


@pytest.fixture(scope="module")
def page(server: str):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=["--no-sandbox"])
        except Exception as exc:  # chromium no instalado
            pytest.skip(f"chromium de playwright no disponible: {exc}")
        pg = browser.new_page()
        pg.errors = []  # type: ignore[attr-defined]
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))  # type: ignore[attr-defined]
        yield pg
        browser.close()


def _goto_mindmap(page, server: str):
    page.goto(f"{server}/mindmap", wait_until="networkidle")
    page.wait_for_timeout(3000)


# --------------------------------------------------------------------------
# API de datos (precondicion: sin datos no hay grafo)
# --------------------------------------------------------------------------

def test_taxonomy_api_returns_atoms(page, server: str) -> None:
    tax = page.request.get(f"{server}/api/taxonomy").json()
    assert set(tax.keys()) >= {"self", "domain", "conversation", "user"}, tax.keys()

    def _count(fam: dict) -> int:
        n = len(fam.get("orphans", []))

        def walk(children):
            s = 0
            for node in children:
                s += len(node.get("atoms", []))
                s += walk(node.get("children", []))
            return s

        return n + walk(fam.get("children", []))

    total = sum(_count(v) for v in tax.values())
    assert total > 0, f"taxonomy sin atoms: {tax}"


# --------------------------------------------------------------------------
# Render base
# --------------------------------------------------------------------------

def test_mindmap_page_loads_without_js_errors(page, server: str) -> None:
    _goto_mindmap(page, server)
    assert page.errors == [], page.errors  # type: ignore[attr-defined]


def test_mindmap_renders_nodes(page, server: str) -> None:
    _goto_mindmap(page, server)
    # @xyflow renderiza nodos con class react-flow__node; el contenido es
    # data-driven, asi que contamos los nodos del canvas.
    page.wait_for_selector(".react-flow__node", timeout=20000)
    count = len(page.query_selector_all(".react-flow__node"))
    assert count > 0, "el canvas no renderizo ningun nodo"


# --------------------------------------------------------------------------
# §4.1 Layouts
# --------------------------------------------------------------------------

def test_mindmap_layout_tree_present(page, server: str) -> None:
    _goto_mindmap(page, server)
    assert page.query_selector('[data-testid="mindmap-layout-tree"]') is not None


def test_mindmap_layout_topdown_present(page, server: str) -> None:
    _goto_mindmap(page, server)
    assert page.query_selector('[data-testid="mindmap-layout-topdown"]') is not None


def test_mindmap_layout_embeddings_present(page, server: str) -> None:
    _goto_mindmap(page, server)
    assert page.query_selector('[data-testid="mindmap-layout-embeddings"]') is not None


def test_mindmap_switch_to_topdown(page, server: str) -> None:
    _goto_mindmap(page, server)
    page.click('[data-testid="mindmap-layout-topdown"]')
    page.wait_for_timeout(800)
    assert page.errors == [], page.errors  # type: ignore[attr-defined]
    assert len(page.query_selector_all(".react-flow__node")) > 0


def test_mindmap_switch_to_embeddings(page, server: str) -> None:
    _goto_mindmap(page, server)
    page.click('[data-testid="mindmap-layout-embeddings"]')
    page.wait_for_timeout(1200)
    assert page.errors == [], page.errors  # type: ignore[attr-defined]
    assert len(page.query_selector_all(".react-flow__node")) > 0


# --------------------------------------------------------------------------
# §4.2 Sidebar filtro
# --------------------------------------------------------------------------

def test_mindmap_sidebar_present(page, server: str) -> None:
    _goto_mindmap(page, server)
    assert page.query_selector('[data-testid="mindmap-sidebar"]') is not None


# --------------------------------------------------------------------------
# §4.3 Nodos: drag handle + node toolbar
# --------------------------------------------------------------------------

def test_mindmap_drag_handle_present(page, server: str) -> None:
    _goto_mindmap(page, server)
    page.wait_for_selector(".react-flow__node", timeout=20000)
    assert page.query_selector('[data-testid="mindmap-drag-handle"]') is not None


def test_mindmap_node_toolbar_present(page, server: str) -> None:
    _goto_mindmap(page, server)
    page.wait_for_selector(".react-flow__node", timeout=20000)
    # NodeToolbar (§4.3) suele montarse al seleccionar un nodo. Clickeamos el
    # primer nodo y buscamos el data-testid del toolbar.
    node = page.query_selector(".react-flow__node")
    assert node is not None
    node.click()
    page.wait_for_timeout(500)
    assert page.query_selector('[data-testid="mindmap-node-toolbar"]') is not None


# --------------------------------------------------------------------------
# §4.4 Cross-family links
# --------------------------------------------------------------------------

def test_mindmap_xfamily_toggle_present(page, server: str) -> None:
    _goto_mindmap(page, server)
    assert page.query_selector('[data-testid="mindmap-xfamily-toggle"]') is not None


# --------------------------------------------------------------------------
# §4.5 Busqueda
# --------------------------------------------------------------------------

def test_mindmap_search_present(page, server: str) -> None:
    _goto_mindmap(page, server)
    assert page.query_selector('[data-testid="mindmap-search"]') is not None


def test_mindmap_search_filters_nodes(page, server: str) -> None:
    _goto_mindmap(page, server)
    page.wait_for_selector(".react-flow__node", timeout=20000)
    before = len(page.query_selector_all(".react-flow__node"))
    box = page.query_selector('[data-testid="mindmap-search"]')
    assert box is not None
    box.fill("zzz-no-existe-nada-asi-xyz")
    page.wait_for_timeout(600)
    after = len(page.query_selector_all(".react-flow__node"))
    assert after < before, f"la busqueda no filtro nodos (antes={before}, despues={after})"


# --------------------------------------------------------------------------
# Screenshot (evidencia visual siempre, aunque algo falle)
# --------------------------------------------------------------------------

def test_mindmap_screenshot(page, server: str) -> None:
    _goto_mindmap(page, server)
    page.wait_for_timeout(1000)
    Path("/tmp").mkdir(exist_ok=True)
    page.screenshot(path="/tmp/mindmap-test.png", full_page=True)
    assert Path("/tmp/mindmap-test.png").exists()
