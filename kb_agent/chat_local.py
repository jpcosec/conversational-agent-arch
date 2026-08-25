"""CLI local real para conversar con el agente.

Uso:
  python -m kb_agent.chat_local
  python -m kb_agent.chat_local --db runs/local-chat.sqlite --kb .sldb_e2e_donpeppe --user wa:+56900000000 --scenario pizzeria
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from kb_agent.agent import CANONICAL_FALLBACK_RESPONSE
from kb_agent.orchestrator import Orchestrator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
DEFAULT_KB_ROOT = PROJECT_ROOT / ".sldb_e2e_donpeppe"
DEFAULT_DB_PATH = PROJECT_ROOT / "runs" / "local-chat.sqlite"
DEFAULT_USER = "local:demo"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chat local real con el orquestador")
    parser.add_argument("--kb", default=str(DEFAULT_KB_ROOT), help="Ruta al root del KB (default: .sldb_e2e_donpeppe)")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Ruta al sqlite local persistente")
    parser.add_argument("--user", default=DEFAULT_USER, help="external_id persistente del usuario local")
    parser.add_argument("--scenario", default=None, help="Scenario inicial opcional; luego se recupera desde SessionState")
    return parser


def _format_reply(turn: dict) -> str:
    reply = turn.get("reply")
    if isinstance(reply, dict):
        return json.dumps(reply, ensure_ascii=False)
    return str(reply)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kb_root = Path(args.kb).resolve()
    db_path = Path(args.db).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    orch = Orchestrator(kb_root=kb_root, db_url=f"sqlite:///{db_path}")

    print("=" * 60)
    print("  Chat local real — Orchestrator + Gemini + SLDB + SQLite")
    print(f"  KB: {kb_root}")
    print(f"  DB: {db_path}")
    print(f"  User: {args.user}")
    print("  Comandos: /exit, /scenario <dominio>, /reflect")
    print("=" * 60)

    scenario = args.scenario
    try:
        while True:
            try:
                msg = input("\nTu > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nChau!")
                return 0

            if not msg:
                continue
            if msg.lower() in {"/exit", "exit", "quit", "salir"}:
                print("Chau!")
                return 0
            if msg.startswith("/scenario "):
                scenario = msg.split(" ", 1)[1].strip() or None
                print(f"[ok] scenario actual = {scenario}")
                continue
            if msg == "/reflect":
                generated = orch.run_reflector()
                print(json.dumps({"generated": generated}, ensure_ascii=False, indent=2))
                continue

            turn = orch.handle_turn(
                external_id=args.user,
                message=msg,
                scenario=scenario,
            )
            scenario = None

            print(f"Bot > {_format_reply(turn)}")
            print(
                json.dumps(
                    {
                        "kind": turn.get("kind"),
                        "scenario_effective": turn.get("scenario_effective"),
                        "scenario_source": turn.get("scenario_source"),
                        "state_trace": turn.get("state_trace"),
                        "traits_after": turn.get("traits_after"),
                        "system_turn": turn.get("system_turn"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            if turn.get("reply") == CANONICAL_FALLBACK_RESPONSE:
                continue
    finally:
        orch.engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
