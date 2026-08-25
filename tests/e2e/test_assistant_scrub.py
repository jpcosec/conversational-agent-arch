from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from kb_agent.models_sql.session import ChatHistory
from kb_agent.orchestrator import Orchestrator
from kb_agent.pii.scrubber import scrub

STORE_ROOT = PROJECT_ROOT / ".sldb_e2e_donpeppe"
USER = "wa:+56925555555"
HELPER_USER = "wa:+56926666666"


def test_assistant_history_is_scrubbed_before_marking_pii_scrubbed(tmp_path: Path) -> None:
    db_file = tmp_path / "assistant-scrub.sqlite"
    evidence_path = PROJECT_ROOT / "runs" / "e2e" / "assistant-scrub-check.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    raw_assistant = "Contáctame en test@example.com o al +56912345678 para confirmar."

    orch = Orchestrator(kb_root=STORE_ROOT, db_url=f"sqlite:///{db_file}")
    try:
        session = orch.SessionLocal()
        try:
            helper_user = orch.ensure_user(session, HELPER_USER)
            orch._persist_chat_history(session, user_id=helper_user.id, role="assistant", content=raw_assistant)
            session.commit()

            persisted_helper = session.scalar(
                select(ChatHistory)
                .where(ChatHistory.user_id == helper_user.id, ChatHistory.role == "assistant")
                .order_by(ChatHistory.id.desc())
            )
            assert persisted_helper is not None
            assert persisted_helper.pii_scrubbed is True
            assert "test@example.com" not in persisted_helper.content
            assert "+56912345678" not in persisted_helper.content
            assert persisted_helper.content != raw_assistant
            assert any(token in persisted_helper.content for token in ("<EMAIL_", "<PHONE_"))

            turn = orch.handle_turn(
                external_id=USER,
                message="Hola, ¿qué pizzas vegetarianas recomiendan hoy?",
                scenario="pizzeria",
            )
            assert turn["kind"] in {"nl", "tool_call", "fallback"}

            real_user = orch.ensure_user(session, USER)
            persisted_turn_assistant = session.scalar(
                select(ChatHistory)
                .where(ChatHistory.user_id == real_user.id, ChatHistory.role == "assistant")
                .order_by(ChatHistory.id.desc())
            )
            assert persisted_turn_assistant is not None
            assert persisted_turn_assistant.pii_scrubbed is True
            assert scrub(persisted_turn_assistant.content) == persisted_turn_assistant.content

            evidence_path.write_text(
                json.dumps(
                    {
                        "db_file": str(db_file),
                        "raw_assistant": raw_assistant,
                        "persisted_helper_content": persisted_helper.content,
                        "persisted_helper_pii_scrubbed": persisted_helper.pii_scrubbed,
                        "real_turn_kind": turn["kind"],
                        "real_turn_assistant_content": persisted_turn_assistant.content,
                        "real_turn_assistant_pii_scrubbed": persisted_turn_assistant.pii_scrubbed,
                    },
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
        finally:
            session.close()
    finally:
        orch.engine.dispose()
