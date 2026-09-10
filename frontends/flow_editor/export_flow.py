"""Exporta el diagrama de conversacion de una KB a flow.json para la UI.

Nodos  = ConversationStep (con sus campos)
Aristas = ``transitions_to`` del grafo tipado de kgdb (RelationDoc de la KB)

Uso:
    PYTHONPATH=. python frontends/flow_editor/export_flow.py [kb_root] [out.json]
    # default: kb_root=project.config.yaml (kb_root)  out=frontends/flow_editor/flow.json
"""
from __future__ import annotations

import json
import sys

from knowledge_base.operations import KnowledgeOperations


def _split(v: str) -> list[str]:
    if not v:
        return []
    return [p.strip() for p in v.replace("\n", ",").split(",") if p.strip()]


def export(kb_root: str) -> dict:
    ops = KnowledgeOperations(kb_root=kb_root)
    flow = ops.flow
    nodes = []
    for s in ops.docs_by_type("step"):
        step = flow.by_id(s["id"])
        nodes.append({
            "id": s["id"],
            "step_tag": step.tag if step else None,
            "title": s.get("title", s["id"]),
            "kind": s.get("kind", "interaccion_simple"),
            "instructions": s.get("instructions", ""),
            "required_slots": _split(s.get("required_slots", "")),
            "allowed_transitions": list(step.transitions) if step else [],
            "grounding_atoms": list(step.grounding) if step else [],
            "tool": step.tool if step else None,
            "completion_condition": s.get("completion_condition", "") or "",
            "domain_ref": s.get("domain_ref"),
        })
    edges = [{"source": src, "target": dst, "relation": "transitions_to"} for src, dst in flow.edges()]
    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    from kb_agent.project_config import load_project_config

    kb = sys.argv[1] if len(sys.argv) > 1 else str(load_project_config().flow_kb_root)
    data = json.dumps(export(kb), indent=2, ensure_ascii=False)
    out = sys.argv[2] if len(sys.argv) > 2 else "frontends/flow_editor/flow.json"
    with open(out, "w", encoding="utf-8") as f:
        f.write(data)
    print(f"wrote {out}")
