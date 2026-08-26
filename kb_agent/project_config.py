"""Config del proyecto/negocio activo del runtime.

Centraliza QUÉ negocio corre (KB, DB, modelo, marca) para no hardcodear
nombres ni paths en el código ni en las UIs. Fuente única de verdad:
``project.config.yaml`` en la raíz del repo.

Precedencia de valores (mayor a menor):
  1. variable de entorno (KB_ROOT, FLOW_KB_ROOT, PROFILING_DB, CHAT_DB, GEMINI_MODEL)
  2. project.config.yaml
  3. defaults embebidos

Doctrina: una KB = un negocio. ``kb_root`` y ``flow_kb_root`` deberían apuntar
al mismo store; si difieren, es responsabilidad del config.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "project.config.yaml"


@dataclass(slots=True)
class ProjectConfig:
    name: str = "Agente"
    slug: str = "default"
    kb_root: Path = field(default_factory=lambda: REPO_ROOT / "tests" / "knowledge")
    flow_kb_root: Path = field(default_factory=lambda: REPO_ROOT / "tests" / "knowledge")
    chat_db: Path = field(default_factory=lambda: REPO_ROOT / "runs" / "ui-chat.sqlite")
    profiling_db: Path = field(default_factory=lambda: REPO_ROOT / "runs" / "ui-chat.sqlite")
    model: str = "gemini-2.5-flash"
    runtime_title: str = "Auditable Agent Runtime"
    kb_label: str = "KB"
    greeting: str = "Hola. ¿En qué te puedo ayudar?"

    def to_public_dict(self) -> dict[str, Any]:
        """Vista serializable para las UIs (rutas como string relativa)."""
        return {
            "name": self.name,
            "slug": self.slug,
            "model": self.model,
            "runtime_title": self.runtime_title,
            "kb_label": self.kb_label,
            "greeting": self.greeting,
        }


def _resolve_path(value: str | os.PathLike[str]) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (REPO_ROOT / p)


def load_project_config(path: str | os.PathLike[str] | None = None) -> ProjectConfig:
    """Carga la config del proyecto: yaml + overrides por entorno.

    ``path`` (o env ``PROJECT_CONFIG``) apunta al yaml; si no existe, se usan
    solo defaults + entorno.
    """
    cfg_path = Path(path or os.getenv("PROJECT_CONFIG", DEFAULT_CONFIG_PATH))
    data: dict[str, Any] = {}
    if cfg_path.exists():
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        data = raw.get("project", raw) if isinstance(raw, dict) else {}

    ui = data.get("ui", {}) if isinstance(data.get("ui"), dict) else {}
    cfg = ProjectConfig()

    if data.get("name"):
        cfg.name = str(data["name"])
    if data.get("slug"):
        cfg.slug = str(data["slug"])
    if data.get("model"):
        cfg.model = str(data["model"])
    if data.get("kb_root"):
        cfg.kb_root = _resolve_path(data["kb_root"])
    if data.get("flow_kb_root"):
        cfg.flow_kb_root = _resolve_path(data["flow_kb_root"])
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

    # Overrides por entorno (mayor precedencia)
    if os.getenv("KB_ROOT"):
        cfg.kb_root = _resolve_path(os.environ["KB_ROOT"])
    if os.getenv("FLOW_KB_ROOT"):
        cfg.flow_kb_root = _resolve_path(os.environ["FLOW_KB_ROOT"])
    if os.getenv("CHAT_DB"):
        cfg.chat_db = _resolve_path(os.environ["CHAT_DB"])
    if os.getenv("PROFILING_DB"):
        cfg.profiling_db = _resolve_path(os.environ["PROFILING_DB"])
    if os.getenv("GEMINI_MODEL"):
        cfg.model = os.environ["GEMINI_MODEL"]

    return cfg
