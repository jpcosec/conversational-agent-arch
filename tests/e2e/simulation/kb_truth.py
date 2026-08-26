"""Verdad de referencia para el juez: la KB compilada tal como la ve el agente.

Se construye con el MISMO compilador del runtime (sin LLM), asi el juez evalua
contra exactamente lo que el asistente tenia disponible.
"""
from __future__ import annotations

from pathlib import Path

from kb_agent.ontologizador.compiler import ContextCompiler
from kb_agent.ontologizador.sldb_reader import SLDBReader


def kb_truth_text(kb_root: Path) -> str:
    reader = SLDBReader(kb_root=kb_root)
    d = ContextCompiler(reader=reader).compile(question="", user_id=None, trigger="cron").to_dict()
    persona = d.get("persona", {})
    tools = ", ".join(t.get("name", "?") for t in d.get("tools", [])) or "(ninguna)"
    lines = [
        f"IDENTIDAD: {persona.get('whoami', '')}",
        f"ESTILO: {persona.get('estilo', '')}",
        f"LIMITES: {persona.get('limites', '')}",
        f"ESTRATEGIA: {d.get('strategy', '')}",
        f"MENSAJE DE FALLBACK (cuando no sabe): {d.get('fallback_text', '')}",
        "HECHOS DEL NEGOCIO (lo UNICO que puede afirmar como dato):",
        *[f"- [{f['id']}] {f['body']}" for f in d.get("domain_facts", [])],
        "REGLAS:",
        *[f"- [{r['id']}] {r['body']}" for r in d.get("rules", [])],
        f"TOOLS DISPONIBLES: {tools}",
    ]
    return "\n".join(lines)
