"""Compilador de contexto: navega SLDB + KGDB + SQL para producir CompiledDocument.

Doctrina de selección (ver KB-DOCTRINE.md + modelation-guide.md):
  - Una KB = un negocio. Los átomos se seleccionan por su MODELO tipado, no por
    un tag ``atom_type:*``. El eje de selección es ``type.knowledge.<tipo>``,
    derivado del ``__semantics__`` de cada modelo (DomainAtom, RuleAtom,
    SelfDeclaration, StyleGuide, CapabilityBoundary, StrategyRule, FallbackRule,
    ToolAtom, ConversationStep, TraitAtom).
  - Cada tipo aporta sus CAMPOS tipados, no un ``answer`` genérico:
      self      -> statement                     (persona.whoami)
      style     -> tone/register/phrases/length   (persona.estilo)
      boundary  -> restriction/conditions/escal.  (persona.limites)
      strategy  -> goal/approach/priorities       (strategy)
      fallback  -> fallback_message               (fallback_text)
      domain    -> answer                         (grounding del negocio)
      rule      -> answer/conditions              (grounding del negocio)
      tool      -> parameters (JSON schema)       (tools)
  - ``scenario`` se conserva solo como etiqueta informativa del negocio y como
    pista opcional para el enriquecimiento KGDB; NUNCA descarta átomos válidos.

Flujo:
  1. Resuelve scenario (etiqueta informativa; argumento -> session_state -> default)
  2. Selecciona atoms por MODELO (type.knowledge.*) en SLDB
  3. Resuelve traits del usuario contra SQL (user:traits.* del catálogo)
  4. [Opcional] Navega grafo KGDB para resolver nodo de flujo, transiciones, slots
  5. Compila a un CompiledDocument con facts, rules, tools, grounding + flujo
"""
from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from kb_agent.agents.router import apply_security_floor
from kb_agent.models.knowledge import (
    CapabilityBoundary,
    ConversationStep,
    DomainAtom,
    FallbackRule,
    RuleAtom,
    SelfDeclaration,
    StrategyRule,
    StyleGuide,
    ToolAtom,
    TraitAtom,
)
from kb_agent.models_sql.identity import UserTraits, Users
from kb_agent.models_sql.session import ChatHistory

logger = logging.getLogger(__name__)

from .compiled_document import CompiledDocument
from .kgdb_reader import KGDBReader

if TYPE_CHECKING:
    from knowledge_base.operations import KnowledgeOperations
    from kb_agent.agents.router import RouterAgent


class SessionStateLike(Protocol):
    active_domain: str | None


@dataclass(slots=True)
class ContextCompiler:
    #: Unico dueno del acceso al store de la KB (docs_by_type / doc). Antes
    #: era un ``SLDBReader`` propio de kb_agent que reimplementaba, con match
    #: por substring, lo que esta clase ya hacia sobre el MISMO store: dos
    #: parseos y dos caches por proceso. Ver el bloque "runtime: acceso al
    #: store" en knowledge_base/operations.py.
    #:
    #: Es distinto de ``knowledge_ops`` de abajo, aunque en produccion el
    #: orquestador inyecta LA MISMA instancia en los dos: este campo pide solo
    #: lectura del store (barata, sin embedder ni SQL), mientras que
    #: ``knowledge_ops`` significa "ops cableada para ranking semantico y
    #: traits por SQL" -- lo que los tests unitarios dejan en None a proposito
    #: para no pagar el modelo de embeddings.
    knowledge: "KnowledgeOperations"
    kgdb: KGDBReader | None = None
    identity_session: Session | None = None
    session_state_loader: Callable[[int], SessionStateLike | None] | None = None
    #: Capa knowledge_base (SLDB+KGDB+SQL) para resolver traits contra su
    #: TraitAtom. El orquestador crea UNA instancia (embedder cacheado por
    #: instancia) y la reutiliza en todos los turnos; si no se inyecta (tests
    #: unitarios del compilador), se resuelve localmente via ``knowledge``.
    #: TAMBIEN es la fuente del embedder para la similitud que arma el bundle
    #: del turno (ver ``_build_bundle``/``_semantic_candidates``); sin ella no
    #: hay ranking semantico y el bundle cae al modo legado (todo domain/rule,
    #: sin tope).
    knowledge_ops: "KnowledgeOperations | None" = None
    #: Ruteador de contexto (fase 2.2, agente): decide el bundle con LLM +
    #: tools de KB (``explore_multi``/``explore``/``show``) en vez de la
    #: union deterministica de ``_build_bundle``. El orquestador crea UNA
    #: instancia y la reutiliza en todos los turnos, igual que
    #: ``knowledge_ops``. Si es ``None`` (tests offline sin
    #: ``FakeRouterAgent``, o compilador usado standalone) o si
    #: ``RouterAgent.route`` lanza, se cae al fallback deterministico
    #: (``_build_bundle``) -- mismo patron fail-open que
    #: ``Orchestrator._policy_gate``. Ver ``_resolve_bundle``.
    router_agent: "RouterAgent | None" = None
    #: Tope del bundle justificado (ver ``_build_bundle``). Solo se aplica
    #: cuando hay ``knowledge_ops`` (hay ranking real con el que decidir que
    #: cae fuera); sin el, no hay tope (modo legado). El bundle armado por
    #: ``router_agent`` tambien respeta este tope (ver
    #: ``_build_bundle_via_agent``).
    max_bundle_size: int = 12
    #: Cuantos mensajes recientes de ``chat_history`` entran a ``history``.
    history_limit: int = 6

    def compile(
        self,
        *,
        question: str,
        user_id: int | None,
        scenario: str | None = None,
        trigger: str = "user",
        session_state: SessionStateLike | None = None,
        conversation_id: int | None = None,
    ) -> CompiledDocument:
        resolved_scenario = self._resolve_scenario(
            user_id=user_id,
            scenario=scenario,
            trigger=trigger,
            session_state=session_state,
        )

        # KGDB primero: el bundle necesita el grounding del step activo antes
        # de armarse. current_step viene del estado de sesion persistido en SQL.
        current_step = getattr(session_state, "flow_node", None)
        active_step, allowed_transitions, grounding_ids = self._resolve_kgdb_active_step(current_step)

        tools = self._find_tools()
        user_traits = self._load_user_traits(user_id)
        history = self._load_history(user_id, conversation_id=conversation_id)

        persona = self._extract_persona()
        strategy = self._extract_strategy()
        fallback_text = self._extract_fallback()

        # Doctrina 1.3 + fase 2.2 (agente): el contexto ya no es "todo
        # domain/rule" (score 1.0 hardcodeado); es un bundle JUSTIFICADO (ver
        # ``_resolve_bundle``). ``domain_facts``/``rules`` son la proyeccion
        # tipada de ese bundle, asi ``decide_turn``/``build_nl_prompt`` no
        # cambian de forma.
        bundle, domain_facts, rules, bundle_source = self._resolve_bundle(
            question=question,
            active_step=active_step,
            grounding_ids=grounding_ids,
            user_traits=user_traits,
            history=history,
        )

        doc = CompiledDocument(
            scenario=resolved_scenario,
            question=question,
            user_traits=user_traits,
            domain_facts=domain_facts,
            rules=rules,
            tools=tools,
            bundle=bundle,
            history=history,
            persona=persona,
            strategy=strategy,
            fallback_text=fallback_text,
            is_empty=not domain_facts and not rules,
        )
        doc.flow_node = active_step
        doc.allowed_transitions = allowed_transitions
        doc.grounding_atoms = grounding_ids
        doc.step = self.step_context(active_step)
        # ``CompiledDocument`` no declara este campo (no es parte de su
        # contrato tipado, ver su docstring): se asigna como atributo de
        # instancia, igual que los 3 de arriba en el caso de
        # ``flow_node``/``allowed_transitions``/``grounding_atoms`` antes de
        # que fueran campos formales -- ``to_dict`` (``self.__dict__``) lo
        # incluye igual. Rastro (fase 2.2): "agent" si lo armo el
        # ``RouterAgent`` real, "deterministic" si se uso el fallback
        # (``_build_bundle``) -- ver ``Orchestrator.handle_turn``,
        # ``decisions.ruteador.source``.
        doc.bundle_source = bundle_source
        return doc

    def _resolve_scenario(
        self,
        *,
        user_id: int | None,
        scenario: str | None,
        trigger: str,
        session_state: SessionStateLike | None,
    ) -> str:
        if scenario:
            return scenario

        active_domain = getattr(session_state, "active_domain", None)
        if active_domain:
            return active_domain

        if trigger != "cron" and user_id is not None and self.session_state_loader is not None:
            loaded_state = self.session_state_loader(user_id)
            loaded_domain = getattr(loaded_state, "active_domain", None) if loaded_state is not None else None
            if loaded_domain:
                return loaded_domain

        return self.default_scenario()

    def default_scenario(self) -> str:
        """Etiqueta informativa del negocio (NO es un filtro de selección).

        Deriva un rótulo estable a partir de los tags ``domain:*`` presentes en
        la KB. Como una KB = un negocio, este valor solo describe la KB; los
        átomos ya se seleccionan por ``atom_type`` con independencia de él.
        """
        scenarios = sorted(
            {
                tag.split(":", 1)[1]
                for r in self._records()
                for tag in r.get("tags", [])
                if tag.startswith("domain:")
            }
        )
        top_level = [s for s in scenarios if "." not in s]
        return top_level[0] if top_level else scenarios[0] if scenarios else ""

    #: tipos de la taxonomía knowledge (models/knowledge/*). Se recorren para
    #: reunir todos los atoms del negocio con independencia del modelo.
    _MODEL_TYPES = (
        "domain", "rule", "tool", "trait", "step",
        "self", "style", "boundary", "strategy", "fallback",
    )

    def _records(self) -> list[dict[str, Any]]:
        """Todos los atoms de la KB (unión de todos los tipos tipados)."""
        seen: dict[str, dict[str, Any]] = {}
        for tipo in self._MODEL_TYPES:
            for m in self.knowledge.docs_by_type(tipo):
                seen[m["id"]] = m
        return list(seen.values())

    def _find_by_model(self, tipo: str) -> list[dict[str, Any]]:
        """Selecciona los atoms de un tipo tipado via ``type.knowledge.<tipo>``.

        Devuelve el doc completo (todos los campos del modelo) resuelto contra
        el store, ordenado por id para estabilidad.
        """
        matched = self.knowledge.docs_by_type(tipo)
        docs = []
        for m in matched:
            doc = self.knowledge.doc(m["id"]) or m
            docs.append(doc)
        return sorted(docs, key=lambda d: d.get("id", ""))

    #: modelo tipado por cada ``tipo`` de la doctrina (ver ``_MODEL_TYPES``).
    #: Se usa para exponer ``family()`` (declarada en la clase, ClassVar
    #: ``__family__``) sin derivarla del prefijo del tag en el consumidor, y
    #: para resolver el ``tipo``/``family`` de un doc_id arbitrario que entro
    #: al bundle por similitud o grounding (``_tipo_y_family_de_doc``).
    _MODEL_CLS_BY_TIPO: ClassVar[dict[str, type]] = {
        "domain": DomainAtom,
        "rule": RuleAtom,
        "tool": ToolAtom,
        "trait": TraitAtom,
        "step": ConversationStep,
        "self": SelfDeclaration,
        "style": StyleGuide,
        "boundary": CapabilityBoundary,
        "strategy": StrategyRule,
        "fallback": FallbackRule,
    }

    def _find_atoms(self, tipo: str) -> list[dict[str, Any]]:
        """Grounding del negocio: domain/rule con su ``answer`` como body.

        Conserva tags y title para que el orquestador arme el contexto del turno
        sin re-leer el store (brecha #2). Tambien propaga ``family``, tomada de
        la CLASE del modelo tipado (``.family()``), no del prefijo del tag: un
        RuleAtom es familia "domain" aunque lleve tags "conversation:*".
        """
        model_cls = self._MODEL_CLS_BY_TIPO.get(tipo)
        family = model_cls.family() if model_cls is not None else None
        result: list[dict[str, Any]] = []
        for d in self._find_by_model(tipo):
            result.append({
                "id": d.get("id", ""),
                "body": d.get("answer", ""),
                "tags": d.get("tags", []),
                "title": d.get("title") or d.get("id", ""),
                "family": family,
            })
        return result

    @staticmethod
    def _tipo_for_doc(doc: dict[str, Any]) -> str | None:
        """Deriva el ``tipo`` (domain/rule/trait/...) del tag ``type.knowledge.<tipo>``."""
        for tag in doc.get("tags") or []:
            if isinstance(tag, str) and tag.startswith("type.knowledge."):
                return tag.split("type.knowledge.", 1)[1]
        return None

    def _tipo_y_family_de_doc(self, doc: dict[str, Any] | None) -> tuple[str | None, str | None]:
        if not doc:
            return None, None
        tipo = self._tipo_for_doc(doc)
        model_cls = self._MODEL_CLS_BY_TIPO.get(tipo) if tipo else None
        return tipo, (model_cls.family() if model_cls is not None else None)

    # ── bundle justificado del turno (doctrina 1.3) ────────────────

    #: Tag que marca el piso de seguridad: RuleAtom de farmacovigilancia y
    #: anti-alucinacion que entran SIEMPRE al bundle, sin importar la
    #: similitud con la pregunta (un PSP no puede quedarse sin ellas).
    _SECURITY_FLOOR_TAG: ClassVar[str] = "conversation:security"

    #: Piso absoluto de score semantico (ruido de embedding), mismo default
    #: que ``KnowledgeOperations.explore_multi``.
    _SEMANTIC_NOISE_FLOOR: ClassVar[float] = 0.05

    def _semantic_candidates(self, question: str, max_results: int) -> list[dict[str, Any]]:
        """Top-k por similitud coseno contra la pregunta, cualquier familia.

        Delega en ``KnowledgeOperations.semantic_search``: misma formula de
        coseno, mismo piso de ruido, mismo orden por score. Antes esto
        reimplementaba el loop aca porque ``semantic_search`` llamaba a
        ``_read_doc`` por cada documento y ese metodo reescanea la KB entera en
        cada llamada -- O(n^2), ~4 min sobre la KB real. Esa causa ya no
        existe: ``semantic_search`` lee el payload que el record ya trae.

        El filtro por ``self._records()`` NO es un detalle de implementacion:
        ``semantic_search`` recorre TODOS los documentos del store, y el
        compilador solo compila los ``_MODEL_TYPES`` de la doctrina. Sin este
        filtro entrarian al bundle los atoms de familia ``gate``, que son
        invisibles al turno a proposito (se consumen post-draft en el policy
        gate, no como grounding del Conversador).
        """
        if self.knowledge_ops is None or not question:
            return []
        try:
            hits = self.knowledge_ops.semantic_search(
                question, threshold=self._SEMANTIC_NOISE_FLOOR,
            )
        except Exception:
            return []
        compilables = {d.get("id", "") for d in self._records()}
        return [
            {"id": h["id"], "score": h["score"]}
            for h in hits if h["id"] in compilables
        ][:max_results]

    def _security_floor_ids(self) -> set[str]:
        """Ids de las ``RuleAtom`` con tag ``conversation:security``: el piso
        de seguridad no negociable (farmacovigilancia). Fuente unica de
        verdad, usada tanto por el fallback deterministico (``_build_bundle``)
        como por el camino del ``RouterAgent`` (``_build_bundle_via_agent``,
        via ``kb_agent.agents.router.apply_security_floor``): un LLM no es
        garantia, asi que ambos caminos fuerzan la MISMA lista por codigo.
        """
        return {
            d.get("id", "")
            for d in self._find_by_model("rule")
            if self._SECURITY_FLOOR_TAG in (d.get("tags") or [])
        }

    def _build_bundle(
        self,
        *,
        question: str,
        active_step: str | None,
        grounding_ids: list[str],
        user_traits: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
        """Arma el bundle justificado del turno: union sin duplicados de

          a) similitud   -- ``_semantic_candidates(question)``, top-k contra la KB entera
             (cualquier familia: domain, rule, trait, step, tool -- doctrina
             del ruteador: mete cualquier documento si lo justifica).
          b) grounding    -- los ``grounding_atoms`` del step activo (KGDB).
          c) piso de seguridad -- RuleAtom con tag ``conversation:security``,
             SIEMPRE, sin importar la similitud.
          d) traits       -- los que ya resuelve ``_load_user_traits``.

        Duplicados: si un doc entra por mas de una via, sus motivos se
        CONCATENAN (orden de evaluacion arriba: piso -> grounding -> traits
        -> similitud) y se conserva el score MAS ALTO visto (solo la
        similitud aporta score; el resto entra con score None).

        Tope (``max_bundle_size``): el piso de seguridad, el grounding del
        step activo y los traits del usuario son OBLIGATORIOS (entran
        siempre, nunca los tapa el tope); el resto de la capacidad la llenan
        los mejores resultados de similitud por score. Sin ``knowledge_ops``
        no hay señal de ranking: se cae al modo previo a 1.3 (TODOS los
        domain/rule atoms, sin tope), igual que ``_load_user_traits`` cae a
        resolucion local cuando no hay ``knowledge_ops`` inyectado.

        Devuelve ``(bundle, domain_facts, rules)``: ``domain_facts``/``rules``
        son la proyeccion tipada (mismo shape que ``_find_atoms``) del
        subconjunto DomainAtom/RuleAtom del bundle final.
        """
        candidates: dict[str, dict[str, Any]] = {}
        order: list[str] = []

        def _add(doc_id: str, motivo: str, score: float | None) -> None:
            if not doc_id:
                return
            entry = candidates.get(doc_id)
            if entry is None:
                entry = {"motivos": [], "score": None}
                candidates[doc_id] = entry
                order.append(doc_id)
            if motivo not in entry["motivos"]:
                entry["motivos"].append(motivo)
            if score is not None and (entry["score"] is None or score > entry["score"]):
                entry["score"] = score

        # a) piso de seguridad: SIEMPRE.
        security_ids = self._security_floor_ids()
        for doc_id in sorted(security_ids):
            _add(doc_id, "piso de seguridad", None)

        mandatory_ids = set(security_ids)

        # b) grounding del step activo.
        if active_step:
            short_step = active_step.split(":", 1)[-1] if ":" in active_step else active_step
            for doc_id in grounding_ids:
                _add(doc_id, f"grounding de {short_step}", None)
                mandatory_ids.add(doc_id)

        # c) traits del usuario ya resueltos contra su TraitAtom.
        for trait in user_traits:
            doc_id = trait.get("trait_id", "")
            _add(doc_id, "trait del usuario", None)
            mandatory_ids.add(doc_id)

        capped = self.knowledge_ops is not None
        if capped:
            # d) similitud: top-k contra la pregunta, cualquier familia
            # (``_semantic_candidates``, ver su docstring: no llama a
            # ``explore_multi`` por el bug de performance que documenta).
            for item in self._semantic_candidates(question, self.max_bundle_size):
                score = item["score"]
                _add(item["id"], f"similitud {score:.2f}", score)
        else:
            # Sin capacidad semantica (sin knowledge_ops): modo previo a 1.3,
            # todo domain/rule entra, sin tope.
            for d in self._find_by_model("domain") + self._find_by_model("rule"):
                doc_id = d.get("id", "")
                _add(doc_id, "sin ranking semántico (knowledge_ops no inyectado)", None)
                mandatory_ids.add(doc_id)

        if capped:
            mandatory = [doc_id for doc_id in order if doc_id in mandatory_ids]
            optional = sorted(
                (doc_id for doc_id in order if doc_id not in mandatory_ids),
                key=lambda doc_id: candidates[doc_id]["score"] or 0.0,
                reverse=True,
            )
            remaining = max(self.max_bundle_size - len(mandatory), 0)
            selected_ids = mandatory + optional[:remaining]
        else:
            selected_ids = order

        bundle: list[dict[str, Any]] = []
        domain_facts: list[dict[str, str]] = []
        rules: list[dict[str, str]] = []
        for doc_id in selected_ids:
            doc = self.knowledge.doc(doc_id)
            tipo, family = self._tipo_y_family_de_doc(doc)
            entry = candidates[doc_id]
            bundle.append({
                "doc_id": doc_id,
                "family": family,
                "motivo": "; ".join(entry["motivos"]),
                "score": entry["score"],
            })
            if doc and tipo in ("domain", "rule"):
                projected = {
                    "id": doc.get("id", doc_id),
                    "body": doc.get("answer", ""),
                    "tags": doc.get("tags", []),
                    "title": doc.get("title") or doc.get("id", doc_id),
                    "family": family,
                }
                (domain_facts if tipo == "domain" else rules).append(projected)

        return bundle, domain_facts, rules

    def _build_bundle_via_agent(
        self,
        *,
        question: str,
        active_step: str | None,
        grounding_ids: list[str],
        user_traits: list[dict[str, Any]],
        history: list[dict[str, str]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]] | None:
        """Arma el bundle con el ``RouterAgent`` (fase 2.2, LLM real + tools).

        Devuelve ``None`` si no hay ``router_agent`` inyectado o si
        ``RouterAgent.route`` lanza -- el llamador (``_resolve_bundle``) cae
        entonces al fallback deterministico (``_build_bundle``), mismo patron
        fail-open que ``Orchestrator._policy_gate``/``GateAgent``: un agente
        caido (LLM sin cuota, red caida, salida no parseable) no puede dejar
        el turno sin contexto.

        Piso de seguridad: se aplica SIEMPRE despues de la respuesta del
        agente, via ``apply_security_floor`` -- no importa que el modelo haya
        decidido, las ``RuleAtom`` de ``conversation:security`` quedan.

        Validacion: cualquier ``doc_id`` que el agente devuelva y que NO
        resuelva contra ``self.knowledge`` (alucinado, o de una KB vieja) se
        descarta silenciosamente -- nunca se propaga un id inventado al
        Conversador/Orquestador.

        Tope (``max_bundle_size``): igual criterio que ``_build_bundle`` --
        el piso de seguridad es OBLIGATORIO (nunca lo tapa el tope); el resto
        de la capacidad la llena, en el orden que devolvio el agente, lo que
        entra.
        """
        if self.router_agent is None:
            return None
        try:
            raw_bundle = self.router_agent.route(
                question=question,
                active_step=active_step,
                grounding_atoms=grounding_ids,
                user_traits=user_traits,
                history=history,
            )
        except Exception:
            # Fail-open igual que el gate, pero AUDIBLE: sin este log el
            # fallback es invisible y no hay como saber por que el ruteador
            # no decidio (paso en el deploy a Modal: source=deterministic
            # en produccion, agent en local, y los logs no decian nada).
            logger.exception("RouterAgent fallo; bundle por la via deterministica")
            return None

        security_ids = self._security_floor_ids()
        merged = apply_security_floor(raw_bundle, security_ids)
        # Grounding del step activo: obligatorio tambien por la via agente
        # (misma guardia de codigo que el piso de seguridad).
        if active_step:
            short_step = active_step.split(":", 1)[-1] if ":" in active_step else active_step
            present = {str(e.get("doc_id") or "") for e in merged}
            for doc_id in grounding_ids:
                if doc_id not in present:
                    merged.append({"doc_id": doc_id, "motivo": f"grounding de {short_step}", "family": None, "score": None})
                    present.add(doc_id)

        resolved: list[dict[str, Any]] = []
        for entry in merged:
            doc_id = str(entry.get("doc_id") or "")
            doc = self.knowledge.doc(doc_id) if doc_id else None
            if doc is None:
                continue  # id alucinado / inexistente: no entra al bundle
            tipo, family = self._tipo_y_family_de_doc(doc)
            resolved.append({
                "doc_id": doc_id,
                "family": family or entry.get("family"),
                "motivo": str(entry.get("motivo") or ""),
                "score": entry.get("score"),
                "_tipo": tipo,
                "_doc": doc,
            })

        if len(resolved) > self.max_bundle_size:
            mandatory_ids = set(security_ids) | set(grounding_ids)
            mandatory = [e for e in resolved if e["doc_id"] in mandatory_ids]
            optional = [e for e in resolved if e["doc_id"] not in mandatory_ids]
            remaining = max(self.max_bundle_size - len(mandatory), 0)
            resolved = mandatory + optional[:remaining]

        bundle: list[dict[str, Any]] = []
        domain_facts: list[dict[str, str]] = []
        rules: list[dict[str, str]] = []
        for entry in resolved:
            doc_id = entry["doc_id"]
            doc = entry.pop("_doc")
            tipo = entry.pop("_tipo")
            bundle.append(entry)
            if tipo in ("domain", "rule"):
                projected = {
                    "id": doc.get("id", doc_id),
                    "body": doc.get("answer", ""),
                    "tags": doc.get("tags", []),
                    "title": doc.get("title") or doc.get("id", doc_id),
                    "family": entry["family"],
                }
                (domain_facts if tipo == "domain" else rules).append(projected)

        return bundle, domain_facts, rules

    def _resolve_bundle(
        self,
        *,
        question: str,
        active_step: str | None,
        grounding_ids: list[str],
        user_traits: list[dict[str, Any]],
        history: list[dict[str, str]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]], str]:
        """Punto unico de entrada del bundle del turno: agente primero, fallback despues.

        Devuelve ``(bundle, domain_facts, rules, source)`` con ``source`` en
        ``"agent"`` (lo armo el ``RouterAgent`` real) o ``"deterministic"``
        (fallback via ``_build_bundle`` -- sin ``router_agent`` inyectado, o
        el agente fallo). ``source`` viaja hasta ``decisions.ruteador.source``
        en el rastro del turno (``Orchestrator.handle_turn``): auditable si
        el contexto de este turno lo decidio un LLM o la union deterministica.
        """
        via_agent = self._build_bundle_via_agent(
            question=question,
            active_step=active_step,
            grounding_ids=grounding_ids,
            user_traits=user_traits,
            history=history,
        )
        if via_agent is not None:
            bundle, domain_facts, rules = via_agent
            return bundle, domain_facts, rules, "agent"

        bundle, domain_facts, rules = self._build_bundle(
            question=question,
            active_step=active_step,
            grounding_ids=grounding_ids,
            user_traits=user_traits,
        )
        return bundle, domain_facts, rules, "deterministic"

    # ── configuracion del agente desde modelos tipados (deshardcodeo) ──

    def _extract_persona(self) -> dict[str, str]:
        """Arma la persona desde los modelos tipados self/style/boundary.

        - whoami : SelfDeclaration.statement
        - estilo : StyleGuide (tone + register + phrases + length)
        - limites: CapabilityBoundary (restriction + conditions + escalation)
        """
        persona: dict[str, str] = {}

        selfs = self._find_by_model("self")
        if selfs:
            persona["whoami"] = selfs[0].get("statement", "")

        styles = self._find_by_model("style")
        if styles:
            s = styles[0]
            persona["estilo"] = "\n".join(
                part for part in (
                    s.get("tone", ""),
                    s.get("language_register", ""),
                    s.get("phrase_preferences", ""),
                    s.get("length_guidelines", ""),
                ) if part
            )

        boundaries = self._find_by_model("boundary")
        if boundaries:
            b = boundaries[0]
            persona["limites"] = "\n".join(
                part for part in (
                    b.get("restriction", ""),
                    b.get("conditions", ""),
                    b.get("escalation", ""),
                ) if part
            )

        return persona

    def _extract_strategy(self) -> str:
        """Estrategia de atención desde StrategyRule (goal/approach/priorities)."""
        strategies = self._find_by_model("strategy")
        if not strategies:
            return ""
        s = strategies[0]
        return "\n".join(
            part for part in (
                s.get("goal", ""),
                s.get("approach", ""),
                s.get("priorities", ""),
            ) if part
        )

    def _extract_fallback(self) -> str:
        """Mensaje de fallback desde FallbackRule.fallback_message."""
        fallbacks = self._find_by_model("fallback")
        if not fallbacks:
            return ""
        return fallbacks[0].get("fallback_message", "")

    def _find_tools(self) -> list[dict[str, Any]]:
        """Selecciona los ToolAtom y devuelve su schema JSON (campo parameters)."""
        tools = []
        for d in self._find_by_model("tool"):
            schema = d.get("parameters")
            if isinstance(schema, str):
                schema = self._parse_tool_schema(schema)
            if isinstance(schema, dict) and schema:
                tools.append(schema)
        return sorted(tools, key=lambda t: t.get("name", ""))

    @staticmethod
    def _parse_tool_schema(text: str) -> dict[str, Any] | None:
        """Extrae el schema JSON de la respuesta de un tool atom."""
        import re, json
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    # ── enriquecimiento KGDB ────────────────────────────────────

    #: placeholders del texto libre "Allowed Transitions" que significan
    #: "sin salida" (step terminal), ver p.ej. step-antonia-despedida.
    _NO_TRANSITION_PLACEHOLDERS = {"ninguno", "ninguna", "ninguna (paso terminal)"}

    @classmethod
    def _split_declared_transitions(cls, text: str) -> list[str]:
        """Parsea el campo libre ``ConversationStep.allowed_transitions``.

        Mismo criterio que ``frontends/flow_editor/export_flow.py`` (unica
        otra lectora de este campo hoy): coma o salto de linea como
        separador, placeholders de "sin transicion" descartados.
        """
        if not text:
            return []
        parts = [p.strip() for p in text.replace("\n", ",").split(",")]
        return [p for p in parts if p and p.lower() not in cls._NO_TRANSITION_PLACEHOLDERS]

    def _find_step_by_tag(self, tag: str) -> dict[str, Any] | None:
        for step in self._find_by_model("step"):
            if tag in (step.get("tags") or []):
                return step
        return None

    _STEP_CONTEXT_FIELDS = ("id", "title", "kind", "instructions", "required_slots", "completion_condition")

    def step_context(self, tag: str | None) -> dict[str, Any] | None:
        """Proyeccion del ``ConversationStep`` de ``tag`` para el prompt del Conversador.

        Deterministico (lectura SLDB, sin LLM): sirve tanto para el step
        activo al compilar como para RE-APUNTAR el borrador al step destino
        cuando el Orquestador decide una transicion en el mismo turno (ver
        ``Orchestrator.handle_turn``): sin esto el Conversador redactaba con
        las instrucciones del step viejo y la respuesta iba un turno atrasada
        respecto del estado (pedia otra vez lo que el step anterior pedia).
        """
        if not tag:
            return None
        doc = self._find_step_by_tag(tag)
        if not doc:
            return None
        out: dict[str, Any] = {"tag": tag}
        for key in self._STEP_CONTEXT_FIELDS:
            out[key] = str(doc.get(key) or "").strip()
        return out

    def retarget_step(self, compiled: dict[str, Any], target: str) -> bool:
        """Re-apunta un contexto compilado (dict) al step ``target`` sin LLM.

        Lo usa ``Orchestrator.handle_turn`` cuando el Orquestador decide una
        transicion: el Conversador redacta con el step destino (``step``) y
        con su grounding sumado a ``bundle``/``domain_facts``/``rules``/
        ``grounding_atoms`` (asi el gate juzga contra el mismo contexto que
        vio el Conversador). ``flow_node`` no se toca: la navegacion la
        persiste el orquestador al cerrar el turno. Devuelve False si el
        step no existe en la KB (no se modifica nada).
        """
        step = self.step_context(target)
        if step is None:
            return False
        compiled["step"] = step
        short_step = target.split(":", 1)[-1] if ":" in target else target
        bundle = compiled.setdefault("bundle", [])
        facts = compiled.setdefault("domain_facts", [])
        rules = compiled.setdefault("rules", [])
        present = {str(e.get("doc_id") or "") for e in bundle}
        present_facts = {str(f.get("id") or "") for f in facts}
        present_rules = {str(r.get("id") or "") for r in rules}
        grounding = list(compiled.get("grounding_atoms") or [])
        for doc_id in self._step_grounding_ids(target):
            if doc_id not in grounding:
                grounding.append(doc_id)
            doc = self.knowledge.doc(doc_id)
            if doc is None:
                continue
            tipo, family = self._tipo_y_family_de_doc(doc)
            if doc_id not in present:
                bundle.append({"doc_id": doc_id, "family": family, "motivo": f"grounding de {short_step}", "score": None})
                present.add(doc_id)
            if tipo in ("domain", "rule"):
                projected = {
                    "id": doc.get("id", doc_id),
                    "body": doc.get("answer", ""),
                    "tags": doc.get("tags", []),
                    "title": doc.get("title") or doc.get("id", doc_id),
                    "family": family,
                }
                if tipo == "domain" and doc_id not in present_facts:
                    facts.append(projected); present_facts.add(doc_id)
                elif tipo == "rule" and doc_id not in present_rules:
                    rules.append(projected); present_rules.add(doc_id)
        compiled["grounding_atoms"] = grounding
        return True

    def _entry_step(self, steps: list[str]) -> str:
        """Step de entrada del diagrama para una sesion sin step valido.

        Orden de preferencia:
          1. ``.onboarding`` si la KB lo declara (convencion historica, Don Peppe).
          2. La raiz del grafo de ``Allowed Transitions``: el step al que
             ningun otro transiciona. Si hay varias raices, la primera en
             orden alfabetico.
          3. El primer step del diagrama (alfabetico).

        Antes se caia directo a ``steps[0]``: en una KB sin onboarding eso
        era el primero por orden alfabetico, no el inicio del flujo (Vitali
        arrancaba en ``agendar_visita`` en vez de ``saludo`` y el primer
        "hola" caia en el step equivocado).
        """
        onboarding = next((s for s in steps if s.endswith(".onboarding")), None)
        if onboarding:
            return onboarding
        targets: set[str] = set()
        for step in steps:
            doc = self._find_step_by_tag(step)
            if doc:
                targets.update(self._split_declared_transitions(doc.get("allowed_transitions", "")))
        roots = [s for s in steps if s not in targets]
        return roots[0] if roots else steps[0]

    def _resolve_kgdb_active_step(
        self, current_step: str | None = None
    ) -> tuple[str | None, list[str], list[str]]:
        """Resuelve el diagrama de conversacion del KGDB para el step activo.

        El grafo generado desde SLDB es tag-centrico: el diagrama de conversacion
        vive en la jerarquia ``conversation:steps.*``. Esta funcion:
          1. determina el step actual (viene del SessionState via ``current_step``,
             o cae al onboarding si existe, o al primer step disponible),
          2. expone SOLO las transiciones que el step activo declara en su
             propia seccion "Allowed Transitions" (no todos los hermanos),
          3. resuelve los documentos que groundean el step contra SLDB.

        Se resuelve ANTES de armar el bundle (``_build_bundle`` necesita el
        grounding del step activo con motivo "grounding de <step>"), a
        diferencia del ``_augment_from_kgdb`` original que corria al final y
        mutaba el ``CompiledDocument`` directamente.

        Nota: ``KGDBReader.get_next_transitions``/``get_grounding_atoms``
        leen aristas ``flows_to``/``grounded_by`` que el pipeline de ingest
        SLDB->KGDB (``kgdb.ingest.sldb``) nunca produce -- el grafo que arma
        ``KGDBReader.from_sldb`` es puramente tag-centrico (``tagged_as``,
        ``semantic_parent``). Por eso las transiciones se leen del campo
        tipado ``ConversationStep.allowed_transitions`` via ``knowledge``, que es
        la fuente real que ya declara cada step (y que ya usa, por el mismo
        motivo, ``frontends/flow_editor/export_flow.py``).

        Devuelve ``(active_step, allowed_transitions, grounding_atom_ids)``,
        o ``(None, [], [])`` sin KGDB o sin diagrama.
        """
        if self.kgdb is None:
            return None, [], []

        steps = self.kgdb.steps_under("conversation:steps")
        if not steps:
            return None, [], []

        # Step actual: el que trae la sesion, si es valido; si no, el step de
        # entrada del diagrama (ver ``_entry_step``).
        active = current_step if current_step in steps else None
        if active is None:
            active = self._entry_step(steps)

        # Transiciones permitidas: SOLO las declaradas por el step activo,
        # filtradas contra el universo real de steps del diagrama (defensivo
        # ante typos o referencias colgantes en el campo libre).
        step_doc = self._find_step_by_tag(active)
        declared = self._split_declared_transitions(step_doc.get("allowed_transitions", "")) if step_doc else []
        allowed_transitions = [t for t in declared if t in steps]
        grounding_atoms = self._step_grounding_ids(active, step_doc)
        return active, allowed_transitions, grounding_atoms

    def _step_grounding_ids(self, tag: str, step_doc: dict[str, Any] | None = None) -> list[str]:
        """Ids que groundean el step ``tag``: union sin duplicados de

          a) los documentos etiquetados con el tag del step (KGDB, p.ej. el
             propio ConversationStep y los ToolAtom del step), y
          b) los ids que el step DECLARA en su campo libre ``grounding_atoms``
             ("Grounding Atoms", separados por coma), validados contra el
             la KB (un id que no existe se descarta).

        Hasta ahora solo entraba (a): la lista que la KB escribe a mano en
        cada step (reglas de horario, oficinas, modalidad...) no llegaba ni
        al Conversador ni al gate, que rechazaba datos correctos por "no
        declarados en el contexto".
        """
        ids: list[str] = list(self.kgdb.docs_for_tag(tag)) if self.kgdb is not None else []
        if step_doc is None:
            step_doc = self._find_step_by_tag(tag)
        declared = self._split_declared_transitions(str((step_doc or {}).get("grounding_atoms") or ""))
        for doc_id in declared:
            if doc_id not in ids and self.knowledge.doc(doc_id) is not None:
                ids.append(doc_id)
        return ids

    def _load_user_traits(self, user_id: int | None) -> list[dict[str, Any]]:
        """Traits del usuario resueltos contra su TraitAtom (no solo el id).

        Via ``knowledge_ops.traits(external_id)`` cuando el orquestador
        inyecto una instancia de ``KnowledgeOperations`` (produccion: una
        sola instancia por proceso, embedder cacheado). Si no hay
        ``knowledge_ops`` (p.ej. tests unitarios del compilador solo), cae a
        la misma resolucion hecha a mano con lo que el compilador ya tiene
        inyectado (``identity_session`` + ``knowledge``), sin abrir una conexion
        SQL nueva.
        """
        if user_id is None or self.identity_session is None:
            return []

        if self.knowledge_ops is not None:
            user = self.identity_session.get(Users, user_id)
            external_id = getattr(user, "external_id", None)
            if external_id is not None:
                return self.knowledge_ops.traits(external_id)

        statement = (
            select(UserTraits)
            .where(UserTraits.user_id == user_id)
            .order_by(UserTraits.trait_id)
        )
        results: list[dict[str, Any]] = []
        for ut in self.identity_session.scalars(statement):
            trait_doc = self.knowledge.doc(ut.trait_id) or {}
            results.append({
                "trait_id": ut.trait_id,
                "title": trait_doc.get("title", ut.trait_id),
                "description": trait_doc.get("description", ""),
                "category": trait_doc.get("category", ""),
                "confidence": ut.confidence,
                "source": ut.source,
            })
        return results

    def _load_history(
        self,
        user_id: int | None,
        limit: int | None = None,
        *,
        conversation_id: int | None = None,
    ) -> list[dict[str, str]]:
        """Ultimos ``limit`` mensajes de ``chat_history``, cronologicos.

        Usa la MISMA ``identity_session`` que el orquestador ya tiene abierta
        (nunca abre una conexion nueva). El orquestador llama al compilador
        ANTES de persistir el turno en curso (ver ``orchestrator.handle_turn``:
        el compile_context corre dentro de ``router.handle_user_message``,
        ``_persist_chat_history`` recien despues), asi que el mensaje actual
        (ya viene como ``question``) nunca aparece duplicado aca.

        Si se pasa ``conversation_id``, el historial se acota a ESA
        conversacion -- no cruza el limite de una conversacion cerrada. Sin el
        (crons, tests viejos, filas pre-migracion sin FK) cae al filtro por
        ``user_id`` como antes.
        """
        if user_id is None or self.identity_session is None:
            return []

        n = self.history_limit if limit is None else limit
        if n <= 0:
            return []

        statement = select(ChatHistory)
        if conversation_id is not None:
            statement = statement.where(ChatHistory.conversation_id == conversation_id)
        else:
            statement = statement.where(ChatHistory.user_id == user_id)
        statement = statement.order_by(ChatHistory.id.desc()).limit(n)
        rows = list(self.identity_session.scalars(statement))
        rows.reverse()  # orden cronologico (mas viejo primero)
        return [{"role": row.role, "content": row.content} for row in rows]


def compile_context(
    question: str,
    user_id: int | None,
    *,
    knowledge: "KnowledgeOperations",
    scenario: str | None = None,
    trigger: str = "user",
    session_state: SessionStateLike | None = None,
    identity_session: Session | None = None,
    session_state_loader: Callable[[int], SessionStateLike | None] | None = None,
    kgdb: KGDBReader | None = None,
    knowledge_ops: "KnowledgeOperations | None" = None,
    router_agent: "RouterAgent | None" = None,
) -> CompiledDocument:
    """Atajo funcional sobre ``ContextCompiler`` (``knowledge`` es obligatorio)."""
    compiler = ContextCompiler(
        knowledge=knowledge,
        identity_session=identity_session,
        session_state_loader=session_state_loader,
        kgdb=kgdb,
        knowledge_ops=knowledge_ops,
        router_agent=router_agent,
    )
    return compiler.compile(
        question=question,
        user_id=user_id,
        scenario=scenario,
        trigger=trigger,
        session_state=session_state,
    )