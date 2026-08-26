"""Usuario simulado: un agente conversacional (LLM) que interpreta a una persona
con un objetivo y datos privados, y conversa con el agente bajo prueba.

El usuario simulado NO conoce la KB: solo sabe lo que su ``Persona`` declara.
Decide cuando su objetivo se cumplio (``done=True``) o cuando se rinde.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from .llm import JsonLLM


@dataclass(frozen=True)
class Persona:
    name: str
    description: str          # quien es y como habla
    goal: str                 # que quiere lograr en la conversacion
    facts: dict[str, str] = field(default_factory=dict)   # datos que conoce (los revela cuando corresponde)
    behavior: str = ""        # instrucciones de comportamiento (ej. "una sola informacion por mensaje")
    opening_message: str | None = None                    # primer mensaje fijo (determinismo)
    done_when: str = ""       # criterio para dar por cumplido el objetivo


class UserMove(BaseModel):
    done: bool = Field(description="true si el objetivo se cumplio o decides terminar la conversacion")
    reason: str = Field(description="por que sigues o terminas, en una frase")
    message: str = Field(description="tu siguiente mensaje al asistente (vacio si done=true)")


def _render_transcript(transcript: list[dict[str, Any]]) -> str:
    if not transcript:
        return "(la conversacion aun no empieza; tu escribes primero)"
    lines = []
    for turn in transcript:
        lines.append(f"TU: {turn['user']}")
        lines.append(f"ASISTENTE: {turn['assistant']}")
    return "\n".join(lines)


def build_user_prompt(persona: Persona, transcript: list[dict[str, Any]]) -> str:
    facts = "\n".join(f"- {k}: {v}" for k, v in persona.facts.items()) or "- (ninguno)"
    return (
        f"Estas interpretando a una persona real que conversa por WhatsApp con un asistente virtual.\n\n"
        f"QUIEN ERES: {persona.name}. {persona.description}\n"
        f"TU OBJETIVO: {persona.goal}\n"
        f"DATOS QUE CONOCES (usalos solo cuando corresponda; no inventes otros):\n{facts}\n"
        f"COMPORTAMIENTO: {persona.behavior or 'Natural, breve, como un mensaje de chat.'}\n"
        f"CUANDO TERMINAR: {persona.done_when or 'Cuando tu objetivo se cumplio, o cuando el asistente claramente no puede ayudarte.'}\n\n"
        "Reglas:\n"
        "- Escribe SOLO tu proximo mensaje, en espanol, en primera persona, como usuario (nunca como asistente).\n"
        "- Mensajes cortos (1-2 frases). No repitas datos que ya diste salvo que te los pidan de nuevo.\n"
        "- No inventes datos que no esten en tu lista. Si te preguntan algo que no sabes, dilo.\n"
        "- Si el objetivo ya se cumplio, responde done=true con message vacio.\n\n"
        f"CONVERSACION HASTA AHORA:\n{_render_transcript(transcript)}\n\n"
        "Responde en JSON con: done, reason, message."
    )


class SimulatedUser:
    def __init__(self, llm: JsonLLM, persona: Persona) -> None:
        self.llm = llm
        self.persona = persona

    def next_move(self, transcript: list[dict[str, Any]]) -> UserMove:
        if not transcript and self.persona.opening_message:
            return UserMove(done=False, reason="mensaje inicial fijo", message=self.persona.opening_message)
        move = self.llm.complete(build_user_prompt(self.persona, transcript), UserMove)
        if not move.done and not move.message.strip():
            return UserMove(done=True, reason="el usuario simulado no produjo mensaje", message="")
        return move
