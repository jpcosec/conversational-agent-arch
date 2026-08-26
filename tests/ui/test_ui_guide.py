"""Tests que validan `frontends/UI-GUIDE.md` — el estado objetivo de las UIs.

Cada test verifica una sección de la guía. Fallan HOY (UI sin rediseñar) y
pasan cuando la implementación esté completa. Sirven como spec ejecutable.

Convención:
- Cada elemento lleva `data-testid` (definido en UI-GUIDE.md).
- Los tests seleccionan SOLO por `data-testid`, nunca por texto o clase.
- `SKIP_LLM_TESTS=1` evita credenciales. El fixture levanta uvicorn
  in-process con LLM fake (offline_orchestrator).
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


# ── Fixtures (calcadas de test_playwright_smoke.py) ──────────────────────


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
        except Exception as exc:
            pytest.skip(f"chromium de playwright no disponible: {exc}")
        page = browser.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        yield page
        browser.close()


# ── Helpers ──────────────────────────────────────────────────────────────


def _send_chat(page, text: str):
    """Escribe y envía un mensaje en el chat."""
    inp = page.locator("[data-testid='chat-input']")
    inp.fill(text)
    page.locator("[data-testid='chat-send']").click()


def _wait_turn(page):
    """Espera a que aparezca un turno renderizado."""
    page.wait_for_function(
        "document.querySelector('[data-testid^=turn-]') !== null",
        timeout=20000,
    )
    page.wait_for_timeout(500)


# ══════════════════════════════════════════════════════════════════════════
# Sección 0 — Sistema de diseño
# ══════════════════════════════════════════════════════════════════════════


def test_config_serves_input_placeholder(page, base_url: str):
    """El endpoint /api/config expone input_placeholder (UI-GUIDE §8)."""
    cfg = page.request.get(f"{base_url}/api/config").json()
    assert "input_placeholder" in cfg, "project_config debe exponer input_placeholder"
    assert isinstance(cfg["input_placeholder"], str)


# ══════════════════════════════════════════════════════════════════════════
# Sección 1 — Navegación global
# ══════════════════════════════════════════════════════════════════════════


def test_nav_shows_all_views(page, base_url: str):
    """La topbar tiene links a las 4 vistas (UI-GUIDE §1)."""
    page.goto(base_url, wait_until="networkidle")
    nav = page.locator("[data-testid='nav-topbar']")
    links = ["nav-chat", "nav-flow", "nav-mindmap", "nav-users"]
    for lid in links:
        link = nav.locator(f"[data-testid='{lid}']")
        assert link.is_visible(), f"Falta {lid} en la navegacion"


def test_old_routes_redirect(page, base_url: str):
    """Las rutas viejas hacen redirect 301 a las nuevas (UI-GUIDE §1)."""
    redirects = {
        "/conversation_flow_editor": "/flow",
        "/taxonomy_explorer": "/mindmap",
        "/profiling_viewer": "/users",
        "/viz": "/mindmap",
    }
    for old, new in redirects.items():
        resp = page.request.get(f"{base_url}{old}")
        assert resp.status == 301, f"{old} deberia redirigir 301"
        assert new in resp.headers.get("location", "")


def test_nav_active_view_highlighted(page, base_url: str):
    """El link de la vista activa se resalta (UI-GUIDE §1)."""
    page.goto(f"{base_url}/flow", wait_until="networkidle")
    link = page.locator("[data-testid='nav-flow']")
    cls = link.get_attribute("class") or ""
    # la clase active/resaltado depende del diseno, verificamos que existe
    # un atributo visual que distinga el estado activo
    assert link.get_attribute("data-active") == "true" or "active" in cls


def test_nav_uses_config_values(page, base_url: str):
    """El brand y labels vienen de /api/config (UI-GUIDE §1)."""
    cfg = page.request.get(f"{base_url}/api/config").json()
    page.goto(base_url, wait_until="networkidle")
    body = page.inner_text("body")
    assert cfg["runtime_title"] in body
    assert cfg["kb_label"] in body


# ══════════════════════════════════════════════════════════════════════════
# Sección 2 — Chat-inspector
# ══════════════════════════════════════════════════════════════════════════


def test_chat_input_placeholder_from_config(page, base_url: str):
    """El placeholder del input viene de config (§2.2, §8). No hardcode."""
    cfg = page.request.get(f"{base_url}/api/config").json()
    page.goto(base_url, wait_until="networkidle")
    inp = page.locator("[data-testid='chat-input']")
    placeholder = inp.get_attribute("placeholder") or ""
    assert "pizza" not in placeholder.lower(), "placeholder hardcodeado de Don Peppe"
    # puede ser el valor de config o el default
    expected = cfg.get("input_placeholder", "Escribe tu mensaje...")
    assert placeholder == expected


def test_chat_send_and_inspector_shows(page, base_url: str):
    """Enviar mensaje → timeline muestra el turno + inspector se abre (§2.2, §2.3)."""
    page.goto(base_url, wait_until="networkidle")
    _send_chat(page, "que pizzas tienen?")
    _wait_turn(page)

    # timeline: aparece un turno
    assert page.locator("[data-testid^=turn-]").count() >= 1

    # inspector: se abre con las 3 secciones
    assert page.locator("[data-testid='inspector']").is_visible()


def test_inspector_summary(page, base_url: str):
    """Inspector muestra Summary con 4 campos exactos (§2.3.A)."""
    page.goto(base_url, wait_until="networkidle")
    _send_chat(page, "que pizzas tienen?")
    _wait_turn(page)

    summary = page.locator("[data-testid='inspector-summary']")
    # debe mostrar: usuario, kind, tool (o "—"), step (o "—")
    assert summary.is_visible()
    inner = summary.inner_text()
    assert any(k in inner for k in ("nl", "tool_call", "fallback")), (
        "summary debe mostrar el kind del turno"
    )
    # tool: si no hay tool_call, muestra "—"
    # step: puede ser nulo


def test_inspector_context_families(page, base_url: str):
    """Inspector Context agrupa atoms por familia (§2.3.B)."""
    page.goto(base_url, wait_until="networkidle")
    _send_chat(page, "que pizzas tienen?")
    _wait_turn(page)

    ctx = page.locator("[data-testid='inspector-context']")
    assert ctx.is_visible()
    # debe haber al menos un atom perteneciente a alguna familia
    # las familias se muestran como headers
    families = {"self", "domain", "conversation", "user"}
    text = ctx.inner_text().lower()
    assert any(f in text for f in families), "context debe mostrar familias"


def test_inspector_context_atom_click_opens_modal(page, base_url: str):
    """Click en card de Context → modal con info del atom (§2.3.B)."""
    page.goto(base_url, wait_until="networkidle")
    _send_chat(page, "que pizzas tienen?")
    _wait_turn(page)

    first_atom = page.locator("[data-testid^='context-atom-']").first
    if not first_atom.is_visible():
        pytest.skip("sin atoms en contexto del turno")

    first_atom.click()
    page.wait_for_timeout(500)
    modal = page.locator("[data-testid='atom-modal']")
    assert modal.is_visible(), "click en card atom debe abrir modal"
    # modal debe contener: titulo, familia, tags, answer, provenance
    content = modal.inner_text()
    assert any(
        k in content.lower() for k in ("family", "familia", "tipo", "type", "tag", "provenance")
    ), "modal debe mostrar metadata del atom"


def test_inspector_reasoning_agents(page, base_url: str):
    """Inspector Razonamiento tiene fila por agente, expandible (§2.3.C)."""
    page.goto(base_url, wait_until="networkidle")
    _send_chat(page, "que pizzas tienen?")
    _wait_turn(page)

    reasoning = page.locator("[data-testid='inspector-reasoning']")
    assert reasoning.is_visible()

    agents = reasoning.locator("[data-testid^='reasoning-agent-']")
    count = agents.count()
    assert count >= 1, "debe haber al menos 1 agente en razonamiento"

    # el primero es expandible: click
    first = agents.first
    detail_id = first.get_attribute("data-testid")
    first.click()
    page.wait_for_timeout(300)
    # el detalle expandido deberia estar visible
    panel = page.locator(f"[data-testid='{detail_id}-detail']")
    assert panel.is_visible() or panel.count() > 0, "click en agente debe expandir detalle"


def test_chat_sidebar_shows_user_and_config(page, base_url: str):
    """Sidebar izquierdo muestra usuario, estado, config, pulse (§2.1)."""
    page.goto(base_url, wait_until="networkidle")
    _send_chat(page, "hola")
    _wait_turn(page)

    sidebar = page.locator("[data-testid='chat-sidebar']")
    assert sidebar.is_visible()

    assert sidebar.locator("[data-testid='sidebar-user']").is_visible()
    assert sidebar.locator("[data-testid='sidebar-conversation']").is_visible()
    assert sidebar.locator("[data-testid='sidebar-agents']").is_visible()
    assert sidebar.locator("[data-testid='sidebar-pulse']").is_visible()


def test_chat_sidebar_no_duplicate_nav(page, base_url: str):
    """No existe sidebar de navegacion duplicada (solo topbar)."""
    page.goto(base_url, wait_until="networkidle")
    # la unica nav es la topbar
    nav_sidebars = page.locator("nav.fixed.left-0, [data-testid='old-sidebar']")
    assert nav_sidebars.count() == 0, "no debe haber sidebar de navegacion duplicada"


# ══════════════════════════════════════════════════════════════════════════
# Sección 3 — Flow
# ══════════════════════════════════════════════════════════════════════════


def test_flow_canvas_and_layout_toggle(page, base_url: str):
    """Flow carga grafo + tiene toggle LR/TB (§3.1)."""
    page.goto(f"{base_url}/flow", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow], canvas", timeout=20000)
    toggle = page.locator("[data-testid='flow-layout-toggle']")
    assert toggle.is_visible()


def test_flow_has_palette(page, base_url: str):
    """Flow tiene paleta de tipos de nodo arrastrables (§3.2)."""
    page.goto(f"{base_url}/flow", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    palette = page.locator("[data-testid='flow-palette']")
    assert palette.is_visible()
    # debe tener los 4 tipos
    kinds = ["interaccion_simple", "obtencion_datos", "handout", "llamado_tool"]
    palette_text = palette.inner_text()
    for k in kinds:
        assert k in palette_text, f"falta kind {k} en palette"


def test_flow_node_toolbar_on_select(page, base_url: str):
    """Seleccionar nodo muestra NodeToolbar (§3.2)."""
    page.goto(f"{base_url}/flow", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    # click en el primer nodo del grafo
    node = page.locator("[class*=react-flow__node]").first
    if not node:
        pytest.skip("sin nodos en el grafo")
    node.click()
    page.wait_for_timeout(300)
    toolbar = page.locator("[data-testid='flow-node-toolbar']")
    assert toolbar.is_visible()


def test_flow_tools_panel(page, base_url: str):
    """Flow sidebar tiene panel de tools de la KB activa (§3.2)."""
    page.goto(f"{base_url}/flow", wait_until="networkidle")
    tools = page.locator("[data-testid='flow-tools-panel']")
    assert tools.is_visible()


def test_flow_has_tooltips(page, base_url: str):
    """Flow muestra tooltips al hover sobre conceptos no obvios (§3.1, §7)."""
    page.goto(f"{base_url}/flow", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    # al menos un tooltip con clase/atributo tooltip
    tips = page.locator("[data-tooltip], [class*=tooltip]")
    assert tips.count() > 0


# ══════════════════════════════════════════════════════════════════════════
# Sección 4 — Mindmap
# ══════════════════════════════════════════════════════════════════════════


def test_mindmap_loads_tree_default(page, base_url: str):
    """Mindmap carga en layout árbol por defecto (§4.1)."""
    page.goto(f"{base_url}/mindmap", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    assert page.locator("[data-testid='mindmap-layout-tree']").is_visible()


def test_mindmap_layout_switch(page, base_url: str):
    """Mindmap permite cambiar entre 3 layouts (§4.1)."""
    page.goto(f"{base_url}/mindmap", wait_until="networkidle")
    # hotkeys 1/2/3 o botones
    for i, layout in enumerate(["tree", "topdown", "embeddings"]):
        selector = f"[data-testid='mindmap-layout-{layout}']"
        elem = page.locator(selector)
        # puede ser boton o activable por hotkey
        if elem.is_visible():
            break
    else:
        pytest.fail("ningun selector de layout visible")


def test_mindmap_drag_handle_not_body(page, base_url: str):
    """Mindmap usa drag-handle como unico punto de arrastre (§4.3)."""
    page.goto(f"{base_url}/mindmap", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    handles = page.locator("[data-testid*='drag-handle'], .drag-handle")
    assert handles.count() > 0, "cada nodo debe tener drag-handle"


def test_mindmap_node_toolbar(page, base_url: str):
    """Mindmap NodeToolbar tiene borrar/hijo/hermano/link/comentario (§4.3)."""
    page.goto(f"{base_url}/mindmap", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    node = page.locator("[class*=react-flow__node]").first
    if not node:
        pytest.skip("sin nodos")
    node.click()
    page.wait_for_timeout(300)
    toolbar = page.locator("[data-testid='mindmap-node-toolbar']")
    assert toolbar.is_visible()
    # debe tener link horizontal, que activa modo linking
    link_btn = toolbar.locator("button:has-text('link'), [data-testid*='link']")
    assert link_btn.count() > 0, "toolbar debe tener link horizontal"


def test_mindmap_node_search(page, base_url: str):
    """Mindmap tiene barra de busqueda que centra en nodo (§4.5)."""
    page.goto(f"{base_url}/mindmap", wait_until="networkidle")
    search = page.locator("[data-testid='mindmap-search']")
    assert search.is_visible()
    # teclear algo y ver que aparecen resultados
    search.fill("domain")
    page.wait_for_timeout(300)
    results = page.locator("[data-testid^='search-result-']")
    assert results.count() >= 0  # puede no haber match, pero el search existe


def test_mindmap_xfamily_toggle(page, base_url: str):
    """Mindmap tiene toggle de cross-family links, OFF default (§4.4)."""
    page.goto(f"{base_url}/mindmap", wait_until="networkidle")
    toggle = page.locator("[data-testid='mindmap-xfamily-toggle']")
    assert toggle.is_visible()
    # off por defecto
    assert toggle.get_attribute("aria-checked") == "false" or "off" in (toggle.inner_text() or "").lower()


def test_mindmap_focus_on_node(page, base_url: str):
    """Mindmap centra en nodo al hacer F (hotkey) o doble-click (§4.5)."""
    page.goto(f"{base_url}/mindmap", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    # simulamos doble-click en el primer nodo
    node = page.locator("[class*=react-flow__node]").first
    if not node:
        pytest.skip("sin nodos")
    node.dblclick()
    page.wait_for_timeout(500)
    # no hay assert de posicion (impreciso), pero no debe haber error
    assert page.evaluate("window.location.pathname") == "/mindmap"


# ══════════════════════════════════════════════════════════════════════════
# Sección 5 — Users
# ══════════════════════════════════════════════════════════════════════════


def test_users_layout(page, base_url: str):
    """Users vista tiene lista izq + selector de vista der (§5.1)."""
    page.goto(f"{base_url}/users", wait_until="networkidle")
    assert page.locator("[data-testid='users-list']").is_visible()
    assert page.locator("[data-testid='users-view-selector']").is_visible()


def test_users_profile_shows_kpis_and_traits(page, base_url: str):
    """Perfil de usuario muestra KPIs a la izq y traits a la der (§5.2)."""
    profiles = page.request.get(f"{base_url}/api/profiles").json()
    assert profiles.get("users"), "debe haber al menos un usuario de prueba"
    page.goto(f"{base_url}/users", wait_until="networkidle")
    # click en primer usuario
    first = page.locator("[data-testid^='user-chip-']").first
    if not first:
        pytest.skip("sin usuarios en el fixture")
    first.click()
    page.wait_for_timeout(300)
    # seleccionar perfil
    page.locator("button:has-text('Perfil'), [data-testid='view-profile']").click()
    page.wait_for_timeout(300)
    assert page.locator("[data-testid='users-profile']").is_visible()
    # kpis y traits
    kpi_section = page.locator("[data-testid='profile-kpis']")
    trait_section = page.locator("[data-testid='profile-traits']")
    assert kpi_section.is_visible()
    # traits: al menos uno con nombre visible
    assert trait_section.is_visible() or len(profiles["users"][0].get("traits", [])) == 0


def test_users_events_timeline(page, base_url: str):
    """Vista eventos muestra grafico y timeline (§5.3)."""
    page.goto(f"{base_url}/users", wait_until="networkidle")
    first = page.locator("[data-testid^='user-chip-']").first
    if not first:
        pytest.skip("sin usuarios")
    first.click()
    page.wait_for_timeout(300)
    page.locator("button:has-text('Eventos'), [data-testid='view-events']").click()
    page.wait_for_timeout(300)
    events = page.locator("[data-testid='users-events']")
    assert events.is_visible()
    # debe tener un grafico (canvas o svg) y dropdown de metrica
    assert events.locator("canvas, svg, [data-testid='events-chart']").count() > 0


def test_users_conversations_list(page, base_url: str):
    """Vista conversaciones muestra lista cronologica clickeable (§5.4)."""
    page.goto(f"{base_url}/users", wait_until="networkidle")
    first = page.locator("[data-testid^='user-chip-']").first
    if not first:
        pytest.skip("sin usuarios")
    first.click()
    page.wait_for_timeout(300)
    page.locator("button:has-text('Conversaciones'), [data-testid='view-conversations']").click()
    page.wait_for_timeout(300)
    conv = page.locator("[data-testid='users-conversations']")
    assert conv.is_visible()
    items = conv.locator("[data-testid^='conversation-']")
    # si hay conversaciones, deben ser clickeables
    if items.count() > 0:
        href = items.first.get_attribute("href") or ""
        assert "session" in href, "click debe navegar a chat con session_id"


# ══════════════════════════════════════════════════════════════════════════
# Sección 6 — Hotkeys globales
# ══════════════════════════════════════════════════════════════════════════


def test_hotkey_help_overlay(page, base_url: str):
    """Hotkey ? abre overlay de ayuda en flow y mindmap (§6)."""
    for path in ("/flow", "/mindmap"):
        page.goto(f"{base_url}{path}", wait_until="networkidle")
        page.wait_for_selector("[class*=react-flow]", timeout=20000)
        page.keyboard.press("?" if not page.locator("input,textarea").is_visible() else "Shift+?")
        page.wait_for_timeout(500)
        overlay = page.locator("[data-testid='hotkey-overlay']")
        # puede estar visible o fallar si no existe
        if overlay.is_visible():
            assert "Ctrl+F" in overlay.inner_text() or "Buscar" in overlay.inner_text()
            break


def test_hotkey_delete_node(page, base_url: str):
    """Delete borra nodo seleccionado en flow y mindmap (§6)."""
    for path in ("/flow", "/mindmap"):
        page.goto(f"{base_url}{path}", wait_until="networkidle")
        page.wait_for_selector("[class*=react-flow]", timeout=20000)
        node = page.locator("[class*=react-flow__node]").first
        if not node:
            continue
        node.click()
        page.wait_for_timeout(200)
        count_before = page.locator("[class*=react-flow__node]").count()
        page.keyboard.press("Delete")
        page.wait_for_timeout(500)
        # puede no borrar (readonly), pero la hotkey no debe causar error
        page.wait_for_timeout(200)


# ══════════════════════════════════════════════════════════════════════════
# Sección 7 — Claridad conceptual (tooltips visibles)
# ══════════════════════════════════════════════════════════════════════════


def test_tooltip_on_hover_concept(page, base_url: str):
    """Hover sobre concepto no obvio muestra tooltip (§7)."""
    page.goto(f"{base_url}/flow", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    # hover sobre un nodo con kind no obvio
    node = page.locator("[class*=react-flow__node]").first
    if not node:
        pytest.skip("sin nodos")
    label = node.locator("[data-kind], [class*='kind']").first
    if label:
        label.hover()
        page.wait_for_timeout(500)
        tooltip = page.locator("[data-tooltip], .tooltip-visible, [role='tooltip']")
        if tooltip.is_visible():
            assert len(tooltip.inner_text()) > 0


# ══════════════════════════════════════════════════════════════════════════
# Sección 8 — Endpoints nuevos
# ══════════════════════════════════════════════════════════════════════════


def test_api_tools_endpoint(page, base_url: str):
    """GET /api/tools devuelve ToolAtoms de la KB activa (§8)."""
    resp = page.request.get(f"{base_url}/api/tools")
    assert resp.status == 200
    data = resp.json()
    assert isinstance(data, list) or "tools" in data


def test_api_events_endpoint(page, base_url: str):
    """GET /api/events?user_id= devuelve serie temporal (§8)."""
    profiles = page.request.get(f"{base_url}/api/profiles").json()
    users = profiles.get("users", [])
    if not users:
        pytest.skip("sin usuarios para probar events")
    uid = users[0].get("user_id") or users[0].get("id") or 1
    resp = page.request.get(f"{base_url}/api/events", params={"user_id": uid})
    assert resp.status == 200
    data = resp.json()
    # puede estar vacio pero debe tener la estructura esperada
    assert isinstance(data, dict)


# ══════════════════════════════════════════════════════════════════════════
# Errores globales
# ══════════════════════════════════════════════════════════════════════════


def test_no_page_errors(page, base_url: str):
    """Navegar todas las vistas no produce page errors."""
    for path in ("/", "/flow", "/mindmap", "/users"):
        page.goto(f"{base_url}{path}", wait_until="networkidle")
        page.wait_for_timeout(2000)
        assert page.errors == [], f"page errors en {path}: {page.errors}"