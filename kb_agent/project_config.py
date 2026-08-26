"""Config del proyecto/negocio activo del runtime.

Centraliza QUÉ negocio corre (KB, DB, modelo, marca) para no hardcodear
nombres ni paths en el código ni en las UIs. Fuente única de verdad:
``project.config.yaml`` en la raíz del repo.

Doctrina: una KB = un negocio. Hay UN solo ``kb_root``; el editor de flujo y
el compilador leen SIEMPRE el mismo store (``flow_kb_root`` deriva de él).

KB según contexto (test vs serving):
  - **serving**: usa ``kb_root`` del yaml (por defecto la KB del negocio real).
  - **test**: usa ``test_kb_root`` (KB de prueba del repo). Se activa cuando se
    corre bajo pytest (``PYTEST_CURRENT_TEST``) o con ``mode="test"``.

Precedencia de valores (mayor a menor):
  1. variable de entorno (KB_ROOT, PROFILING_DB, CHAT_DB, GEMINI_MODEL)
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


@dataclass(slots=True)
class ProjectConfig:
    name: str = "Agente"
    slug: str = "default"
    kb_root: Path = field(default_factory=lambda: DEFAULT_TEST_KB_ROOT)
    chat_db: Path = field(default_factory=lambda: REPO_ROOT / "runs" / "ui-chat.sqlite")
    profiling_db: Path = field(default_factory=lambda: REPO_ROOT / "runs" / "ui-chat.sqlite")
    model: str = "gemini-2.5-flash"
    runtime_title: str = "Auditable Agent Runtime"
    kb_label: str = "KB"
    greeting: str = "Hola. ¿En qué te puedo ayudar?"
    mode: str = "serving"  # "serving" | "test" (informativo)

    @property
    def flow_kb_root(self) -> Path:
        """El editor de flujo lee el MISMO store del negocio (una KB = un negocio)."""
        return self.kb_root

    def to_public_dict(self) -> dict[str, Any]:
        """Vista serializable para las UIs (sin rutas internas)."""
        return {
            "name": self.name,
            "slug": self.slug,
            "model": self.model,
            "runtime_title": self.runtime_title,
            "kb_label": self.kb_label,
            "greeting": self.greeting,
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
) -> ProjectConfig:
    """Carga la config del proyecto: yaml + resolución test/serving + env.

    - ``path`` (o env ``PROJECT_CONFIG``) apunta al yaml.
    - ``mode`` fuerza "test" o "serving"; si es None se autodetecta (pytest -> test).

    En modo test, ``kb_root`` se resuelve desde ``test_kb_root`` del yaml (o el
    fallback ``tests/knowledge``); en serving, desde ``kb_root``.
    """
    cfg_path = Path(path or os.getenv("PROJECT_CONFIG", DEFAULT_CONFIG_PATH))
    data: dict[str, Any] = {}
    if cfg_path.exists():
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        data = raw.get("project", raw) if isinstance(raw, dict) else {}

    ui = data.get("ui", {}) if isinstance(data.get("ui"), dict) else {}
    resolved_mode = mode or ("test" if _is_test_context() else "serving")
    cfg = ProjectConfig(mode=resolved_mode)

    if data.get("name"):
        cfg.name = str(data["name"])
    if data.get("slug"):
        cfg.slug = str(data["slug"])
    if data.get("model"):
        cfg.model = str(data["model"])

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
    if ui.get("runtime_title"):
        cfg.runtime_title = str(ui["runtime_title"])
    if ui.get("kb_label"):
        cfg.kb_label = str(ui["kb_label"])
    if ui.get("greeting"):
        cfg.greeting = str(ui["greeting"]).strip()

    # Overrides por entorno (mayor precedencia; ganan sobre test/serving).
    if os.getenv("KB_ROOT"):
        cfg.kb_root = _resolve_path(os.environ["KB_ROOT"])
    if os.getenv("CHAT_DB"):
        cfg.chat_db = _resolve_path(os.environ["CHAT_DB"])
    if os.getenv("PROFILING_DB"):
        cfg.profiling_db = _resolve_path(os.environ["PROFILING_DB"])
    if os.getenv("GEMINI_MODEL"):
        cfg.model = os.environ["GEMINI_MODEL"]

    return cfg
