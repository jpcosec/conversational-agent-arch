"""Entry point real del CLI ``python -m knowledge_base`` (subprocess) sobre la KB Antonia."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kb_agent.models_sql.identity import Base, UserTraits, Users
from kb_agent.models_sql.session import SessionNode, SessionState
from tests.support.sldb_seed import REPO_ROOT

USER = "wa:+56900000000"


def _knowledge(kb: Path, *args: str) -> dict | list:
    cmd = [sys.executable, "-m", "knowledge_base", "--kb", str(kb), "--pythonpath", ".", *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=REPO_ROOT)
    assert r.returncode == 0, f"{' '.join(cmd)}\nstdout:{r.stdout}\nstderr:{r.stderr}"
    return json.loads(r.stdout)


def test_context_command_joins_sql_and_sldb(antonia_kb: Path, tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'cli.db'}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        user = Users(external_id=USER, channel="whatsapp")
        s.add(user)
        s.flush()
        s.add(SessionState(user_id=user.id, current_node=SessionNode.IDLE, flow_node="conversation:steps.onboarding", flow_slots={"missing_slots": ["nombre"]}))
        s.add(UserTraits(user_id=user.id, trait_id="trait-antonia-primera-vez", confidence=0.9, source="test"))
        s.commit()
    engine.dispose()

    result = _knowledge(antonia_kb, "--db", db_url, "context", "--user", USER)
    assert set(result) == {"step", "traits", "self"}
    assert result["step"]["flow_node"] == "conversation:steps.onboarding" and result["step"]["missing_slots"] == ["nombre"]
    assert [t["trait_id"] for t in result["traits"]] == ["trait-antonia-primera-vez"]
    assert result["self"]["identity"][0]["id"] == "self-antonia"
    assert len(result["self"]["boundaries"]) == 2


def test_show_and_unknown_atom_exit_codes(antonia_kb: Path) -> None:
    assert _knowledge(antonia_kb, "show", "self-antonia")["_model"] == "SelfDeclaration"
    r = subprocess.run([sys.executable, "-m", "knowledge_base", "--kb", str(antonia_kb), "--pythonpath", ".", "show", "nope"], capture_output=True, text=True, cwd=REPO_ROOT)
    assert r.returncode == 1 and "not found" in r.stderr
