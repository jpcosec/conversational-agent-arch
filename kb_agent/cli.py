"""CLI local para conversar con el agente del negocio activo (project.config.yaml).

Uso:
  python -m kb_agent.cli
  python -m kb_agent.cli --db runs/local-chat.sqlite --kb /ruta/a/otra/kb --user wa:+56900000000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from kb_agent.db_check import check_db_revision
from kb_agent.orchestrator import Orchestrator
from kb_agent.project_config import REPO_ROOT, load_project_config

load_dotenv(REPO_ROOT / ".env")

DEFAULT_USER = "local:demo"


def build_parser() -> argparse.ArgumentParser:
    cfg = load_project_config()
    parser = argparse.ArgumentParser(description=f"Chat local con el orquestador ({cfg.name})")
    parser.add_argument("--kb", default=str(cfg.kb_root), help=f"Ruta al root del KB (default: {cfg.kb_root})")
    parser.add_argument("--db", default=str(REPO_ROOT / "runs" / "local-chat.sqlite"), help="Ruta al sqlite local persistente")
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
    cfg = load_project_config()
    kb_root = Path(args.kb).resolve()
    db_path = Path(args.db).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{db_path}"

    # Chequeo no bloqueante: create_all() crea tablas que faltan pero nunca
    # altera una tabla existente. Si la base esta atrasada respecto de
    # alembic/versions, avisamos ANTES de que reviente en el primer turno
    # con un OperationalError opaco (ver docs/OPERATIONS.md#migraciones).
    status = check_db_revision(db_url)
    if not status.ok:
        print(f"[WARNING] {status.message}", file=sys.stderr)

    orch = Orchestrator.from_config(cfg, db_url=db_url, kb_root=kb_root)

    print("=" * 60)
    print(f"  Chat local — {cfg.name} ({cfg.model})")
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

            turn = orch.handle_turn(external_id=args.user, message=msg, scenario=scenario)
            scenario = None

            print(f"Bot > {_format_reply(turn)}")
            # Rastro del turno: step, decision de cada agente, tool.
            print(
                json.dumps(
                    {**turn.get("decisions", {}), "traits_after": turn.get("traits_after")},
                    ensure_ascii=False,
                    indent=2,
                )
            )
    finally:
        orch.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
