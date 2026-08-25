"""Orquestador REAL end-to-end: cablea TODOS los modulos.

Flujo por turno:
  usuario -> RouterStateMachine -> Ontologizador (compile_context real, con traits del user)
          -> Conversador (Gemini real: NL / fallback / function_call)
          -> [si function_call] Tool dispatcher REAL que persiste en SQL
          -> ChatHistory (scrubbed) + publish turn -> Perfilador async (Gemini real)
          -> traits persistidos en UserTraits -> disponibles en el siguiente turno

SIN mock, SIN dummy, SIN stub. LLM real via Vertex ADC, SQL real, SLDB real.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

from google import genai
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from kb_agent.agent import CANONICAL_FALLBACK_RESPONSE, draft_conversador_response
from kb_agent.models_sql.identity import Base, Users, UserTraits
from kb_agent.models_sql.reservas import Reservas
from kb_agent.models_sql.session import ChatHistory, SessionState
from kb_agent.ontologizador.compiler import ContextCompiler
from kb_agent.ontologizador.sldb_reader import SLDBReader
from kb_agent.perfilador.extractor import TraitCandidate, TraitExtractor
from kb_agent.perfilador.listener import InProcessEventBus, publish_turn_closed
from kb_agent.pii.scrubber import scrub

MODEL = "gemini-2.5-flash"


# ─────────────────────────── LLM real: Conversador NL ───────────────────────────
class GeminiConversador:
    def __init__(self, client: genai.Client) -> None:
        self._client = client

    def draft_nl(self, compiled: dict[str, Any]) -> str:
        facts = [f["body"] for f in compiled.get("domain_facts", [])]
        rules = [r["body"] for r in compiled.get("rules", [])]
        traits = compiled.get("user_traits", [])
        grounding = "\n".join(f"- {t}" for t in facts + rules)
        perfil = f"\nPERFIL DEL CLIENTE (traits): {', '.join(traits)}" if traits else ""
        prompt = (
            "Eres el asistente de la pizzeria Don Peppe. Responde en espanol, "
            "breve y amable, usando EXCLUSIVAMENTE los datos de abajo. "
            "Si hay traits del cliente, adapta la sugerencia a su perfil. "
            "No inventes nada fuera de estos datos.\n\n"
            f"DATOS:\n{grounding}{perfil}\n\n"
            f"PREGUNTA: {compiled['question']}\n\nRESPUESTA:"
        )
        resp = self._client.models.generate_content(model=MODEL, contents=prompt)
        return (resp.text or "").strip()


# ─────────────────────────── LLM real: Trait mapper ───────────────────────────
class GeminiTraitMapper:
    """StructuredTraitMapper real: usa Gemini para mapear texto -> trait_ids."""

    def __init__(self, client: genai.Client) -> None:
        self._client = client

    def extract_traits(self, *, turn_text: str, candidates: list[TraitCandidate], instructions: str) -> list[dict[str, Any]]:
        catalogo = "\n".join(f"- {c.id}: {c.body}" for c in candidates)
        prompt = (
            "Analiza el mensaje del cliente y determina si revela EXPLICITAMENTE "
            "alguna de las caracteristicas del catalogo. Solo caracteristicas dichas "
            "explicitamente, no inferencias.\n\n"
            f"CATALOGO DE TRAITS:\n{catalogo}\n\n"
            f"MENSAJE: {turn_text}\n\n"
            "Responde SOLO un array JSON con los traits detectados, formato: "
            '[{\"trait_id\": \"<id exacto del catalogo>\", \"confidence\": <0..1>}]. '
            "Si no hay ninguno, responde []."
        )
        resp = self._client.models.generate_content(model=MODEL, contents=prompt)
        text = (resp.text or "").strip()
        match = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if not match:
            return []
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return []


# ─────────────────────────── Tool dispatcher REAL ───────────────────────────
def execute_tool(session: Session, user_id: int | None, function_call: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta la tool de verdad y PERSISTE. Devuelve el System Turn (JSON)."""
    name = function_call.get("name")
    args = function_call.get("args", {})
    if name == "crear_reserva":
        reserva = Reservas(
            user_id=user_id,
            fecha=str(args.get("fecha", "")),
            hora=str(args.get("hora", "")),
            personas=int(args.get("personas", 0)),
            nombre=args.get("nombre"),
        )
        session.add(reserva)
        session.commit()
        return {"tool": name, "status": "ok", "reserva_id": reserva.id, "args": args}
    return {"tool": name, "status": "unknown_tool", "args": args}


# ─────────────────────────── Orquestador ───────────────────────────
class Orchestrator:
    def __init__(self, *, kb_root: Path, db_url: str = "sqlite:///:memory:") -> None:
        self.engine = create_engine(db_url, future=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, future=True)

        self.reader = SLDBReader(kb_root=kb_root, store_name=".sldb")
        self.client = genai.Client()
        self.conversador = GeminiConversador(self.client)
        self.trait_mapper = GeminiTraitMapper(self.client)
        self.event_bus = InProcessEventBus()

    def ensure_user(self, session: Session, external_id: str) -> Users:
        user = session.query(Users).filter_by(external_id=external_id).one_or_none()
        if user is None:
            user = Users(external_id=external_id, channel="e2e")
            session.add(user)
            session.commit()
        return user

    def handle_turn(self, *, external_id: str, message: str, scenario: str = "pizzeria") -> dict[str, Any]:
        session = self.SessionLocal()
        try:
            user = self.ensure_user(session, external_id)

            # 1) Ontologizador REAL con traits del usuario desde SQL
            compiler = ContextCompiler(reader=self.reader, identity_session=session)
            compiled = compiler.compile(question=message, user_id=user.id, scenario=scenario)

            # 2) Conversador: decision determinista (fallback/tool) + Gemini para NL
            decision = draft_conversador_response(compiled)
            system_turn = None
            if isinstance(decision, dict) and "function_call" in decision:
                kind = "tool_call"
                # 3) Tool dispatcher REAL: persiste en SQL
                system_turn = execute_tool(session, user.id, decision["function_call"])
                reply = decision
            elif decision == CANONICAL_FALLBACK_RESPONSE:
                kind, reply = "fallback", decision
            else:
                kind, reply = "nl", self.conversador.draft_nl(compiled)

            # 4) Persistir turno en ChatHistory (scrubbeado)
            session.add(ChatHistory(user_id=user.id, role="user", content=scrub(message), pii_scrubbed=True))
            reply_text = json.dumps(reply, ensure_ascii=False) if isinstance(reply, dict) else str(reply)
            session.add(ChatHistory(user_id=user.id, role="assistant", content=reply_text, pii_scrubbed=True))
            session.commit()

            # 5) Perfilador async REAL: extrae traits con Gemini y persiste
            traits_before = self._current_traits(session, user.id)
            asyncio.run(self._run_profiler(user.id, message))
            traits_after = self._current_traits(session, user.id)

            return {
                "user_id": user.id,
                "question": message,
                "kind": kind,
                "reply": reply,
                "system_turn": system_turn,
                "traits_before": traits_before,
                "traits_after": traits_after,
                "used_traits_in_context": compiled.get("user_traits", []),
            }
        finally:
            session.close()

    async def _run_profiler(self, user_id: int, turn_text: str) -> None:
        # scrub inline antes de que el perfilador vea nada (regla PII)
        publish_turn_closed(self.event_bus, user_id=user_id, turn_text=turn_text)
        event = await self.event_bus.get()
        # el extractor usa SU PROPIA session (worker independiente)
        session = self.SessionLocal()
        try:
            extractor = TraitExtractor(
                reader=self.reader,
                identity_session=session,
                llm_mapper=self.trait_mapper,
            )
            extractor.extract(user_id=event.user_id, turn_text=event.turn_text_scrubbed)
        finally:
            session.close()

    def _current_traits(self, session: Session, user_id: int) -> list[str]:
        rows = session.query(UserTraits.trait_id).filter_by(user_id=user_id).order_by(UserTraits.trait_id).all()
        return [r[0] for r in rows]

    def count_reservas(self) -> int:
        session = self.SessionLocal()
        try:
            return session.query(Reservas).count()
        finally:
            session.close()
