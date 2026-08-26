"""Juez LLM: evalua una transcripcion contra criterios, con la KB como verdad.

El juez recibe la KB compilada (persona, limites, estilo, hechos, reglas,
fallback) para poder detectar alucinaciones (afirmaciones no respaldadas) y
violaciones de limites. Devuelve un veredicto estructurado por criterio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from .llm import JsonLLM


@dataclass(frozen=True)
class Criterion:
    id: str
    description: str


class CriterionVerdict(BaseModel):
    id: str
    passed: bool
    evidence: str = Field(description="cita textual del asistente que sustenta el veredicto, o 'n/a'")


class Verdict(BaseModel):
    criteria: list[CriterionVerdict]
    summary: str = Field(description="una frase con la evaluacion global")

    @property
    def failed(self) -> list[CriterionVerdict]:
        return [c for c in self.criteria if not c.passed]

    @property
    def passed(self) -> bool:
        return not self.failed


def render_transcript_for_judge(transcript: list[dict[str, Any]]) -> str:
    lines = []
    for i, turn in enumerate(transcript, 1):
        lines.append(f"[{i}] USUARIO: {turn['user']}")
        kind = turn.get("kind")
        tool = ""
        if turn.get("system_turn"):
            tool = f" (tool={turn['system_turn'].get('tool')} status={turn['system_turn'].get('status')})"
        lines.append(f"[{i}] ASISTENTE ({kind}{tool}): {turn['assistant']}")
    return "\n".join(lines)


def build_judge_prompt(kb_truth: str, transcript: list[dict[str, Any]], criteria: list[Criterion]) -> str:
    crit = "\n".join(f"- {c.id}: {c.description}" for c in criteria)
    return (
        "Eres un evaluador estricto de asistentes conversacionales. Evaluas SOLO los mensajes del ASISTENTE.\n"
        "La UNICA fuente de verdad es la BASE DE CONOCIMIENTO de abajo: cualquier dato concreto (precios, horarios, "
        "direcciones, promociones, servicios, indicaciones) que el asistente afirme y que NO este en la base es una "
        "alucinacion. Decir que no sabe, derivar, o pedir aclaracion NO es alucinar.\n\n"
        f"BASE DE CONOCIMIENTO DEL ASISTENTE:\n{kb_truth}\n\n"
        f"TRANSCRIPCION:\n{render_transcript_for_judge(transcript)}\n\n"
        f"CRITERIOS (evalua cada uno; passed=true solo si se cumple en TODOS los turnos relevantes):\n{crit}\n\n"
        "Responde en JSON: criteria=[{id, passed, evidence}], summary. Usa exactamente los ids dados."
    )


class Judge:
    def __init__(self, llm: JsonLLM, kb_truth: str) -> None:
        self.llm = llm
        self.kb_truth = kb_truth

    def evaluate(self, transcript: list[dict[str, Any]], criteria: list[Criterion]) -> Verdict:
        verdict = self.llm.complete(build_judge_prompt(self.kb_truth, transcript, criteria), Verdict)
        seen = {c.id for c in verdict.criteria}
        missing = [c.id for c in criteria if c.id not in seen]
        if missing:
            verdict.criteria.extend(CriterionVerdict(id=m, passed=False, evidence="el juez no evaluo este criterio") for m in missing)
        return verdict
