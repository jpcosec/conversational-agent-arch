"""project.config.yaml -> ProjectConfig: unica fuente de verdad del negocio activo."""
from __future__ import annotations

from pathlib import Path

import pytest

from kb_agent.project_config import DEFAULT_MODEL, DEFAULT_TEST_KB_ROOT, REPO_ROOT, ProjectConfig, load_project_config

YAML = """
project:
  name: "Negocio X"
  slug: negociox
  kb_root: kbs/real
  test_kb_root: tests/knowledge
  chat_db: runs/x.sqlite
  profiling_db: runs/x-prof.sqlite
  model: gemini-9
  fallback_message: "  Ups, no lo se.  "
  tools:
    crear_reserva: kb_agent.tools.reservas:crear_reserva
    vacia: ""
  server:
    host: 0.0.0.0
    port: 9001
  ui:
    runtime_title: "Titulo"
    kb_label: "X · KB"
    greeting: >-
      Hola
      mundo
"""


@pytest.fixture()
def cfg_path(tmp_path: Path) -> Path:
    p = tmp_path / "project.config.yaml"
    p.write_text(YAML, encoding="utf-8")
    return p


def test_serving_mode_reads_business_kb_and_all_sections(cfg_path: Path) -> None:
    cfg = load_project_config(cfg_path, mode="serving", env={})

    assert cfg.name == "Negocio X"
    assert cfg.slug == "negociox"
    assert cfg.kb_root == REPO_ROOT / "kbs" / "real"
    assert cfg.chat_db == REPO_ROOT / "runs" / "x.sqlite"
    assert cfg.profiling_db == REPO_ROOT / "runs" / "x-prof.sqlite"
    assert cfg.chat_db_url == f"sqlite:///{REPO_ROOT / 'runs' / 'x.sqlite'}"
    assert cfg.model == "gemini-9"
    assert cfg.fallback_message == "Ups, no lo se."
    assert cfg.tool_handlers == {"crear_reserva": "kb_agent.tools.reservas:crear_reserva"}  # los vacios se ignoran
    assert (cfg.host, cfg.port) == ("0.0.0.0", 9001)
    assert cfg.runtime_title == "Titulo"
    assert cfg.kb_label == "X · KB"
    assert cfg.greeting == "Hola mundo"
    assert cfg.mode == "serving"


def test_test_mode_uses_test_kb_root(cfg_path: Path) -> None:
    cfg = load_project_config(cfg_path, mode="test", env={})
    assert cfg.kb_root == REPO_ROOT / "tests" / "knowledge"
    assert cfg.flow_kb_root == cfg.kb_root  # una KB = un negocio
    assert cfg.mode == "test"


def test_pytest_context_autodetects_test_mode(cfg_path: Path) -> None:
    # Bajo pytest, PYTEST_CURRENT_TEST esta definido -> modo test sin pedirlo.
    cfg = load_project_config(cfg_path)
    assert cfg.mode == "test"
    assert cfg.kb_root == REPO_ROOT / "tests" / "knowledge"


def test_env_overrides_win_over_yaml(cfg_path: Path, tmp_path: Path) -> None:
    env = {
        "KB_ROOT": str(tmp_path / "otra-kb"),
        "CHAT_DB": "runs/env.sqlite",
        "PROFILING_DB": str(tmp_path / "p.sqlite"),
        "GEMINI_MODEL": "gemini-env",
        "HOST": "127.0.0.9",
        "PORT": "7777",
    }
    cfg = load_project_config(cfg_path, mode="serving", env=env)
    assert cfg.kb_root == tmp_path / "otra-kb"
    assert cfg.chat_db == REPO_ROOT / "runs" / "env.sqlite"  # relativo -> REPO_ROOT
    assert cfg.profiling_db == tmp_path / "p.sqlite"
    assert cfg.model == "gemini-env"
    assert (cfg.host, cfg.port) == ("127.0.0.9", 7777)


def test_project_config_env_selects_yaml_path(cfg_path: Path) -> None:
    cfg = load_project_config(env={"PROJECT_CONFIG": str(cfg_path)}, mode="serving")
    assert cfg.name == "Negocio X"


def test_missing_yaml_falls_back_to_defaults(tmp_path: Path) -> None:
    cfg = load_project_config(tmp_path / "nope.yaml", mode="serving", env={})
    assert cfg == ProjectConfig(mode="serving")
    assert cfg.kb_root == DEFAULT_TEST_KB_ROOT
    assert cfg.model == DEFAULT_MODEL
    assert cfg.tool_handlers == {}
    assert cfg.fallback_message is None


def test_public_dict_hides_paths_and_handlers(cfg_path: Path) -> None:
    public = load_project_config(cfg_path, mode="serving", env={}).to_public_dict()
    assert set(public) == {"name", "slug", "model", "runtime_title", "kb_label", "greeting", "mode"}


def test_repo_config_declares_business_tools_and_test_kb() -> None:
    """El project.config.yaml del repo debe ser cargable y coherente."""
    cfg = load_project_config(mode="test", env={})
    assert cfg.kb_root.exists() and (cfg.kb_root / ".sldb").exists()
    assert "crear_reserva" in cfg.tool_handlers
