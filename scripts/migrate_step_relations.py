"""Migracion de una vez: el diagrama de conversacion pasa de texto libre a relaciones tipadas.

Antes, cada ``ConversationStep`` declaraba en campos de texto (``allowed_transitions``,
``grounding_atoms``, ``tool_ref``) a que steps podia pasar, que atoms lo groundeaban y
que tool ejecutaba; el compilador partia esos strings por coma y filtraba referencias
colgantes a mano. Ahora eso son aristas de kgdb: ``RelationTypeDoc`` (``transitions_to``,
``grounded_by``, ``uses_tool``) + un ``RelationDoc`` por arista, documentos del store de la
KB que el ingest tipado valida (una referencia a un documento inexistente es un error de
ensamblaje, no un ``if`` defensivo en el runtime).

Uso (idempotente; corre ``kgdb init`` antes si el store no lo tuvo)::

    python scripts/migrate_step_relations.py knowledge            # la KB de Antonia
    python scripts/migrate_step_relations.py tests/knowledge --pythonpath .

Lee los campos viejos MIENTRAS existan en el frontmatter/secciones (payload crudo del
documento); despues de correrlo, los campos se sacan del modelo y de los atoms.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pron.world import World

#: Los tres verbos del diagrama de conversacion: sujeto siempre un ConversationStep.
RELATION_TYPES: list[dict] = [
    {
        "name": "transitions_to", "axis": "WHEN", "cardinality": "many_to_many",
        "source_types": ["ConversationStep"], "target_types": ["ConversationStep"],
        "description": "Allowed move from one conversation step to another. The orchestrator may only navigate along these edges.",
    },
    {
        "name": "grounded_by", "axis": "WHY", "cardinality": "many_to_many",
        "source_types": ["ConversationStep"], "target_types": [],
        "description": "A document whose content grounds the step's instructions: it enters the turn's bundle whenever the step is active.",
    },
    {
        "name": "uses_tool", "axis": "HOW", "cardinality": "many_to_one",
        "source_types": ["ConversationStep"], "target_types": ["ToolAtom"],
        "description": "The tool a llamado_tool step executes.",
    },
]

_PLACEHOLDERS = {"", "ninguno", "ninguna", "ninguna (paso terminal)", "no aplica", "n/a", "none"}


def _split(text: str | None) -> list[str]:
    parts = [p.strip() for p in str(text or "").replace("\n", ",").split(",")]
    return [p for p in parts if p.lower() not in _PLACEHOLDERS]


def ensure_relation_types(world: World) -> list[str]:
    """Declara los tres RelationTypeDoc si faltan. Devuelve los creados."""
    existing = {d.name for d in world.store.docs_of("RelationTypeDoc")}
    created = []
    for spec in RELATION_TYPES:
        name = f"rt-{spec['name']}"
        if name in existing:
            continue
        payload = {"title": spec["name"], "direction": "directed", "condition": "", **spec}
        world.store.create("RelationTypeDoc", name, payload, Path("relations") / "types" / f"{spec['name']}.md")
        created.append(name)
    return created


def migrate(world: World) -> dict:
    steps = world.store.docs_of("ConversationStep")
    by_name = {d.name: d for d in world.store.docs()}
    tag_to_step = {
        t: d.name for d in steps for t in (d.semantic_tags or []) if t.startswith("conversation:steps.")
    }
    existing = {d.name for d in world.store.docs_of("RelationDoc")}
    report = {"created": [], "skipped_existing": 0, "unresolved": []}

    def edge(rel: str, src: str, dst_name: str) -> None:
        dst = by_name.get(dst_name)
        if dst is None:
            report["unresolved"].append((rel, src, dst_name))
            return
        doc_name = f"{rel}--{src}--{dst_name}"
        if doc_name in existing:
            report["skipped_existing"] += 1
            return
        payload = {
            "title": f"{src} {rel} {dst_name}",
            "source_id": f"ConversationStep:{src}",
            "target_id": f"{dst.model_name}:{dst_name}",
            "relation_type": rel, "condition": "", "notes": "",
        }
        world.store.create("RelationDoc", doc_name, payload, Path("relations") / f"{doc_name}.md")
        report["created"].append(doc_name)

    for step in steps:
        p = step.payload or {}
        for tag in _split(p.get("allowed_transitions")):
            target = tag_to_step.get(tag)
            if target is None:
                report["unresolved"].append(("transitions_to", step.name, tag))
                continue
            edge("transitions_to", step.name, target)
        for atom in _split(p.get("grounding_atoms")):
            edge("grounded_by", step.name, atom)
        for tool in _split(p.get("tool_ref")):
            edge("uses_tool", step.name, tool)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("kb_root", help="directorio que contiene .sldb/")
    ap.add_argument("--pythonpath", default=None, help="raiz del repo con los modelos (default: cwd)")
    args = ap.parse_args(argv)
    world = World(args.kb_root, pythonpath=args.pythonpath or str(Path.cwd()))
    for missing in ("RelationTypeDoc", "RelationDoc"):
        if missing not in world.model_names():
            print(f"el store no tiene {missing}: corre `kgdb init --store {args.kb_root}/.sldb --pythonpath .` primero", file=sys.stderr)
            return 2
    types = ensure_relation_types(world)
    report = migrate(world)
    world.refresh()
    print(f"relation types creados: {types or 'ninguno (ya existian)'}")
    print(f"aristas creadas: {len(report['created'])} · ya existian: {report['skipped_existing']}")
    for rel, src, dst in report["unresolved"]:
        print(f"  SIN RESOLVER {rel}: {src} -> {dst!r} (no existe en el store)")
    return 1 if report["unresolved"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
