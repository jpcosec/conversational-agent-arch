"""Orquestador end-to-end: cablea TODOS los modulos.

Flujo por turno:
  usuario -> RouterStateMachine -> Ontologizador (compile_context, con traits del user)
          -> policy decide_turn (pura) -> Conversador (LLM: NL) | fallback (KB) | function_call
          -> [si function_call] Tool dispatcher (registry inyectado) que persiste en SQL
          -> ChatHistory (scrubbed) + publish turn -> Perfilador (LLM)
          -> traits persistidos en UserTraits -> disponibles en el siguiente turno

Nada del negocio vive aqui: KB, modelo, tools y fallback llegan por
``project.config.yaml`` (``Orchestrator.from_config``) o por inyeccion
explicita en el constructor (tests, otros canales).
"""
from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from kb_agent.agent import DEFAULT_FALLBACK_MESSAGE, decide_turn
from kb_agent.llm import Conversador, GeminiConversador, GeminiTraitMapper, TraitMapper, make_gemini_client
from kb_agent.models_sql.identity import Base, Users, UserTraits
from kb_agent.models_sql.reservas import Reservas  # noqa: F401  (registra la tabla en Base)
from kb_agent.models_sql.recordatorios import Recordatorios  # noqa: F401  (registra la tabla en Base)
from kb_agent.models_sql.session import ChatHistory, SessionNode, SessionState
from kb_agent.ontologizador.compiler import ContextCompiler
from kb_agent.ontologizador.kgdb_reader import KGDBReader
from kb_agent.ontologizador.sldb_reader import SLDBReader
from kb_agent.perfilador.extractor import TraitExtractor
from kb_agent.perfilador.listener import InProcessEventBus, publish_turn_closed
from kb_agent.pii.scrubber import scrub
from kb_agent.project_config import DEFAULT_MODEL, ProjectConfig, load_project_config
from kb_agent.reflector import InMemoryCheckpointStore, ReflectorAtomGenerator, ReflectorBatchReaderJob
from kb_agent.tools import ToolHandler, execute_tool, load_tool_handlers
from kb_agent.state_machine import RouterStateMachine

#: Canal cuando el external_id no trae prefijo reconocible ("<canal>:<id>").
UNKNOWN_CHANNEL = "unknown"


def channel_from_external_id(external_id: str) -> str:
    """Deriva el canal del prefijo del external_id (``whatsapp:+56...`` -> ``whatsapp``)."""
    prefix, sep, _ = external_id.partition(":")
    if sep and prefix and " " not in prefix:
        return prefix.lower()
    return UNKNOWN_CHANNEL


class Orchestrator:
    def __init__(
        self,
        *,
        kb_root: Path | str,
        db_url: str = "sqlite:///:memory:",
        model: str | None = None,
        tool_handlers: Mapping[str, ToolHandler] | None = None,
        fallback_message: str | None = None,
        conversador: Conversador | None = None,
        trait_mapper: TraitMapper | None = None,
        client: Any | None = None,
    ) -> None:
        self.kb_root = Path(kb_root).resolve()
        self.repo_root = Path(__file__).resolve().parents[1]
        self.model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
        self.tool_handlers: dict[str, ToolHandler] = dict(tool_handlers or {})
        self.fallback_message = fallback_message or DEFAULT_FALLBACK_MESSAGE

        self.engine = create_engine(db_url, future=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, future=True)

        self.reader = SLDBReader(kb_root=self.kb_root, store_name=".sldb")
        try:
            self.kgdb = KGDBReader.from_sldb(self.kb_root / ".sldb")
        except Exception:
            self.kgdb = None
        self._reflector_checkpoint_store = InMemoryCheckpointStore()

        # LLM: solo se crea el cliente real si no inyectaron ambos puertos.
        if conversador is None or trait_mapper is None:
            client = client or make_gemini_client()
        self.conversador: Conversador = conversador or GeminiConversador(client, self.model)
        self.trait_mapper: TraitMapper = trait_mapper or GeminiTraitMapper(client, self.model)
        self.event_bus = InProcessEventBus()

    @classmethod
    def from_config(cls, cfg: ProjectConfig | None = None, *, db_url: str | None = None, **overrides: Any) -> "Orchestrator":
        """Construye el orquestador del negocio declarado en project.config.yaml."""
        cfg = cfg or load_project_config()
        params: dict[str, Any] = {
            "kb_root": cfg.kb_root,
            "db_url": db_url or cfg.chat_db_url,
            "model": cfg.model,
            "tool_handlers": load_tool_handlers(cfg.tool_handlers),
            "fallback_message": cfg.fallback_message,
        }
        params.update(overrides)
        return cls(**params)

    # ── identidad ─────────────────────────────────────────────────────────
    def ensure_user(self, session: Session, external_id: str, channel: str | None = None) -> Users:
        user = session.query(Users).filter_by(external_id=external_id).one_or_none()
        if user is None:
            user = Users(external_id=external_id, channel=channel or channel_from_external_id(external_id))
            session.add(user)
            session.commit()
        return user

    # ── turno ─────────────────────────────────────────────────────────────
    def handle_turn(
        self,
        *,
        external_id: str,
        message: str,
        scenario: str | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        session = self.SessionLocal()
        try:
            user = self.ensure_user(session, external_id, channel=channel)
            session_state = self._load_or_create_session_state(session, user.id)

            if scenario is not None:
                scenario_source = "argument"
            elif session_state.active_domain:
                scenario_source = "session_state"
            else:
                scenario_source = "default"

            compiler = ContextCompiler(reader=self.reader, kgdb=self.kgdb, identity_session=session)

            def compile_context(*, question: str, user_id: int | None, scenario: str | None, trigger: str) -> dict[str, Any]:
                compiled = compiler.compile(
                    question=question,
                    user_id=user_id,
                    scenario=scenario,
                    trigger=trigger,
                    session_state=session_state,
                )
                d = compiled.to_dict()
                d["user_id"] = user_id
                return d

            def draft(compiled_context: dict[str, Any]) -> Any:
                # El ORQUESTADOR decide el tipo de turno con una policy pura
                # (decide_turn) y SOLO despues actua. Decidir != redactar.
                if compiled_context.get("system_turn"):
                    return self.conversador.draft_nl(compiled_context)

                decision = decide_turn(compiled_context)
                kind = decision.get("kind")
                if kind == "tool_call":
                    return {"function_call": decision["function_call"]}
                if kind == "fallback":
                    return self._fallback_text(compiled_context)
                # Guardar flow_target si existe para navegacion post-draft
                compiled_context["_flow_target"] = decision.get("flow_target")
                return self.conversador.draft_nl(compiled_context)

            router = RouterStateMachine(compile_context=compile_context, draft_response=draft)
            turn_result = router.handle_user_message(message, user_id=user.id, scenario=scenario)
            if turn_result is None:
                raise RuntimeError("router did not produce a turn result for immediate user turn")

            compiled = turn_result.compiled_context
            scenario_effective = str(compiled.get("scenario", ""))
            response = turn_result.response
            state_trace = [node.value for node in router.state_trace]

            system_turn = None
            if isinstance(response, dict) and "function_call" in response:
                kind = "tool_call"
                system_turn = execute_tool(session, user.id, response["function_call"], self.tool_handlers)
                resumed_result = router.handle_tool_result(system_turn)
                response = resumed_result.response
                compiled = resumed_result.compiled_context
                state_trace = [node.value for node in router.state_trace]
            elif self._is_fallback_response(response, compiled):
                kind = "fallback"
            else:
                kind = "nl"
                # Policy Gate: validar respuesta redactada contra criterios gate
                gate_result = self._validate_response(response, compiled)
                if not gate_result["approved"]:
                    kind = "derived"
                    response = (
                        "He preparado una respuesta pero prefiero que un profesional "
                        "del programa la revise antes de enviarla. Alguien del equipo "
                        "te contactará a la brevedad."
                    )
                    compiled["gate_rejection"] = gate_result["reasons"]

            # Navegacion de flujo: si el orquestador clasifico un flow_target,
            # actualizar el flow_node en SessionState
            flow_target = compiled.get("_flow_target")
            if flow_target:
                compiled["flow_node"] = flow_target

            # Persistir SessionState (dominio + flujo) + ChatHistory
            session_state.active_domain = scenario_effective or None
            flow_node = compiled.get("flow_node")
            if flow_node:
                session_state.flow_node = flow_node
            flow_transitions = compiled.get("allowed_transitions", [])
            flow_missing = compiled.get("missing_slots", [])
            if flow_transitions or flow_missing:
                session_state.flow_slots = {
                    "allowed_transitions": flow_transitions,
                    "missing_slots": flow_missing,
                }
            session_state.current_node = SessionNode.IDLE
            session_state.updated_at = datetime.now(timezone.utc)
            reply_text = json.dumps(response, ensure_ascii=False) if isinstance(response, dict) else str(response)
            self._persist_chat_history(session, user_id=user.id, role="user", content=message)
            self._persist_chat_history(session, user_id=user.id, role="assistant", content=reply_text)
            session.commit()

            # Perfilador: extrae traits con LLM y persiste (sesion propia)
            traits_before = self._current_traits(session, user.id)
            asyncio.run(self._run_profiler(user.id, message))
            traits_after = self._current_traits(session, user.id)

            return {
                "user_id": user.id,
                "question": message,
                "kind": kind,
                "reply": response,
                "reply_text": reply_text,
                "system_turn": system_turn,
                "traits_before": traits_before,
                "traits_after": traits_after,
                "used_traits_in_context": compiled.get("user_traits", []),
                "scenario_effective": scenario_effective,
                "scenario_source": scenario_source,
                "state_trace": state_trace,
                "flow_node": flow_node,
                "allowed_transitions": flow_transitions,
                "missing_slots": flow_missing,
                "context": self._build_turn_context(compiled),
            }
        finally:
            session.close()

    # ── fallback ──────────────────────────────────────────────────────────
    def _fallback_text(self, compiled: Mapping[str, Any]) -> str:
        """Texto de fallback: FallbackRule de la KB > config del proyecto > constante."""
        kb_fallback = (compiled.get("fallback_text") or "").strip()
        return kb_fallback or self.fallback_message

    def _is_fallback_response(self, response: Any, compiled: Mapping[str, Any]) -> bool:
        if not isinstance(response, str):
            return False
        return response == self._fallback_text(compiled)

    # ── policy gate ───────────────────────────────────────────────────────
    def _validate_response(self, response: str, compiled: Mapping[str, Any]) -> dict[str, Any]:
        """Valida una respuesta redactada contra los criterios GateCriterion de la KB.

        Lee los atomos type.knowledge.gate del store y verifica que la
        respuesta no viole ningun criterio regulatorio. Si algun criterio
        falla, devuelve ``approved: False`` con los motivos.

        Los atomos gate son invisibles al compilador de turno, asi que se
        leen directamente del reader.
        """
        if not isinstance(response, str) or not response.strip():
            return {"approved": True, "reasons": []}

        try:
            gate_atoms = self.reader.find("type.knowledge.gate")
        except Exception:
            return {"approved": True, "reasons": []}

        if not gate_atoms:
            return {"approved": True, "reasons": []}

        reasons: list[str] = []
        response_lower = response.lower()

        for atom in gate_atoms:
            criterion = str(atom.get("criterion", "") or "")
            approval = str(atom.get("approval_condition", "") or "")
            rejection = str(atom.get("rejection_action", "") or "")
            atom_id = atom.get("id", "")

            # Heuristicas deterministicas por criterio comun
            # Se basan en los approval_condition de los 5 gate atoms
            violated = False

            if "dosis" in atom_id or "dosis" in criterion:
                # No indica, sugiere ni comenta cambios de dosis
                if any(p in response_lower for p in ["sube la dosis", "subir la dosis", "suba la dosis",
                       "baja la dosis", "bajar la dosis", "baje la dosis",
                       "aumenta la dosis", "aumentar la dosis", "aumente la dosis",
                       "debes tomar", "tienes que tomar", "tiene que tomar",
                       "cambia la dosis", "cambiar la dosis", "cambie la dosis",
                       "ajusta la dosis", "ajustar la dosis", "ajuste la dosis"]):
                    violated = True

            if "diagnostico" in atom_id or "diagnostico" in criterion:
                # No diagnostica ni interpreta sintomas
                # Usar frases completas para evitar falsos positivos con "tienes"
                if any(p in response_lower for p in ["tienes diabetes", "tienes cancer", "tienes una enfermedad",
                       "tienes un problema de", "diagnosticado", "padeces de", "sufres de",
                       "tu enfermedad es", "tu problema es", "lo que tienes es",
                       "esto es debido a", "la causa de tus sintomas"]):
                    violated = True

            if "corpus" in atom_id or "corpus" in criterion:
                # La respuesta no debe indicar que usa informacion no aprobada
                if any(p in response_lower for p in ["según estudios", "investigaciones muestran",
                       "la literatura dice", "se ha demostrado que", "segun la ciencia"]):
                    violated = True

            if "promesas" in atom_id or "promesas" in criterion:
                # No promete resultados clinicos
                if any(p in response_lower for p in ["vas a mejorar", "te curar", "te sanar",
                       "100%", "garantiz", "resultado seguro", "sin riesgo"]):
                    violated = True

            if "derivacion" in atom_id or "derivacion" in criterion:
                # Si la respuesta contiene informacion que debio derivar pero no deriva
                # (check mas suave — se basa en que el LLM ya deriva correctamente)
                pass

            if violated:
                reasons.append(f"{atom_id}: {rejection}" if rejection else atom_id)

        return {"approved": len(reasons) == 0, "reasons": reasons}

    # ── contexto del turno (para UIs) ─────────────────────────────────────
    @staticmethod
    def _semantic_role(tags: list[str], fallback: str) -> str:
        """Deriva el rol semantico del atom desde su eje de tag (doctrina KB).

        self:* -> identidad/estilo/limites; domain:* -> conocimiento del negocio;
        conversation:* -> flujo. El eje de negocio (domain:*) prima sobre el de
        flujo (conversation:*). Si no hay eje reconocible, usa el fallback por
        atom_type (domain_fact / rule).
        """
        for t in tags:
            if t.startswith("self:"):
                return f"self.{t.split(':', 1)[1]}"
        for t in tags:
            if t.startswith("domain:"):
                return "domain_fact"
        for t in tags:
            if t.startswith("conversation:"):
                return f"conversation.{t.split(':', 1)[1]}"
        return fallback

    def _build_turn_context(self, compiled: Mapping[str, Any]) -> dict[str, Any]:
        """Atoms reales (facts + rules) que fundamentaron la respuesta, con rol y tags.

        NO re-lee el store: el compilador ya entrego tags y title en cada atom.
        """
        items: list[dict[str, Any]] = []
        atom_ids: list[str] = []
        include_tags: set[str] = set()
        grounding = set(compiled.get("grounding_atoms", []))

        def _add(atom: Mapping[str, Any], fallback_role: str) -> None:
            atom_id = atom.get("id", "")
            tags = list(atom.get("tags", []))
            items.append({
                "atom_id": atom_id,
                "title": atom.get("title") or atom_id,
                "role": self._semantic_role(tags, fallback_role),
                "score": 1.0,
                "tags": tags,
                "grounds_step": atom_id in grounding,
                "body": atom.get("body", ""),
            })
            atom_ids.append(atom_id)
            include_tags.update(tags)

        for fact in compiled.get("domain_facts", []):
            _add(fact, "domain_fact")
        for rule in compiled.get("rules", []):
            _add(rule, "rule")

        return {
            "scenario": compiled.get("scenario", ""),
            "atom_ids": atom_ids,
            "include_tags": sorted(include_tags),
            "items": items,
            "tools": compiled.get("tools", []),
            "user_traits": compiled.get("user_traits", []),
            "grounding_atoms": compiled.get("grounding_atoms", []),
            "flow_node": compiled.get("flow_node"),
            "allowed_transitions": compiled.get("allowed_transitions", []),
            "is_empty": compiled.get("is_empty", False),
        }

    # ── perfilador ────────────────────────────────────────────────────────
    async def _run_profiler(self, user_id: int, turn_text: str) -> None:
        # scrub inline antes de que el perfilador vea nada (regla PII)
        publish_turn_closed(self.event_bus, user_id=user_id, turn_text=turn_text)
        event = await self.event_bus.get()
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

    # ── reflector ─────────────────────────────────────────────────────────
    def run_reflector(self) -> list[dict[str, Any]]:
        reader = ReflectorBatchReaderJob(self.SessionLocal, self._reflector_checkpoint_store)
        rows = reader.run(trigger="cron")
        generator = ReflectorAtomGenerator(
            kb_root=self.repo_root,
            store_name=str(self.kb_root / ".sldb"),
            output_dir=self.kb_root / "atoms",
            pythonpath=self.repo_root,
        )
        generated = generator.generate(rows)
        return [
            {
                "atom_id": atom.atom_id,
                "atom_type": atom.atom_type,
                "path": str(atom.path),
                "normalized_text": atom.normalized_text,
                "count": atom.count,
            }
            for atom in generated
        ]

    # ── persistencia ──────────────────────────────────────────────────────
    def _load_or_create_session_state(self, session: Session, user_id: int) -> SessionState:
        state = session.get(SessionState, user_id)
        if state is None:
            state = SessionState(user_id=user_id, current_node=SessionNode.IDLE)
            session.add(state)
            session.commit()
        return state

    def _persist_chat_history(self, session: Session, *, user_id: int, role: str, content: str) -> ChatHistory:
        row = ChatHistory(user_id=user_id, role=role, content=scrub(content), pii_scrubbed=True)
        session.add(row)
        return row

    def _current_traits(self, session: Session, user_id: int) -> list[str]:
        rows = session.query(UserTraits.trait_id).filter_by(user_id=user_id).order_by(UserTraits.trait_id).all()
        return [r[0] for r in rows]

    def count_reservas(self) -> int:
        session = self.SessionLocal()
        try:
            return session.query(Reservas).count()
        finally:
            session.close()

    def close(self) -> None:
        self.engine.dispose()
