"""Config del proyecto/negocio activo del runtime.

Centraliza QUÉ negocio corre (KB, DB, modelo, marca, tools, server) para no
hardcodear nombres ni paths en el código ni en las UIs. Fuente única de verdad:
``project.config.yaml`` en la raíz del repo.

Doctrina: una KB = un negocio. Hay UN solo ``kb_root``; el editor de flujo y
el compilador leen SIEMPRE el mismo store (``flow_kb_root`` deriva de él).

KB según contexto (test vs serving):
  - **serving**: usa ``kb_root`` del yaml (por defecto la KB del negocio real).
  - **test**: usa ``test_kb_root`` (KB de prueba del repo). Se activa cuando se
    corre bajo pytest (``PYTEST_CURRENT_TEST``) o con ``mode="test"``.

Precedencia de valores (mayor a menor):
  1. variable de entorno (KB_ROOT, PROFILING_DB, CHAT_DB, GEMINI_MODEL, HOST, PORT)
  2. project.config.yaml (rama según contexto test/serving)
  3. defaults embebidos
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "project.config.yaml"

#: KB de prueba del repo (fallback para el modo test si no se declara otra).
DEFAULT_TEST_KB_ROOT = REPO_ROOT / "tests" / "knowledge"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


@dataclass(slots=True)
class ProjectConfig:
    name: str = "Agente"
    slug: str = "default"
    kb_root: Path = field(default_factory=lambda: DEFAULT_TEST_KB_ROOT)
    chat_db: Path = field(default_factory=lambda: REPO_ROOT / "runs" / "ui-chat.sqlite")
    profiling_db: Path = field(default_factory=lambda: REPO_ROOT / "runs" / "ui-chat.sqlite")
    model: str = DEFAULT_MODEL
    #: Fallback de ultimo recurso si la KB no declara FallbackRule. None => constante del runtime.
    fallback_message: str | None = None
    #: {tool_name: "modulo:funcion"} — handlers que ejecutan los ToolAtom de la KB.
    tool_handlers: dict[str, str] = field(default_factory=dict)
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    runtime_title: str = "Auditable Agent Runtime"
    kb_label: str = "KB"
    greeting: str = "Hola. ¿En qué te puedo ayudar?"
    input_placeholder: str = "Escribe tu mensaje..."
    mode: str = "serving"  # "serving" | "test" (informativo)
    #: Modo demo (opt-in con DEMO_MODE=1): sin orquestador ni LLM, todos los
    #: /api/* sirven ``frontends/chat/demo_data``. Nunca en modo test.
    demo_mode: bool = False

    @property
    def flow_kb_root(self) -> Path:
        """El editor de flujo lee el MISMO store del negocio (una KB = un negocio)."""
        return self.kb_root

    @property
    def chat_db_url(self) -> str:
        return f"sqlite:///{self.chat_db}"

    def to_public_dict(self) -> dict[str, Any]:
        """Vista serializable para las UIs (sin rutas internas ni handlers)."""
        return {
            "name": self.name,
            "slug": self.slug,
            "model": self.model,
            "runtime_title": self.runtime_title,
            "kb_label": self.kb_label,
            "greeting": self.greeting,
            "input_placeholder": self.input_placeholder,
            "mode": self.mode,
        }


def _resolve_path(value: str | os.PathLike[str]) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (REPO_ROOT / p)


def _is_test_context() -> bool:
    """True si estamos corriendo bajo pytest."""
    return bool(os.getenv("PYTEST_CURRENT_TEST")) or "PYTEST_VERSION" in os.environ


def load_project_config(
    path: str | os.PathLike[str] | None = None,
    *,
    mode: str | None = None,
    env: dict[str, str] | None = None,
) -> ProjectConfig:
    """Carga la config del proyecto: yaml + resolución test/serving + env.

    - ``path`` (o env ``PROJECT_CONFIG``) apunta al yaml.
    - ``mode`` fuerza "test" o "serving"; si es None se autodetecta (pytest -> test).
    - ``env`` permite inyectar el entorno (tests); por defecto ``os.environ``.

    En modo test, ``kb_root`` se resuelve desde ``test_kb_root`` del yaml (o el
    fallback ``tests/knowledge``); en serving, desde ``kb_root``.
    """
    environ: dict[str, str] = dict(os.environ) if env is None else env
    cfg_path = Path(path or environ.get("PROJECT_CONFIG", DEFAULT_CONFIG_PATH))
    data: dict[str, Any] = {}
    if cfg_path.exists():
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        data = raw.get("project", raw) if isinstance(raw, dict) else {}

    ui = data.get("ui", {}) if isinstance(data.get("ui"), dict) else {}
    server = data.get("server", {}) if isinstance(data.get("server"), dict) else {}
    tools = data.get("tools", {}) if isinstance(data.get("tools"), dict) else {}
    resolved_mode = mode or ("test" if _is_test_context() else "serving")
    cfg = ProjectConfig(mode=resolved_mode)

    if data.get("name"):
        cfg.name = str(data["name"])
    if data.get("slug"):
        cfg.slug = str(data["slug"])
    if data.get("model"):
        cfg.model = str(data["model"])
    if data.get("fallback_message"):
        cfg.fallback_message = str(data["fallback_message"]).strip()
    cfg.tool_handlers = {str(k): str(v) for k, v in tools.items() if v}

    # kb_root según contexto: test -> test_kb_root; serving -> kb_root.
    serving_kb = data.get("kb_root")
    test_kb = data.get("test_kb_root")
    if resolved_mode == "test":
        cfg.kb_root = _resolve_path(test_kb or serving_kb or DEFAULT_TEST_KB_ROOT)
    else:
        cfg.kb_root = _resolve_path(serving_kb or DEFAULT_TEST_KB_ROOT)

    if data.get("chat_db"):
        cfg.chat_db = _resolve_path(data["chat_db"])
    if data.get("profiling_db"):
        cfg.profiling_db = _resolve_path(data["profiling_db"])
    if server.get("host"):
        cfg.host = str(server["host"])
    if server.get("port"):
        cfg.port = int(server["port"])
    if ui.get("runtime_title"):
        cfg.runtime_title = str(ui["runtime_title"])
    if ui.get("kb_label"):
        cfg.kb_label = str(ui["kb_label"])
    if ui.get("greeting"):
        cfg.greeting = str(ui["greeting"]).strip()
    if ui.get("input_placeholder"):
        cfg.input_placeholder = str(ui["input_placeholder"]).strip()

    # Overrides por entorno (mayor precedencia; ganan sobre test/serving).
    if environ.get("KB_ROOT"):
        cfg.kb_root = _resolve_path(environ["KB_ROOT"])
    if environ.get("CHAT_DB"):
        cfg.chat_db = _resolve_path(environ["CHAT_DB"])
    if environ.get("PROFILING_DB"):
        cfg.profiling_db = _resolve_path(environ["PROFILING_DB"])
    if environ.get("GEMINI_MODEL"):
        cfg.model = environ["GEMINI_MODEL"]
    if environ.get("HOST"):
        cfg.host = environ["HOST"]
    if environ.get("PORT"):
        cfg.port = int(environ["PORT"])
    cfg.demo_mode = resolved_mode != "test" and environ.get("DEMO_MODE") == "1"

    return cfg
