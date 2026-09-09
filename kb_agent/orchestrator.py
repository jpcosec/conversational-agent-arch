"""Orquestador end-to-end: cablea TODOS los modulos.

Flujo por turno:
  usuario -> RouterStateMachine -> Knowledge (compile_context, con traits del user)
          -> policy decide_turn (pura) -> Conversador (LLM: NL) | fallback (KB) | function_call
          -> [si function_call] Tool dispatcher (registry inyectado) que persiste en SQL
          -> ChatHistory (scrubbed) + publish turn -> Perfilador (LLM)
          -> traits persistidos en UserTraits -> disponibles en el siguiente turno

Nada del negocio vive aqui: KB, modelo, tools y fallback llegan por
``project.config.yaml`` (``Orchestrator.from_config``) o por inyeccion
explicita en el constructor (tests, otros canales).
"""
from __future__ import annotations

import re

import json
import threading
from time import perf_counter
import logging
import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from kb_agent.agent import DEFAULT_FALLBACK_MESSAGE
from kb_agent.agents.base import AgentRole
from kb_agent.agents.gate import GateAgent
from kb_agent.agents.orchestrator_agent import OrchestratorAgent
from kb_agent.agents.router import RouterAgent
from kb_agent.llm import Conversador, GeminiConversador, GeminiTraitMapper, TraitMapper, make_gemini_client
from kb_agent.models_sql.identity import Base, Users, UserTraits
from kb_agent.models_sql.reservas import Reservas  # noqa: F401  (registra la tabla en Base)
from kb_agent.models_sql.recordatorios import Recordatorios  # noqa: F401  (registra la tabla en Base)
from kb_agent.models_sql.session import ChatHistory, SessionNode, SessionState
from kb_agent.models_sql.turns import Turns, TurnKind
from kb_agent.models_sql.conversation import Conversation, ConversationStatus
from kb_agent.knowledge.compiler import ContextCompiler
from kb_agent.perfilador.extractor import TraitExtractor
from kb_agent.perfilador.listener import InProcessEventBus, TurnClosedEvent
from kb_agent.lead_slots import extract_lead_slots, merge_lead_slots
from kb_agent.pii.scrubber import scrub
from kb_agent.pii.scrubber import scrub
from kb_agent.project_config import DEFAULT_MODEL, ProjectConfig, TuningConfig, load_project_config
from kb_agent.reflector import InMemoryCheckpointStore, ReflectorAtomGenerator, ReflectorBatchReaderJob
from kb_agent.tools import ToolHandler, execute_tool, load_tool_handlers
from kb_agent.state_machine import RouterStateMachine
from knowledge_base.operations import KnowledgeOperations

#: Mensaje neutro cuando el policy gate rechaza el borrador; cada negocio
#: lo redacta en su yaml (``gate_handoff_message``).
DEFAULT_GATE_HANDOFF_MESSAGE = (
    "Prefiero confirmar ese punto con el equipo antes de responderte. "
    "Alguien del equipo te contactará a la brevedad."
)

logger = logging.getLogger(__name__)

#: Canal cuando el external_id no trae prefijo reconocible ("<canal>:<id>").
UNKNOWN_CHANNEL = "unknown"


#: Telefono E.164: opcional ``+`` y 7 a 15 digitos, tras quitar separadores.
_PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def canonical_phone(raw: str) -> str | None:
    """Telefono canonico (``+`` + digitos) de un id de canal telefonico.

    ``+56 9 1234-5678`` -> ``+56912345678``. Devuelve None si el id NO parece
    un telefono (``devsession-1``, ``abc``): antes se extraian los digitos que
    hubiera y ``ui:devsession-1`` daba ``+1``, con lo que dos sesiones de UI
    distintas terminadas en 1 se unificaban como la misma persona.
    """
    compact = re.sub(r"[\s\-().]", "", raw or "")
    if not _PHONE_RE.match(compact):
        return None
    return "+" + compact.lstrip("+")


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
        gate_handoff_message: str | None = None,
        tuning: TuningConfig | None = None,
        identity_key: str = "external_id",
        conversador: Conversador | None = None,
        trait_mapper: TraitMapper | None = None,
        gate: GateAgent | None = None,
        orchestrator_agent: OrchestratorAgent | None = None,
        router_agent: RouterAgent | None = None,
        client: Any | None = None,
    ) -> None:
        self.kb_root = Path(kb_root).resolve()
        self.repo_root = Path(__file__).resolve().parents[1]
        self.model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
        self.tool_handlers: dict[str, ToolHandler] = dict(tool_handlers or {})
        self.fallback_message = fallback_message or DEFAULT_FALLBACK_MESSAGE
        #: Texto que ve el usuario cuando el gate rechaza el borrador (kind
        #: "derived"). Es voz del negocio, no del runtime: viene del yaml
        #: (``gate_handoff_message``); el default es neutro.
        self.gate_handoff_message = gate_handoff_message or DEFAULT_GATE_HANDOFF_MESSAGE
        #: Parametros de tuning del runtime (bundle/historial/router). Antes
        #: eran constantes en el codigo; ahora llegan del yaml via ProjectConfig.
        self.tuning: TuningConfig = tuning or TuningConfig()
        #: Clave canonica de identidad de persona: "external_id" (default,
        #: cada canal:id es un usuario) o "phone" (unifica entre canales por
        #: telefono). Ver ``ensure_user`` y ``_canonical_phone``.
        self.identity_key = identity_key

        engine_kwargs: dict[str, Any] = {"future": True}
        if db_url.startswith("sqlite") and not db_url.endswith(":memory:"):
            # Espera hasta 30 s por un candado ajeno en vez de fallar a los 5 s
            # (default de sqlite3): dos turnos concurrentes que escriben en
            # ventanas cortas se serializan en vez de perder un mensaje.
            engine_kwargs["connect_args"] = {"timeout": 30}
        if db_url.endswith(":memory:"):
            # sqlite en memoria (tests): cada conexion nueva es OTRA base vacia.
            # El perfilador corre en un hilo con sesion propia, asi que todos
            # los hilos tienen que compartir la unica conexion.
            engine_kwargs.update(poolclass=StaticPool, connect_args={"check_same_thread": False})
        self.engine = create_engine(db_url, **engine_kwargs)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, future=True)

        # UNICA instancia por proceso y UNICO dueno del acceso al store: el
        # runtime lee la KB solo por aca (``docs_by_type`` / ``doc``). Antes
        # convivia con un ``SLDBReader`` propio de kb_agent que parseaba el
        # MISMO store una segunda vez, con su propio cache que nadie
        # sincronizaba con este. Ademas cachea el embedder de jina por
        # INSTANCIA (~1 min en frio), asi que se reutiliza en todos los turnos.
        self.knowledge_ops = KnowledgeOperations(
            kb_root=self.kb_root, db_url=db_url, pythonpath=str(self.repo_root),
        )
        self._reflector_checkpoint_store = InMemoryCheckpointStore()

        # LLM: solo se crea el cliente real si no inyectaron los 5 puertos
        # (conversador, trait_mapper, gate, orchestrator_agent, router_agent).
        # El gate LLM-judge (fase 2.3), el orquestador LLM-judge (fase 2.4) y
        # el ruteador de contexto (fase 2.2) se construyen UNA vez aca, no por
        # turno: los GateCriterion y el grafo de ConversationStep de la KB son
        # contexto fijo (ver GateAgent.static_instruction /
        # OrchestratorAgent.static_instruction), y el RouterAgent reusa la
        # UNICA instancia de KnowledgeOperations del proceso (embedder
        # cacheado, ver su constructor arriba).
        if (
            conversador is None
            or trait_mapper is None
            or gate is None
            or orchestrator_agent is None
            or router_agent is None
        ):
            client = client or make_gemini_client()
        self.conversador: Conversador = conversador or GeminiConversador(client, self.model)
        self.trait_mapper: TraitMapper = trait_mapper or GeminiTraitMapper(client, self.model)
        self.gate: GateAgent = gate or GateAgent(
            client=client, model=self.model, gate_atoms=self._load_gate_atoms(),
            framing=self._load_agent_framing(AgentRole.GATE),
        )
        # Orquestador (fase 2.4): decide kind/tool_call/step_target con LLM +
        # salida tipada, en vez de la policy por keywords (`decide_turn`, que
        # sigue viva como fallback deterministico -- ver
        # kb_agent/agents/orchestrator_agent.py). El grafo de steps declarado
        # en la KB es su static_instruction (fijo, no cambia por turno).
        self.orchestrator_agent: OrchestratorAgent = orchestrator_agent or OrchestratorAgent(
            client=client, model=self.model, step_atoms=self._load_step_atoms(),
            framing=self._load_agent_framing(AgentRole.ORCHESTRATOR),
        )
        # Ruteador de contexto (fase 2.2): decide el bundle justificado del
        # turno con LLM + tools de KB, en vez de (solo) la union
        # deterministica (`ContextCompiler._build_bundle`, que sigue viva
        # como fallback fail-open -- ver kb_agent/agents/router.py). Se
        # inyecta al `ContextCompiler` de cada turno en `handle_turn`, no se
        # reconstruye por turno.
        self.router_agent: RouterAgent = router_agent or RouterAgent(
            client=client, model=self.model, knowledge_ops=self.knowledge_ops,
            framing=self._load_agent_framing(AgentRole.ROUTER),
            default_max_results=self.tuning.router_max_results,
        )
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
            "gate_handoff_message": cfg.gate_handoff_message,
            "tuning": cfg.tuning,
            "identity_key": cfg.identity_key,
        }
        params.update(overrides)
        return cls(**params)

    # ── identidad ─────────────────────────────────────────────────────────
    @staticmethod
    def _canonical_phone(external_id: str) -> str | None:
        """Telefono canonico (solo digitos con prefijo +) de un external_id de
        canal telefonico. ``whatsapp:+56 9 1234 5678`` -> ``+56912345678``.

        Canales sin telefono (``ui:...``, ``web-anon-...``) devuelven None: no
        se unifican por telefono. Devuelve None si no queda ningun digito.
        """
        _, sep, raw = external_id.partition(":")
        if not sep:
            return None
        return canonical_phone(raw)

    def ensure_user(self, session: Session, external_id: str, channel: str | None = None) -> Users:
        user = session.query(Users).filter_by(external_id=external_id).one_or_none()
        if user is not None:
            return user

        # Identidad unificada por telefono (identity_key='phone', decision del
        # owner para Vitali): el mismo telefono en otro canal es la MISMA
        # persona. Se reusa el Users existente y el external_id nuevo queda
        # como alias (no se crea una fila duplicada). Sin telefono, o con
        # identity_key='external_id', cae al comportamiento por canal.
        phone = self._canonical_phone(external_id) if self.identity_key == "phone" else None
        if phone is not None:
            existing = (
                session.query(Users).filter_by(phone=phone).order_by(Users.id).first()
            )
            if existing is not None:
                return existing

        # SELECT-then-INSERT tiene una carrera: dos requests concurrentes del
        # mismo usuario nuevo (dos pestanas, doble tap, reintento de webhook)
        # pasan ambos el filtro y el segundo INSERT viola el UNIQUE de
        # ``external_id``. Antes eso reventaba el turno con un 500 y el mensaje
        # se perdia. Ahora: si el INSERT choca, rollback y re-SELECT del
        # ganador de la carrera.
        user = Users(
            external_id=external_id,
            channel=channel or channel_from_external_id(external_id),
            phone=phone,
        )
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            user = session.query(Users).filter_by(external_id=external_id).one()
        return user

    # ── turno ─────────────────────────────────────────────────────────────
    def handle_turn(
        self,
        *,
        external_id: str,
        message: str,
        scenario: str | None = None,
        channel: str | None = None,
        contact: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        session = self.SessionLocal()
        try:
            # Identificador unico del turno, generado UNA vez: es el mismo que
            # se persiste en ``turns`` y el que se devuelve al frontend. Antes
            # la UI usaba un contador ``tN`` (colisionaba entre requests
            # concurrentes de la misma sesion y no coincidia con el uuid
            # persistido). Un turno, un identificador.
            turn_id = uuid4().hex[:12]
            turn_started = perf_counter()
            user = self.ensure_user(session, external_id, channel=channel)
            session_state = self._load_or_create_session_state(session, user.id)
            # Conversacion activa (o nueva si la anterior expiro por
            # inactividad). El historial que va al prompt se acota a ESTA
            # conversacion, no a todo el chat_history del usuario.
            conversation = self._resolve_conversation(
                session, user_id=user.id, channel=channel or channel_from_external_id(external_id)
            )
            step_before = session_state.flow_node
            # Perfilador EN PARALELO con el turno (hilo propio, sesion SQL
            # propia): antes corria en serie despues de la respuesta y sumaba
            # una llamada LLM completa a la latencia de cada turno. Los
            # traits que extrae NO entran al contexto de este turno (igual
            # que antes: se leian antes de correrlo); ``traits_before`` se
            # captura aca, ``traits_after`` tras el join.
            traits_before = self._current_traits(session, user.id)
            #: El hilo arranca DESPUES de compilar el contexto del turno (ver
            #: ``compile_context``): el perfil aprendido en este turno entra
            #: al SIGUIENTE, nunca al que lo aprendio (contrato medido en
            #: tests: ``used_traits_in_context`` del primer turno es []).
            profiler: dict[str, tuple] = {}

            if scenario is not None:
                scenario_source = "argument"
            elif session_state.active_domain:
                scenario_source = "session_state"
            else:
                scenario_source = "default"

            # Datos del lead (email, telefono, preferencia de visita, modalidad)
            # capturados del mensaje CRUDO: chat_history se persiste scrubbeado
            # y no se pueden recuperar despues (ver kb_agent/lead_slots.py).
            # Se calculan ANTES de compilar para que (a) el OrchestratorAgent
            # sepa que datos ya tiene al decidir los args de una tool y (b) los
            # handlers los lean de session_state cuando el modelo no los paso.
            previous_slots = session_state.flow_slots if isinstance(session_state.flow_slots, dict) else {}
            # ``contact`` son datos que el CANAL ya conoce de la persona (el
            # formulario de entrada del chat web, el numero de WhatsApp): se
            # tratan igual que los que dijo en el mensaje, pero no pisan lo
            # que ya se habia capturado en la conversacion.
            declared = {k: v for k, v in (contact or {}).items() if v}
            collected_slots = merge_lead_slots(
                merge_lead_slots(declared, previous_slots.get("collected") or {}),
                extract_lead_slots(message),
            )
            session_state.flow_slots = {**previous_slots, "collected": collected_slots}
            # COMMIT, no flush: lo que sigue es la fase LLM (30-40 s con modelo
            # real). Un flush deja abierta una transaccion de escritura y SQLite
            # mantiene el candado RESERVED hasta el commit, asi que el turno de
            # OTRO usuario que llegue mientras tanto (webhook async: un hilo por
            # mensaje) muere con "database is locked" a los 5 s. Medido en local
            # con dos personas escribiendo a la vez.
            session.commit()

            compiler = ContextCompiler(
                knowledge=self.knowledge_ops,
                identity_session=session,
                knowledge_ops=self.knowledge_ops,
                router_agent=self.router_agent,
                max_bundle_size=self.tuning.max_bundle_size,
                history_limit=self.tuning.history_limit,
            )

            def compile_context(*, question: str, user_id: int | None, scenario: str | None, trigger: str) -> dict[str, Any]:
                compiled = compiler.compile(
                    question=question,
                    user_id=user_id,
                    scenario=scenario,
                    trigger=trigger,
                    session_state=session_state,
                    conversation_id=conversation.id,
                )
                d = compiled.to_dict()
                d["user_id"] = user_id
                d["collected_slots"] = dict(collected_slots)
                # Contexto compilado (traits de este turno ya leidos): desde
                # aca el perfilador corre en paralelo con orquestador,
                # conversador y gate.
                if "thread" not in profiler:
                    profiler["thread"] = self._start_profiler(user.id, message)
                return d

            #: Resultado de la tool del turno (lo llena handle_turn antes de
            #: reanudar el router); draft() lo lee para decidir si aplica el
            #: step destino. Un dict mutable porque draft() es un closure.
            tool_outcome: dict[str, Any] = {}

            def draft(compiled_context: dict[str, Any]) -> Any:
                # El ORQUESTADOR decide el tipo de turno con salida tipada
                # (OrchestratorAgent, fase 2.4: LLM + guardia dura sobre
                # allowed_transitions) y SOLO despues actua. Decidir != redactar.
                if compiled_context.get("system_turn"):
                    # Reanudacion tras la tool: el step destino decidido junto
                    # con el tool_call se aplica SOLO si la tool efectivamente
                    # hizo lo suyo (status ok). Si devolvio faltan_datos (o
                    # fallo), el flujo se queda donde estaba y el Conversador
                    # redacta con ese resultado pidiendo lo que falta.
                    tool_target = compiled_context.get("_flow_target")
                    if tool_target and tool_outcome.get("status") == "ok":
                        if tool_target != compiled_context.get("flow_node"):
                            compiler.retarget_step(compiled_context, tool_target)
                    else:
                        compiled_context["_flow_target"] = None
                    return self.conversador.draft_nl(compiled_context)

                decision = self.orchestrator_agent.decide(compiled_context)
                # Se conserva para exponer la decision del orquestador en el turno
                compiled_context["_decision"] = decision
                kind = decision.get("kind")
                if kind == "tool_call":
                    # El step destino decidido junto con la tool se aplica
                    # igual que en un turno 'nl': tras crear la visita el
                    # flujo avanza al cierre, no se queda pidiendo datos.
                    compiled_context["_flow_target"] = decision.get("flow_target")
                    return {"function_call": decision["function_call"]}
                if kind == "fallback":
                    return self._fallback_text(compiled_context)
                # Guardar flow_target si existe para navegacion post-draft
                flow_target = decision.get("flow_target")
                compiled_context["_flow_target"] = flow_target
                # El borrador se redacta YA con el step destino: si el
                # orquestador decidio avanzar, el Conversador tiene que pedir
                # lo que pide el step nuevo, no repetir lo del anterior.
                if flow_target and flow_target != compiled_context.get("flow_node"):
                    compiler.retarget_step(compiled_context, flow_target)
                return self.conversador.draft_nl(compiled_context)

            router = RouterStateMachine(
                compile_context=compile_context,
                draft_response=draft,
                tool_timeout_ms=self.tuning.tool_timeout_ms,
            )
            turn_result = router.handle_user_message(message, user_id=user.id, scenario=scenario)
            if turn_result is None:
                raise RuntimeError("router did not produce a turn result for immediate user turn")

            compiled = turn_result.compiled_context
            scenario_effective = str(compiled.get("scenario", ""))
            response = turn_result.response
            state_trace = [node.value for node in router.state_trace]

            # Decisiones de cada agente, para el rastro del turno. La del
            # orquestador se captura antes de que un tool_call reemplace
            # `compiled` por el contexto recompilado tras la tool.
            orchestrator_decision = compiled.get("_decision")
            draft_response: Any = None
            gate_result: dict[str, Any] | None = None

            system_turn = None
            if isinstance(response, dict) and "function_call" in response:
                kind = "tool_call"
                system_turn = execute_tool(session, user.id, response["function_call"], self.tool_handlers)
                tool_outcome.update(system_turn)
                resumed_result = router.handle_tool_result(system_turn)
                response = resumed_result.response
                draft_response = response
                compiled = resumed_result.compiled_context
                state_trace = [node.value for node in router.state_trace]
            elif self._is_fallback_response(response, compiled):
                kind = "fallback"
                draft_response = response
            else:
                kind = "nl"
                draft_response = response
                # Policy Gate: validar respuesta redactada contra criterios gate
                gate_result = self._policy_gate(
                    response, compiled, self._session_tools_called(session, user.id)
                )
                if not gate_result["approved"]:
                    kind = "derived"
                    response = self.gate_handoff_message
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
            session_state.flow_slots = {
                "allowed_transitions": flow_transitions,
                "missing_slots": flow_missing,
                "collected": collected_slots,
            }
            session_state.current_node = SessionNode.IDLE
            session_state.updated_at = datetime.now(timezone.utc)
            reply_text = json.dumps(response, ensure_ascii=False) if isinstance(response, dict) else str(response)
            self._persist_chat_history(session, user_id=user.id, role="user", content=message, conversation_id=conversation.id)
            self._persist_chat_history(session, user_id=user.id, role="assistant", content=reply_text, conversation_id=conversation.id)
            session.commit()

            # Perfilador: se espera su termino (arranco al compilar el contexto;
            # si el turno no compilo nada, corre aca en serie).
            profiler_thread, profiler_matches = profiler.setdefault(
                "thread", self._start_profiler(user.id, message)
            )
            profiler_thread.join()
            self._persist_profiler(session, profiler_matches, user.id)
            traits_after = self._current_traits(session, user.id)

            turn_context = self._build_turn_context(compiled)
            # Rastro por agente: ruteador (contexto) -> orquestador (decision)
            # -> conversador (borrador) -> gate (veredicto). El borrador se
            # conserva aunque el gate lo reemplace por el handoff.
            decisions = {
                "step": {
                    "before": step_before,
                    "after": flow_node,
                    "target": flow_target,
                    "allowed_transitions": flow_transitions,
                    "missing_slots": flow_missing,
                },
                "ruteador": {
                    # Bundle justificado del turno (doctrina 1.3 + fase 2.2):
                    # union sin duplicados de similitud, grounding, piso de
                    # seguridad y traits (o la decision del RouterAgent, con
                    # el mismo piso de seguridad forzado por codigo), cada
                    # entrada con su motivo. Es lo que hace auditable "por
                    # que entro este documento" sin abrir la KB -- ver
                    # ContextCompiler._resolve_bundle.
                    "bundle": compiled.get("bundle", []),
                    # "agent" si lo armo el RouterAgent real; "deterministic"
                    # si se uso el fallback (sin router_agent, o el agente
                    # fallo) -- ver ContextCompiler._resolve_bundle.
                    "source": compiled.get("bundle_source", "deterministic"),
                    "atoms": len(turn_context.get("atom_ids", [])),
                    "grounding_atoms": compiled.get("grounding_atoms", []),
                    "user_traits": compiled.get("user_traits", []),
                    "is_empty": bool(compiled.get("is_empty", False)),
                },
                "orquestador": {
                    "kind": kind,
                    "decision": orchestrator_decision,
                    "state_trace": state_trace,
                    # Por que decidio esto (auditable) y, si aplica, la
                    # transicion de step que propuso pero la guardia dura
                    # descarto por no estar en allowed_transitions del step
                    # activo (ver kb_agent.agents.orchestrator_agent.apply_transition_guard).
                    "reason": orchestrator_decision.get("reason") if isinstance(orchestrator_decision, dict) else None,
                    "step_target_vetado": (
                        orchestrator_decision.get("step_target_vetado")
                        if isinstance(orchestrator_decision, dict)
                        else None
                    ),
                },
                "conversador": {"draft": draft_response},
                "gate": gate_result if gate_result is not None else {"approved": None, "skipped": kind},
                "tool": {"called": True, **system_turn} if isinstance(system_turn, dict) else {"called": False},
            }

            self._persist_turn(
                session,
                turn_id=turn_id,
                user_id=user.id,
                external_id=external_id,
                conversation_id=conversation.id,
                decisions=decisions,
                draft=reply_text,
                duration_ms=int((perf_counter() - turn_started) * 1000),
            )

            return {
                "turn_id": turn_id,
                "conversation_id": conversation.id,
                "user_id": user.id,
                "question": message,
                "kind": kind,
                "reply": response,
                "reply_text": reply_text,
                "system_turn": system_turn,
                "traits_before": traits_before,
                "traits_after": traits_after,
                "collected_slots": collected_slots,
                "used_traits_in_context": compiled.get("user_traits", []),
                "scenario_effective": scenario_effective,
                "scenario_source": scenario_source,
                "state_trace": state_trace,
                "flow_node": flow_node,
                "allowed_transitions": flow_transitions,
                "missing_slots": flow_missing,
                "context": turn_context,
                "decisions": decisions,
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
    def _load_gate_atoms(self) -> list[dict[str, Any]]:
        """Carga los ``GateCriterion`` (``type.knowledge.gate``) para el ``GateAgent``.

        Fail-open a lista vacia: si la KB no tiene la familia gate o el
        reader falla, ``GateAgent`` (ver su docstring) aprueba por defecto en
        vez de que falle la construccion del orquestador.
        """
        try:
            return self.knowledge_ops.docs_by_type("gate")
        except Exception:
            return []

    def _load_step_atoms(self) -> list[dict[str, Any]]:
        """Carga los ``ConversationStep`` (``type.knowledge.step``) para el ``OrchestratorAgent``,
        cada uno con sus ``allowed_transitions`` resueltas del grafo (aristas ``transitions_to``).

        Fail-open a lista vacia: si la KB no tiene el diagrama de flujo o el
        reader falla, ``OrchestratorAgent`` (ver ``render_orchestrator_flow``)
        decide sin grafo (``step_target`` siempre ``null``) en vez de que
        falle la construccion del orquestador.
        """
        try:
            flow = self.knowledge_ops.flow
            steps = []
            for doc in self.knowledge_ops.docs_by_type("step"):
                step = flow.by_id(doc["id"])
                steps.append({**doc, "allowed_transitions": list(step.transitions) if step else []})
            return steps
        except Exception:
            return []

    def _load_agent_framing(self, role: AgentRole) -> str | None:
        """Encuadre de negocio del agente ``role`` desde la KB (familia ``agent``).

        Busca un ``AgentFraming`` (``type.knowledge.agent``) cuyo campo
        ``role`` coincida y devuelve su ``framing`` (mas ``examples`` si los
        tiene). Fail-open a ``None``: sin atom (o si el reader falla), el
        ``render_*`` correspondiente usa su encuadre generico. Asi el
        vocabulario del negocio (clinico, gastronomico, etc.) vive en la KB,
        no hardcodeado en el codigo del agente.
        """
        try:
            atoms = self.knowledge_ops.docs_by_type("agent")
        except Exception:
            return None
        for atom in atoms:
            doc = self.knowledge_ops.doc(atom["id"]) or atom
            if str(doc.get("role") or "").strip() != str(role):
                continue
            framing = str(doc.get("framing") or "").strip()
            examples = str(doc.get("examples") or "").strip()
            if framing and examples:
                return f"{framing}\n\nEjemplos:\n{examples}"
            return framing or examples or None
        return None

    @staticmethod
    def _tool_name_from_system_turn(system_turn: Any) -> str | None:
        """Nombre de la tool ejecutada, si ``system_turn`` trae un resultado real.

        ``system_turn['content']`` es el payload de ``execute_tool`` serializado
        a JSON (ver ``RouterStateMachine._resume_from_waiting_tool``); ese
        payload trae ``{"tool": <nombre>, "status": ..., ...}``.
        """
        if not isinstance(system_turn, Mapping):
            return None
        content = system_turn.get("content")
        if not isinstance(content, str):
            return None
        try:
            payload = json.loads(content)
        except (TypeError, ValueError):
            return None
        tool = payload.get("tool") if isinstance(payload, Mapping) else None
        return str(tool) if tool else None

    @staticmethod
    def _persist_turn(
        session: Session,
        *,
        turn_id: str,
        user_id: int,
        external_id: str,
        decisions: Mapping[str, Any],
        draft: str,
        conversation_id: int | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Persiste el rastro del turno en ``turns`` (fase 3.1).

        Hasta ahora el rastro se calculaba y se descartaba: solo viajaba en la
        respuesta HTTP, y por eso al reabrir una conversacion el Turn Inspector
        mostraba "0 atoms, step —". Se guarda el borrador del Conversador ANTES
        del gate: si el gate lo rechaza, el texto que ve el paciente es otro y
        queremos poder auditar los dos.

        No rompe el turno si falla: el rastro es para auditoria, no para
        responderle a la paciente. Si la tabla no existe (base vieja sin la
        migracion) se ignora.
        """
        step = decisions.get("step") or {}
        tool = decisions.get("tool") or {}
        try:
            session.add(
                Turns(
                    turn_id=turn_id,
                    session_id=external_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    kind=TurnKind.AGENT,
                    step_before=step.get("before"),
                    step_after=step.get("after"),
                    decision=dict(decisions.get("orquestador") or {}),
                    draft=str((decisions.get("conversador") or {}).get("draft") or draft),
                    gate=dict(decisions.get("gate") or {}),
                    bundle=list((decisions.get("ruteador") or {}).get("bundle") or []),
                    tool=dict(tool) if tool else None,
                    duration_ms=duration_ms,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("no se pudo persistir el rastro del turno en turns")

    @staticmethod
    def _session_tools_called(session: Session, user_id: int) -> list[str]:
        """Tools que ya se ejecutaron antes en esta conversacion.

        El pre-filtro del gate es por turno, pero una afirmacion puede referirse
        legitimamente a algo hecho en un turno anterior. Medido en el CLI real:
        el turno 2 ejecuto ``agendar_recordatorio`` (fila real en SQL) y en el
        turno 3 el agente respondio "ya esta confirmado tu recordatorio" --
        cierto-- con ``tool_called`` False en ese turno; el gate lo derivaba a
        un humano sin motivo.

        Se leen de ``turns`` (fase 3.1). Si la tabla todavia no existe en una
        base vieja, se devuelve vacio: el gate vuelve a su comportamiento por
        turno, que es el conservador.
        """
        try:
            rows = session.query(Turns.tool).filter(Turns.user_id == user_id).all()
        except Exception:
            return []
        names: list[str] = []
        for (tool,) in rows:
            if isinstance(tool, Mapping) and tool.get("called") and tool.get("tool"):
                names.append(str(tool["tool"]))
        return names

    @staticmethod
    def _step_and_client_facts(compiled: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Contexto declarado EXTRA para el gate, ademas de facts/rules.

        Medido en Vitali: el gate rechazaba el cierre ("afirma 30 minutos,
        invitacion por correo, jueves en la tarde, un email... no declarados
        en el contexto") cuando esos datos venian de (a) las instrucciones
        del ConversationStep activo, que son KB, y (b) lo que el propio
        cliente dijo en la conversacion (su dia preferido, su correo). Ambos
        entran como lineas de contexto declarado: el step con su id, y los
        mensajes del cliente (solo rol user, ya scrubbeados de PII al
        persistirse) como una linea "conversacion-cliente".
        """
        extra: list[dict[str, Any]] = []
        step = compiled.get("step")
        if isinstance(step, Mapping) and (step.get("instructions") or step.get("required_slots")):
            body = " ".join(
                part for part in (
                    str(step.get("instructions") or "").strip(),
                    f"Datos que este paso reune: {step.get('required_slots')}" if step.get("required_slots") else "",
                ) if part
            )
            extra.append({
                "id": str(step.get("id") or step.get("tag") or "step-actual"),
                "title": f"Paso actual de la conversacion: {step.get('title') or step.get('tag') or ''}".strip(),
                "body": body,
            })
        said: list[str] = []
        for turn in compiled.get("history") or []:
            if isinstance(turn, Mapping) and turn.get("role") == "user" and str(turn.get("content") or "").strip():
                said.append(str(turn["content"]).strip())
        question = str(compiled.get("question") or "").strip()
        if question:
            said.append(question)
        if said:
            extra.append({
                "id": "conversacion-cliente",
                "title": "Lo que el cliente dijo en esta conversacion (datos aportados por el, no por la KB)",
                "body": "\n".join(f"- {line}" for line in said),
            })
        return extra

    def _policy_gate(
        self,
        response: str,
        compiled: Mapping[str, Any],
        session_tools_called: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Veredicto del ``GateAgent`` (fase 2.3) sobre la respuesta redactada.

        ``tool_called`` se deriva de ``compiled["system_turn"]``: es la unica
        senal de que hubo una ejecucion REAL de tool grounding esta respuesta
        (lo mismo que ya usan ``draft()``/``build_nl_prompt`` para inyectar el
        resultado de la tool al Conversador). Este metodo solo se llama desde
        la rama ``kind == "nl"`` de ``handle_turn``, que es precisamente donde
        el Conversador puede redactar libremente y, sin este gate, afirmar una
        accion que nunca ocurrio (el caso medido: "¡Listo! Te agendé..." con
        ``tool.called: false``).

        Fail-open EXPLICITO: si ``GateAgent.evaluate`` lanza -- LLM caido,
        cuota agotada, parseo de la salida estructurada, lo que sea -- este
        metodo NO propaga la excepcion. Loguea y aprueba (``approved=True``),
        igual que el ``try/except`` que ya envolvia la lectura de la KB en la
        version anterior de este gate: un juez caido no puede dejar a un
        paciente sin respuesta.
        """
        if not isinstance(response, str) or not response.strip():
            return {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}

        system_turn = compiled.get("system_turn")
        tool_called = isinstance(system_turn, Mapping) and bool(system_turn)
        tool_name = self._tool_name_from_system_turn(system_turn) if tool_called else None
        step = compiled.get("flow_node")

        # Facts/rules que la KB declaro para este turno: es el universo contra
        # el que el gate juzga grounding (la respuesta no puede afirmar
        # atributos que no esten aca). Ver GateCriterion de grounding en la KB.
        declared_facts = [
            *compiled.get("domain_facts", []),
            *compiled.get("rules", []),
            *self._step_and_client_facts(compiled),
        ]

        try:
            return self.gate.evaluate(
                response,
                tool_called=tool_called,
                tool_name=tool_name,
                step=step,
                session_tools_called=session_tools_called,
                declared_facts=declared_facts,
            )
        except Exception:
            logger.exception("GateAgent fallo evaluando la respuesta; fail-open (approved=True)")
            return {"approved": True, "reasons": [], "action": "pass", "criterion_ids": [], "fail_open": True}

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

        Cada item se cruza con ``bundle`` (el bundle justificado del turno,
        ver ``ContextCompiler._build_bundle``) por ``doc_id`` para heredar el
        ``motivo`` real por el que entro (piso de seguridad, grounding, trait
        del usuario, similitud) y el ``score`` real de similitud (``None`` si
        entro sin ranking semantico). Antes el score era 1.0 hardcodeado para
        todo el mundo -- ya no.
        """
        items: list[dict[str, Any]] = []
        atom_ids: list[str] = []
        include_tags: set[str] = set()
        grounding = set(compiled.get("grounding_atoms", []))
        bundle = compiled.get("bundle", [])
        bundle_by_id = {b.get("doc_id"): b for b in bundle if b.get("doc_id")}

        def _add(atom: Mapping[str, Any], fallback_role: str) -> None:
            atom_id = atom.get("id", "")
            tags = list(atom.get("tags", []))
            bundle_entry = bundle_by_id.get(atom_id)
            items.append({
                "atom_id": atom_id,
                "title": atom.get("title") or atom_id,
                "role": self._semantic_role(tags, fallback_role),
                "family": atom.get("family"),
                "score": bundle_entry.get("score") if bundle_entry else None,
                "motivo": bundle_entry.get("motivo", "") if bundle_entry else "",
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
            # Bundle justificado completo del turno (incluye entradas que no
            # proyectan a domain_facts/rules, p.ej. traits o steps que
            # entraron por similitud): auditoria completa, no solo la
            # proyeccion tipada que arma ``items``.
            "bundle": bundle,
        }

    # ── perfilador ────────────────────────────────────────────────────────
    def _start_profiler(self, user_id: int, turn_text: str) -> tuple[threading.Thread, list]:
        """Corre el ANALISIS del perfilador (embedder + LLM) en un hilo daemon.

        Devuelve ``(thread, sink)``: el hilo no toca la base, deja los matches
        en ``sink`` y el turno los persiste con su propia sesion despues del
        join (ver ``TraitExtractor.analyze``/``persist``). Dos hilos
        escribiendo la misma conexion sqlite se pisan ("cannot commit
        transaction - SQL statements in progress", medido en la suite); asi
        la unica parte paralela es la cara, que es la que interesa.

        Un fallo del perfilador no puede tumbar el turno: se loguea y el
        turno sigue con ``traits_after == traits_before``.
        """
        # scrub inline antes de que el perfilador vea nada (regla PII). El
        # evento se construye directo (no pasa por la cola compartida del
        # bus: con turnos concurrentes cada hilo consumia el evento de otro).
        event = TurnClosedEvent(user_id=user_id, turn_text_scrubbed=scrub(turn_text))
        sink: list = []

        def _analyze() -> None:
            try:
                extractor = TraitExtractor(
                    knowledge=self.knowledge_ops,
                    llm_mapper=self.trait_mapper,
                    knowledge_ops=self.knowledge_ops,
                )
                sink.extend(extractor.analyze(user_id=event.user_id, turn_text=event.turn_text_scrubbed))
            except Exception:
                logger.exception("perfilador fallo; el turno sigue sin traits nuevos")

        thread = threading.Thread(target=_analyze, name=f"profiler-{user_id}", daemon=True)
        thread.start()
        return thread, sink

    def _persist_profiler(self, session: Session, matches: list, user_id: int) -> None:
        """Escribe en ``user_traits`` lo que el hilo del perfilador analizo."""
        if not matches:
            return
        try:
            TraitExtractor(
                knowledge=self.knowledge_ops,
                identity_session=session,
                llm_mapper=self.trait_mapper,
                knowledge_ops=self.knowledge_ops,
            ).persist(user_id=user_id, matches=matches)
        except Exception:
            session.rollback()
            logger.exception("no se pudieron persistir los traits del perfilador")

    # ── reflector ─────────────────────────────────────────────────────────
    def run_reflector(self) -> list[dict[str, Any]]:
        reader = ReflectorBatchReaderJob(self.SessionLocal, self._reflector_checkpoint_store)
        rows = reader.run(trigger="cron")
        generator = ReflectorAtomGenerator(
            kb_root=self.kb_root, pythonpath=self.repo_root, knowledge=self.knowledge_ops,
            registry_root=self.repo_root,
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
        if state is not None:
            return state
        # Misma carrera que ``ensure_user``: el PK es ``user_id``, dos requests
        # concurrentes del mismo usuario nuevo compiten por crear el estado y
        # el segundo INSERT viola el PK. rollback + re-SELECT del ganador.
        state = SessionState(user_id=user_id, current_node=SessionNode.IDLE)
        session.add(state)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            state = session.get(SessionState, user_id)
        return state

    def _resolve_conversation(
        self, session: Session, *, user_id: int, channel: str | None
    ) -> Conversation:
        """Conversacion activa del usuario, o una nueva si la ultima expiro.

        Criterio de cierre (config ``tuning.conversation_idle_ttl_s``): si la
        conversacion abierta mas reciente lleva mas de ese TTL sin actividad,
        se cierra y se abre una nueva. Asi el historial que va al prompt
        (filtrado por ``conversation_id``) no cruza el limite de una
        conversacion vieja -- antes se infería por dia calendario y se
        mezclaba todo el ``chat_history`` del usuario.
        """
        now = datetime.now(timezone.utc)
        ttl = timedelta(seconds=self.tuning.conversation_idle_ttl_s)
        current = (
            session.query(Conversation)
            .filter(
                Conversation.user_id == user_id,
                Conversation.status == ConversationStatus.OPEN,
            )
            .order_by(Conversation.last_activity_at.desc())
            .first()
        )
        if current is not None:
            last = current.last_activity_at
            if last is not None and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last is None or now - last <= ttl:
                current.last_activity_at = now
                session.commit()
                return current
            # expiro por inactividad: cerrarla y abrir una nueva
            current.status = ConversationStatus.CLOSED
            current.closed_at = now
            session.commit()

        conv = Conversation(
            user_id=user_id,
            status=ConversationStatus.OPEN,
            channel=channel,
            started_at=now,
            last_activity_at=now,
        )
        session.add(conv)
        session.commit()
        return conv

    def _persist_chat_history(
        self,
        session: Session,
        *,
        user_id: int,
        role: str,
        content: str,
        conversation_id: int | None = None,
    ) -> ChatHistory:
        row = ChatHistory(
            user_id=user_id,
            role=role,
            content=scrub(content),
            pii_scrubbed=True,
            conversation_id=conversation_id,
        )
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
