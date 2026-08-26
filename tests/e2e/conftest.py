"""Fixtures e2e: Gemini real. Todo lo que cuelga de tests/e2e lleva marker ``llm``."""
from __future__ import annotations

from pathlib import Path

import pytest
from dotenv import load_dotenv

from tests.conftest import REPO_ROOT

load_dotenv(REPO_ROOT / ".env")

SIM_REPORTS_DIR = REPO_ROOT / "runs" / "simulation"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if "llm" not in item.keywords:
            item.add_marker(pytest.mark.llm)


@pytest.fixture(scope="session")
def gemini_client():
    from kb_agent.llm import make_gemini_client

    return make_gemini_client()


@pytest.fixture(scope="session")
def json_llm(gemini_client, ):
    from kb_agent.project_config import load_project_config
    from tests.e2e.simulation.llm import GeminiJsonLLM

    return GeminiJsonLLM(gemini_client, load_project_config(mode="test").model)


@pytest.fixture(scope="session")
def sim_reports_dir() -> Path:
    SIM_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return SIM_REPORTS_DIR
