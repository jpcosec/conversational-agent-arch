"""Main entry point for the knowledge CLI."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from knowledge_base.operations import KnowledgeOperations
from knowledge_base.parser import build_parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0

    kb_root = Path(getattr(args, "kb", ".")).resolve()
    db_url = getattr(args, "db", None)
    pythonpath = getattr(args, "pythonpath", None)
    ops = KnowledgeOperations(kb_root, db_url, pythonpath=pythonpath)

    try:
        if args.command == "explore":
            if args.query:
                result = ops.explore_multi(query=args.query)
                _print_json(result)
            else:
                results = ops.explore(tag=args.tag, atom=args.atom)
                _print_json(results)
            return 0

        if args.command == "show":
            result = ops.show(args.atom_id)
            if result is None:
                print(f"Atom '{args.atom_id}' not found.", file=sys.stderr)
                return 1
            _print_json(result)
            return 0

        if args.command == "traits":
            results = ops.traits(args.user)
            _print_json(results)
            return 0

        if args.command == "self":
            result = ops.self_context()
            _print_json(result)
            return 0

        if args.command == "propose":
            result = ops.propose(args.model, args.body)
            _print_json(result)
            return 0

        if args.command == "organize":
            result = ops.organize(dry_run=args.dry_run)
            _print_json(result)
            return 0

        if args.command == "index":
            if args.index_command == "embeddings":
                result = ops.index_embeddings(model=getattr(args, "model", None))
                print(f"Embeddings: {result['processed']} processed, {result['skipped']} skipped, {result['errors']} errors")
                if result.get("store_update_error"):
                    print(f"Warning: store update failed (embeddings already written): {result['store_update_error']}", file=sys.stderr)
                return 0
            if args.index_command == "audit":
                result = ops.audit_embeddings()
                print(
                    f"Embeddings audit [{result['kb']}]: {result['with_embedding']}/{result['total']} "
                    f"con vector, {result['embeddingless_by_design']} sin vector por diseño, "
                    f"{len(result['missing'])} faltantes"
                )
                for m in result["missing"]:
                    print(f"  FALTA: {m['id']} ({m['model']})", file=sys.stderr)
                return 0 if result["ok"] else 1

        if args.command == "promote":
            result = ops.promote(args.atom_id)
            _print_json(result)
            return 0

        if args.command == "reflect":
            result = ops.reflect(db_url=args.db)
            _print_json(result)
            return 0

        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    sys.exit(main())