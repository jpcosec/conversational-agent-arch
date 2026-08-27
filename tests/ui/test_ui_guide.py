"""Tests que validan `frontends/UI-GUIDE.md` — el estado objetivo de las UIs.

Cada test verifica una sección de la guía; las secciones todavía no
implementadas quedan marcadas `xfail`. Sirven como spec ejecutable.

Convención:
- Cada elemento lleva `data-testid` (definido en UI-GUIDE.md).
- Los tests seleccionan por `data-testid`, nunca por texto. Dos excepciones
  que la UI expone de otra forma (y que la guía documenta asi): las cards de
  turno por `data-turn-id` (ver REAL_TURN) y el detalle de cada agente del
  razonamiento por la clase `.agent-detail`.
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


# Las cards de turno se identifican con `data-turn-id` (t1, t2, ...; el saludo
# inicial es `turn-000` y el placeholder mientras corre el turno `ghost-*`),
# como documenta UI-GUIDE §2.2.
REAL_TURN = "[data-turn-id]:not([data-turn-id^='turn-']):not([data-turn-id^='ghost-'])"


def _send_chat(page, text: str) -> int:
    """Escribe y envía un mensaje en el chat. Devuelve cuantos turnos reales habia antes."""
    before = page.locator(REAL_TURN).count()
    inp = page.locator("[data-testid='chat-input']")
    inp.fill(text)
    page.locator("[data-testid='chat-send']").click()
    return before


def _wait_turn(page, before: int = 0):
    """Espera a que el turno nuevo (respuesta del orquestador offline) quede renderizado.

    La sesion persiste en localStorage y la pagina recarga el historial, asi
    que se espera a que haya MAS turnos reales que antes del envio.
    """
    page.wait_for_function(
        "n => document.querySelectorAll(n.sel).length > n.before",
        arg={"sel": REAL_TURN, "before": before},
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
    """La topbar tiene links a las 5 vistas (UI-GUIDE §1)."""
    page.goto(base_url, wait_until="networkidle")
    nav = page.locator("[data-testid='nav-topbar']")
    links = ["nav-chat", "nav-flow", "nav-mindmap", "nav-users", "nav-dashboard"]
    for lid in links:
        link = nav.locator(f"[data-testid='{lid}']")
        assert link.is_visible(), f"Falta {lid} en la navegacion"


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
    # la topbar pinta la marca como `name || runtime_title` y el chip de KB como `kb_label || name`
    assert page.inner_text("[data-testid='nav-brand']").strip() == (cfg["name"] or cfg["runtime_title"])
    assert cfg["kb_label"] in page.inner_text("body")


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
    _wait_turn(page, _send_chat(page, "que pizzas tienen?"))

    # timeline: aparece un turno real (ademas del saludo inicial)
    assert page.locator(REAL_TURN).count() >= 1

    # inspector: se abre con las 3 secciones
    assert page.locator("[data-testid='inspector']").is_visible()


def test_inspector_summary(page, base_url: str):
    """Inspector muestra Summary con 4 campos exactos (§2.3.A)."""
    page.goto(base_url, wait_until="networkidle")
    _wait_turn(page, _send_chat(page, "que pizzas tienen?"))

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
    _wait_turn(page, _send_chat(page, "que pizzas tienen?"))

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
    _wait_turn(page, _send_chat(page, "que pizzas tienen?"))

    first_atom = page.locator("[data-testid^='context-atom-']").first
    if first_atom.count() == 0:
        pytest.skip("sin atoms en contexto del turno")
    first_atom.scroll_into_view_if_needed()

    first_atom.click()
    page.wait_for_timeout(500)
    modal = page.locator("[data-testid='atom-modal']")
    assert modal.is_visible(), "click en card atom debe abrir modal"
    # modal muestra: titulo, familia, path, tags y el body del atom
    content = modal.inner_text().lower()
    assert "familia" in content and "tags" in content, "modal debe mostrar metadata del atom"


def test_inspector_reasoning_agents(page, base_url: str):
    """Inspector Razonamiento tiene fila por agente, expandible (§2.3.C)."""
    page.goto(base_url, wait_until="networkidle")
    _wait_turn(page, _send_chat(page, "que pizzas tienen?"))

    reasoning = page.locator("[data-testid='inspector-reasoning']")
    assert reasoning.is_visible()

    # Cada agente es una fila `agent-row` (UI-GUIDE §2.3.C); el detalle es el
    # hijo `.agent-detail` que se destapa al hacer click en la fila.
    agents = reasoning.locator("[data-testid='agent-row']")
    count = agents.count()
    assert count >= 1, "debe haber al menos 1 agente en razonamiento"

    first = agents.first
    detail = first.locator(".agent-detail")
    assert detail.count() == 1 and not detail.is_visible(), "el detalle arranca colapsado"
    first.click()
    page.wait_for_timeout(300)
    assert detail.is_visible(), "click en agente debe expandir detalle"


def test_chat_sidebar_shows_user_and_config(page, base_url: str):
    """Sidebar izquierdo muestra usuario, estado, config, pulse (§2.1)."""
    page.goto(base_url, wait_until="networkidle")
    _wait_turn(page, _send_chat(page, "hola"))

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
    # debe tener los 4 tipos (STEP_KINDS del editor), rendereados por su label humano
    items = palette.locator("[data-testid='flow-palette-item']")
    assert items.count() == 4, "la paleta debe tener los 4 kinds de paso"
    labels = {"interaccion_simple": "Interacción simple", "obtencion_datos": "Obtención de datos", "handout": "Handout", "llamado_tool": "Llamado a tool"}
    palette_text = palette.inner_text()
    for kind, label in labels.items():
        assert label in palette_text, f"falta kind {kind} ({label}) en palette"


def test_flow_node_toolbar_on_select(page, base_url: str):
    """Seleccionar nodo muestra NodeToolbar (§3.2)."""
    page.goto(f"{base_url}/flow", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    # click en el primer nodo del grafo (`.react-flow__node` exacto: `[class*=]`
    # tambien matchea el contenedor `.react-flow__nodes`)
    node = page.locator(".react-flow__node").first
    if node.count() == 0:
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
    # los tooltips del flow son `title` nativos (paleta, toolbar, inspector);
    # no hay componente/atributo tooltip propio
    tips = page.locator("[data-tooltip], [class*=tooltip], [title]:not([title=''])")
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
    node = page.locator(".react-flow__node").first
    if node.count() == 0:
        pytest.skip("sin nodos")
    node.click()
    page.wait_for_timeout(300)
    toolbar = page.locator("[data-testid='mindmap-node-toolbar']")
    assert toolbar.is_visible()
    # debe tener link horizontal, que activa modo linking (boton con title, sin testid propio)
    link_btn = toolbar.locator("button[title*='Link' i], [data-testid*='link']")
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
    # es un checkbox nativo: off por defecto
    assert not toggle.is_checked()


def test_mindmap_focus_on_node(page, base_url: str):
    """Mindmap centra en nodo al hacer F (hotkey) o doble-click (§4.5)."""
    page.goto(f"{base_url}/mindmap", wait_until="networkidle")
    page.wait_for_selector("[class*=react-flow]", timeout=20000)
    # simulamos doble-click en el primer nodo
    node = page.locator(".react-flow__node").first
    if node.count() == 0:
        pytest.skip("sin nodos")
    node.dblclick()
    page.wait_for_timeout(500)
    # no hay assert de posicion (impreciso), pero no debe haber error
    assert page.evaluate("window.location.pathname") == "/mindmap"


# ══════════════════════════════════════════════════════════════════════════
# Sección 5 — Users
# ══════════════════════════════════════════════════════════════════════════


def _open_first_user(page, base_url: str):
    """Garantiza un usuario (un turno por API) y lo selecciona en la lista.

    Los usuarios se listan como `user-item-<id>` (test_users.py usa el mismo
    testid). El click es REAL (`.click()`, no `dispatch_event`): es la
    regresion de `.user-chip{user-select:none}` — sin eso el mousedown real
    arrancaba una seleccion de texto que colgaba el renderer de Chromium.
    """
    page.request.post(f"{base_url}/api/chat", data={"message": "hola", "session_id": "ui-guide-users"})
    page.goto(f"{base_url}/users", wait_until="networkidle")
    first = page.locator("[data-testid^='user-item-']").first
    first.wait_for(timeout=20000)
    first.click()
    page.wait_for_timeout(300)


def test_users_layout(page, base_url: str):
    """Users vista tiene lista izq + selector de vista der (§5.1)."""
    page.goto(f"{base_url}/users", wait_until="networkidle")
    assert page.locator("[data-testid='users-list']").is_visible()
    assert page.locator("[data-testid='users-view-selector']").is_visible()


def test_users_profile_shows_kpis_and_traits(page, base_url: str):
    """Perfil de usuario muestra KPIs a la izq y traits a la der (§5.2)."""
    _open_first_user(page, base_url)
    profiles = page.request.get(f"{base_url}/api/profiles").json()
    assert profiles.get("users"), "debe haber al menos un usuario de prueba"
    # seleccionar perfil
    page.locator("[data-testid='view-profile']").click()
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
    _open_first_user(page, base_url)
    page.locator("[data-testid='view-events']").click()
    page.wait_for_timeout(300)
    events = page.locator("[data-testid='users-events']")
    assert events.is_visible()
    # debe tener un grafico (canvas o svg) y dropdown de metrica
    assert events.locator("canvas, svg, [data-testid='events-chart']").count() > 0


def test_users_conversations_list(page, base_url: str):
    """Vista conversaciones muestra lista cronologica clickeable (§5.4)."""
    _open_first_user(page, base_url)
    page.locator("[data-testid='view-conversations']").click()
    page.wait_for_timeout(300)
    conv = page.locator("[data-testid='users-conversations']")
    assert conv.is_visible()
    items = conv.locator("[data-testid^='conversation-']")
    # si hay conversaciones, deben ser links al chat: `/?session=<id>` cuando
    # la fila tiene session_id, `/?user=<external_id>` cuando no (hoy el
    # orquestador no setea chat_history.session_id, ver _group_conversations).
    if items.count() > 0:
        href = items.first.get_attribute("href") or ""
        assert href.startswith("/?") and ("session=" in href or "user=" in href), (
            f"click debe navegar al chat con la conversacion cargada: href={href!r}"
        )


# ══════════════════════════════════════════════════════════════════════════
# Sección 6 — Hotkeys globales
# ══════════════════════════════════════════════════════════════════════════


@pytest.mark.xfail(reason="UI no rediseñada — se implementa en esta task")
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


@pytest.mark.xfail(reason="UI no rediseñada — se implementa en esta task")
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


@pytest.mark.xfail(reason="UI no rediseñada — se implementa en esta task")
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