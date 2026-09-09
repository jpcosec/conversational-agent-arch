"""Tools del piloto HCP: handlers, registro en config y exposicion desde la KB real.

Bug que motiva el ultimo test: los ToolAtom de ``knowledge_hcp`` traian el JSON
schema pelado (sin ``name``) y ``build_function_declarations`` los descartaba,
asi que el LLM nunca veia ``programar_recontacto`` ni ``actualizar_consentimiento``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kb_agent.agent import build_function_declarations
from kb_agent.knowledge.compiler import ContextCompiler
from kb_agent.models_sql.hcp import Consentimientos, Recontactos
from kb_agent.models_sql.identity import Base
from kb_agent.project_config import load_project_config
from kb_agent.tools import load_tool_handlers
from kb_agent.tools.hcp import actualizar_consentimiento, programar_recontacto
from knowledge_base.operations import KnowledgeOperations
from tests.conftest import REPO_ROOT

HCP_KB = REPO_ROOT / "knowledge_hcp"


@dataclass
class SessionStateStub:
    active_domain: str | None = None
    flow_node: str | None = None


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_programar_recontacto_persists_row(session: Session) -> None:
    result = programar_recontacto(session, None, {
        "hcp_id": "hcp-123", "fecha_recontacto": "2026-09-15", "franja_horaria": "tarde",
        "campania_id": "camp-01", "nota_contexto": "Quedamos en el detalle de dosis",
    })
    row = session.get(Recontactos, result["recontacto_id"])
    assert (row.fecha_recontacto, row.franja_horaria, row.campania_id, row.nota_contexto, row.user_id) == (
        "2026-09-15", "tarde", "camp-01", "Quedamos en el detalle de dosis", None,
    )


def test_actualizar_consentimiento_persists_row(session: Session) -> None:
    result = actualizar_consentimiento(session, None, {
        "hcp_id": "hcp-123", "nuevo_estado": "campaign_opt_out", "campania_id": "camp-01",
        "motivo_verbatim": "No me interesa esta campaña",
    })
    row = session.get(Consentimientos, result["consentimiento_id"])
    assert (row.nuevo_estado, row.campania_id, row.motivo_verbatim, row.user_id) == (
        "campaign_opt_out", "camp-01", "No me interesa esta campaña", None,
    )


def test_project_config_registers_hcp_handlers() -> None:
    handlers = load_tool_handlers(load_project_config(mode="serving").tool_handlers)
    assert handlers["programar_recontacto"] is programar_recontacto
    assert handlers["actualizar_consentimiento"] is actualizar_consentimiento


@pytest.mark.skipif(not HCP_KB.exists(), reason="knowledge_hcp no esta en este checkout")
def test_hcp_kb_exposes_both_tools_from_root_step() -> None:
    compiler = ContextCompiler(knowledge=KnowledgeOperations(kb_root=Path(HCP_KB)))
    compiled = compiler.compile(
        question="Prefiero que me escriba la semana que viene",
        user_id=None,
        session_state=SessionStateStub(flow_node="conversation:steps.contacto_inicial"),
    ).to_dict()
    names = {d["name"] for d in build_function_declarations(compiled)}
    assert names == {"programar_recontacto", "actualizar_consentimiento"}
