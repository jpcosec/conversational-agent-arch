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

        if args.command == "step":
            if args.step_command == "next":
                result = ops.step_next(args.user)
                _print_json(result)
                return 0
            print(f"Unknown step subcommand: {args.step_command}", file=sys.stderr)
            return 1

        if args.command == "traits":
            results = ops.traits(args.user)
            _print_json(results)
            return 0

        if args.command == "self":
            result = ops.self_context()
            _print_json(result)
            return 0

        if args.command == "context":
            result = ops.context(args.user)
            _print_json(result)
            return 0

        if args.command == "propose":
            result = ops.propose(args.model, args.body)
            _print_json(result)
            return 0

        if args.command == "index":
            if args.index_command == "embeddings":
                result = ops.index_embeddings()
                print(f"Embeddings: {result['processed']} processed, {result['skipped']} skipped, {result['errors']} errors")
                return 0
            if args.index_command == "hierarchy":
                result = ops.index_hierarchy()
                print(f"Hierarchy: {result.get('tags', 0)} tags, {result.get('new_parent_relations', 0)} new relations")
                return 0

        if args.command == "promote":
            result = ops.promote(args.atom_id)
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