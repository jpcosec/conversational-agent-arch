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
    # mode="serving" explicito: usa la KB real de Antonia; LLM sigue fake.
    # Sin esto, load_project_config autodetecta pytest (_is_test_context())
    # y cae a test_kb_root (la KB chica de DonPeppe) pese a lo que decia este
    # comentario -- bug preexistente: el "Sin mode='test'" de antes no alcanzaba,
    # porque el default es None y la autodeteccion de pytest gana igual.
    cfg = load_project_config(mode="serving", env={"CHAT_DB": str(db), "PROFILING_DB": str(db)})
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
# Filtro por agente (además del filtro por familia)
# --------------------------------------------------------------------------

_AGENT_IDS = ["conversador", "ruteador", "orquestador", "gate", "perfilador"]


def _visible_atom_types(page) -> set[str]:
    """atom_type de cada nodo-hoja actualmente visible en el canvas (via el
    atributo data-atom-type que MindNode expone solo en nodos kind=atom)."""
    types = page.eval_on_selector_all(
        "[data-atom-type]",
        "els => els.map(e => e.getAttribute('data-atom-type')).filter(t => t)",
    )
    return set(types)


def _wait_full_graph(page, min_types: int = 8, timeout_s: float = 15.0) -> set[str]:
    """El fetch de /api/taxonomy + layout de dagre es async; esperar un
    timeout fijo es fragil (CDN de esm.sh / carga de KB real puede variar).
    Poll hasta ver la variedad de atom_type esperada antes de medir un
    "antes" confiable."""
    deadline = time.time() + timeout_s
    types: set[str] = set()
    while time.time() < deadline:
        types = _visible_atom_types(page)
        if len(types) >= min_types:
            return types
        page.wait_for_timeout(300)
    return types


def test_mindmap_agent_filter_present(page, server: str) -> None:
    _goto_mindmap(page, server)
    for aid in _AGENT_IDS:
        assert page.query_selector(f'[data-testid="mindmap-agent-{aid}"]') is not None, aid


def test_mindmap_agent_filter_by_content(page, server: str) -> None:
    """No alcanza con que exista el testid: al filtrar por el agente Gate
    solo deben quedar visibles atoms atom_type=gate, y el resto (domain,
    rule, step, tool...) tiene que desaparecer. Mapeo verificado contra
    docs/AGENT-CONTRACTS.md §2.0: atom_type 'gate' -> solo el agente Gate."""
    _goto_mindmap(page, server)
    page.wait_for_selector(".react-flow__node", timeout=20000)

    before_types = _wait_full_graph(page)
    assert len(before_types) > 1, f"esperaba varios atom_type antes de filtrar, vi {before_types}"
    assert "gate" in before_types and "domain" in before_types

    page.click('[data-testid="mindmap-agent-gate"]')
    page.wait_for_timeout(500)

    after_types = _visible_atom_types(page)
    assert after_types == {"gate"}, f"filtro por Gate dejo pasar otros atom_type: {after_types}"

    # Desactivar (toggle): vuelve a mostrar todos los atom_type de antes.
    page.click('[data-testid="mindmap-agent-gate"]')
    page.wait_for_timeout(500)
    assert _visible_atom_types(page) == before_types


def test_mindmap_agent_filter_respects_agent_document_map(page, server: str) -> None:
    """atom_type 'tool' solo lo toca el Orquestador (carga base fija,
    AGENT-CONTRACTS §2.0 / KNOWLEDGE-MODEL §5); filtrando por Conversador no
    debe aparecer ningun atom tool, aunque el Conversador vea otros tipos."""
    _goto_mindmap(page, server)
    page.wait_for_selector(".react-flow__node", timeout=20000)
    _wait_full_graph(page)

    page.click('[data-testid="mindmap-agent-conversador"]')
    page.wait_for_timeout(500)
    types = _visible_atom_types(page)
    assert types, "filtro por Conversador no dejo ningun atom visible"
    assert "tool" not in types, f"Conversador no deberia ver atom_type=tool, vi {types}"
    assert "gate" not in types, f"Conversador no deberia ver atom_type=gate, vi {types}"
    assert "domain" in types, f"Conversador si deberia ver atom_type=domain, vi {types}"


def test_mindmap_agent_filter_is_multiselect(page, server: str) -> None:
    """El filtro por agente es combinable, no exclusivo: Gate + Orquestador
    juntos deben mostrar la union (gate y tool), no solo uno de los dos."""
    _goto_mindmap(page, server)
    page.wait_for_selector(".react-flow__node", timeout=20000)
    _wait_full_graph(page)

    page.click('[data-testid="mindmap-agent-gate"]')
    page.click('[data-testid="mindmap-agent-orquestador"]')
    page.wait_for_timeout(500)
    types = _visible_atom_types(page)
    assert "gate" in types, f"Gate+Orquestador deberia incluir gate, vi {types}"
    assert "tool" in types, f"Gate+Orquestador deberia incluir tool (de Orquestador), vi {types}"


def test_mindmap_agent_filter_combines_with_family_filter(page, server: str) -> None:
    """Cruce de los dos ejes (el motivo de ser del filtro, ver pedido del
    usuario): rama 'domain' trae atom_type domain+rule; agregar el filtro de
    agente Orquestador encima debe dejar solo 'rule' (el Orquestador clasifica
    con rule pero no toca domain, KNOWLEDGE-MODEL §5)."""
    _goto_mindmap(page, server)
    page.wait_for_selector(".react-flow__node", timeout=20000)
    _wait_full_graph(page)

    page.click('[data-testid="mindmap-rama-domain"]')
    page.wait_for_timeout(500)
    rama_types = _visible_atom_types(page)
    assert {"domain", "rule"} <= rama_types, f"rama domain deberia traer domain+rule, vi {rama_types}"

    page.click('[data-testid="mindmap-agent-orquestador"]')
    page.wait_for_timeout(500)
    combo_types = _visible_atom_types(page)
    assert combo_types == {"rule"}, (
        f"rama=domain + agente=Orquestador deberia dejar solo rule, vi {combo_types}"
    )


# --------------------------------------------------------------------------
# Screenshot (evidencia visual siempre, aunque algo falle)
# --------------------------------------------------------------------------

def test_mindmap_screenshot(page, server: str) -> None:
    _goto_mindmap(page, server)
    page.wait_for_timeout(1000)
    Path("/tmp").mkdir(exist_ok=True)
    page.screenshot(path="/tmp/mindmap-test.png", full_page=True)
    assert Path("/tmp/mindmap-test.png").exists()
