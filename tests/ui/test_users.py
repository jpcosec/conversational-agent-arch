"""Playwright de la vista Users (`/users`, sirve frontends/profiling/index.html).

Levanta la app FastAPI in-process (uvicorn en un hilo, puerto libre) con el
orquestador LLM fake. Verifica que la vista de perfilado renderiza sus
`data-testid` y que los endpoints `/api/profiles` y `/api/events` responden.

Selecciona SOLO por `data-testid` (nunca por texto ni clases). Requiere el
Chromium de Playwright y salida a internet (fuentes/CDN).

Recaba bugs: no modifica frontends. Reusa el fixture `server` in-process.
"""
from __future__ import annotations

import socket
import threading
import time
import tempfile
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


@pytest.fixture
def server():
    import uvicorn

    db = Path(tempfile.mkdtemp()) / "ui.sqlite"
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


@pytest.fixture
def page(server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=["--no-sandbox"])
        except Exception as exc:  # chromium no instalado
            pytest.skip(f"Chromium de Playwright no disponible: {exc}")
        pg = browser.new_page()
        errors: list[str] = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        pg._captured_errors = errors  # type: ignore[attr-defined]
        yield pg
        browser.close()


def _goto_users(page, server):
    page.goto(f"{server}/users", wait_until="networkidle")
    page.wait_for_timeout(3000)


# --------------------------------------------------------------------------
# Estructura estatica (topbar, layout, selector de vista) — no depende de datos
# --------------------------------------------------------------------------

def test_users_topbar_present(page, server):
    _goto_users(page, server)
    assert page.locator("[data-testid='nav-topbar']").count() == 1
    assert page.locator("[data-testid='nav-users']").count() == 1


def test_users_no_js_errors(page, server):
    _goto_users(page, server)
    errs = page._captured_errors  # type: ignore[attr-defined]
    assert errs == [], f"errores JS en /users: {errs}"


def test_users_list_container_present(page, server):
    _goto_users(page, server)
    assert page.locator("[data-testid='users-list']").count() == 1


def test_users_view_selector_present(page, server):
    _goto_users(page, server)
    assert page.locator("[data-testid='users-view-selector']").count() == 1
    # las tres vistas del selector
    assert page.locator("[data-testid='view-profile']").count() == 1
    assert page.locator("[data-testid='view-events']").count() == 1
    assert page.locator("[data-testid='view-conversations']").count() == 1


# --------------------------------------------------------------------------
# Endpoints backing de la vista
# --------------------------------------------------------------------------

def test_api_profiles_responds_200(server):
    import httpx

    r = httpx.get(f"{server}/api/profiles", timeout=10)
    assert r.status_code == 200, f"/api/profiles => {r.status_code}"
    body = r.json()
    assert "users" in body, f"/api/profiles sin 'users': {list(body.keys())}"
    assert "fichas" in body, f"/api/profiles sin 'fichas': {list(body.keys())}"
    assert isinstance(body["users"], list)


def test_api_events_responds_200(server):
    import httpx

    # sin user_id => lista vacia pero 200
    r0 = httpx.get(f"{server}/api/events", timeout=10)
    assert r0.status_code == 200, f"/api/events => {r0.status_code}"
    assert "events" in r0.json()

    # con user_id inexistente => 200 con lista vacia (no 500)
    r1 = httpx.get(f"{server}/api/events", params={"user_id": 1}, timeout=10)
    assert r1.status_code == 200, f"/api/events?user_id=1 => {r1.status_code}"
    assert "events" in r1.json()


# --------------------------------------------------------------------------
# Render de paneles: perfil / eventos / conversaciones.
# En DB fresca no hay usuarios; el panel de detalle debe seguir renderizando
# el estado vacio sin romper. Estos tests documentan comportamiento real.
# --------------------------------------------------------------------------

def test_profile_view_renders_something(page, server):
    _goto_users(page, server)
    # el panel de detalle siempre existe
    assert page.locator("#detailPanel").count() == 1
    detail_text = page.locator("#detailPanel").inner_text()
    assert detail_text.strip() != "", "detailPanel vacio (ni datos ni estado vacio)"


def test_switch_to_events_view(page, server):
    _goto_users(page, server)
    page.locator("[data-testid='view-events']").click()
    page.wait_for_timeout(500)
    # tras cambiar de vista el boton queda activo (clase 'active')
    cls = page.locator("[data-testid='view-events']").get_attribute("class") or ""
    assert "active" in cls, f"view-events no quedo activo: class={cls!r}"


def test_switch_to_conversations_view(page, server):
    _goto_users(page, server)
    page.locator("[data-testid='view-conversations']").click()
    page.wait_for_timeout(500)
    cls = page.locator("[data-testid='view-conversations']").get_attribute("class") or ""
    assert "active" in cls, f"view-conversations no quedo activo: class={cls!r}"


# --------------------------------------------------------------------------
# Reporte visual + inventario de data-testids (no falla; deja evidencia)
# --------------------------------------------------------------------------

def test_users_screenshot_and_testid_inventory(page, server):
    _goto_users(page, server)
    page.screenshot(path="/tmp/users-test.png", full_page=True)

    expected = [
        "nav-topbar",
        "nav-users",
        "users-list",
        "users-view-selector",
        "view-profile",
        "view-events",
        "view-conversations",
        # segun UI-GUIDE §5 (pueden faltar en la impl actual):
        "users-profile",
        "profile-kpis",
        "profile-traits",
        "users-events",
        "users-conversations",
    ]
    present = {tid: page.locator(f"[data-testid='{tid}']").count() for tid in expected}
    missing = [tid for tid, n in present.items() if n == 0]
    print("\n=== data-testid inventory (/users) ===")
    for tid, n in present.items():
        print(f"  {'OK ' if n else 'MISS'} {tid}: {n}")
    print(f"missing: {missing}")
    # este test es informativo: solo exige que exista el andamiaje minimo
    core = ["nav-topbar", "users-list", "users-view-selector"]
    core_missing = [t for t in core if present[t] == 0]
    assert not core_missing, f"faltan testids core: {core_missing}"
