"""Exporta los ConversationStep de un store SLDB a flow.json para la UI.

Nodos  = ConversationStep (con sus campos)
Aristas = allowed_transitions (tag conversation:steps.<x> -> step id)

Uso:
    PYTHONPATH=. python conversation_flow_editor/export_flow.py [kb_root] [out.json]
    # default: kb_root=project.config.yaml (kb_root)  out=conversation_flow_editor/flow.json
"""
from __future__ import annotations

import json
import sys

from kb_agent.ontologizador.sldb_reader import SLDBReader


def _split(v: str) -> list[str]:
    if not v:
        return []
    parts = [p.strip() for p in v.replace("\n", ",").split(",")]
    return [p for p in parts if p and p.lower() not in ("ninguno", "ninguna", "ninguna (paso terminal)")]


def export(kb_root: str) -> dict:
    r = SLDBReader(kb_root=kb_root, store_name=".sldb")
    steps = r.find("type.knowledge.step")

    # tag conversation:steps.<name> -> step id
    tag_to_id: dict[str, str] = {}
    for s in steps:
        for t in s.get("tags", []):
            if t.startswith("conversation:steps."):
                tag_to_id[t] = s["id"]

    nodes = []
    edges = []
    for s in steps:
        step_tag = next((t for t in s.get("tags", []) if t.startswith("conversation:steps.")), None)
        nodes.append({
            "id": s["id"],
            "step_tag": step_tag,
            "title": s.get("title", s["id"]),
            "kind": s.get("kind", "interaccion_simple"),
            "instructions": s.get("instructions", ""),
            "required_slots": _split(s.get("required_slots", "")),
            "allowed_transitions": _split(s.get("allowed_transitions", "")),
            "grounding_atoms": _split(s.get("grounding_atoms", "")),
            "completion_condition": s.get("completion_condition", "") or "",
            "domain_ref": s.get("domain_ref"),
        })
        for tag in _split(s.get("allowed_transitions", "")):
            target = tag_to_id.get(tag)
            if target:
                edges.append({"source": s["id"], "target": target, "relation": "flows_to"})

    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    from kb_agent.project_config import load_project_config

    kb = sys.argv[1] if len(sys.argv) > 1 else str(load_project_config().flow_kb_root)
    data = json.dumps(export(kb), indent=2, ensure_ascii=False)
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(data)
        print(f"wrote {sys.argv[2]}")
    else:
        default_out = "conversation_flow_editor/flow.json"
        with open(default_out, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"wrote {default_out}")
