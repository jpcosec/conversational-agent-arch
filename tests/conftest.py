"""Configuracion raiz de la suite.

Capas (ver README "Tests"):
  tests/unit         sin red: policy, compilador, state machine, modelos, orquestador con LLM fake
  tests/integration  stores SLDB reales, API FastAPI, CLI por subprocess; sin LLM
  tests/e2e          Gemini real (marker ``llm``): smoke + simulacion agente-vs-agente
  tests/ui           Playwright contra la app in-process (marker ``ui``)

Aislamiento: ninguna prueba toca ``runs/ui-chat.sqlite`` ni la KB real del
negocio. ``CHAT_DB``/``PROFILING_DB`` apuntan a un sqlite temporal por sesion y
``project_config`` se carga siempre en modo test (``test_kb_root``).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DONPEPPE_KB = REPO_ROOT / "tests" / "knowledge"       # KB de prueba (atoms tipados)
ANTONIA_KB = REPO_ROOT / "knowledge"                  # KB REAL del negocio desplegado


# ── gating por entorno ────────────────────────────────────────────────────────

def llm_available() -> bool:
    """True si hay credenciales para Gemini (Vertex ADC o API key) y no se pidio saltar."""
    if os.getenv("SKIP_LLM_TESTS") == "1":
        return False
    from dotenv import dotenv_values

    env = {**dotenv_values(REPO_ROOT / ".env"), **os.environ}
    return bool(env.get("GOOGLE_CLOUD_PROJECT") or env.get("GOOGLE_API_KEY") or env.get("GOOGLE_APPLICATION_CREDENTIALS"))


def playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return False
    return True


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    skip_llm = pytest.mark.skip(reason="sin credenciales Gemini (.env) o SKIP_LLM_TESTS=1")
    skip_ui = pytest.mark.skip(reason="playwright no instalado")
    has_llm = llm_available()
    has_ui = playwright_available()
    for item in items:
        if "llm" in item.keywords and not has_llm:
            item.add_marker(skip_llm)
        if "ui" in item.keywords and not has_ui:
            item.add_marker(skip_ui)


# ── aislamiento de DBs/config ─────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _isolate_runtime_dbs(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Nunca escribir en runs/ui-chat.sqlite desde la suite."""
    db_dir = tmp_path_factory.mktemp("runtime-db")
    os.environ["CHAT_DB"] = str(db_dir / "chat.sqlite")
    os.environ["PROFILING_DB"] = str(db_dir / "chat.sqlite")
    os.environ.pop("KB_ROOT", None)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def donpeppe_kb() -> Path:
    return DONPEPPE_KB


@pytest.fixture(scope="session")
def antonia_kb() -> Path:
    return ANTONIA_KB


@pytest.fixture()
def tmp_db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'runtime.sqlite'}"


@pytest.fixture()
def project_cfg():
    from kb_agent.project_config import load_project_config

    return load_project_config(mode="test")
