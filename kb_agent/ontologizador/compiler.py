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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from kb_agent.models.knowledge import DomainAtom, RuleAtom
from kb_agent.models_sql.identity import UserTraits, Users

from .compiled_document import CompiledDocument
from .kgdb_reader import KGDBReader
from .sldb_reader import SLDBReader

if TYPE_CHECKING:
    from knowledge_base.operations import KnowledgeOperations


class SessionStateLike(Protocol):
    active_domain: str | None


@dataclass(slots=True)
class ContextCompiler:
    reader: SLDBReader
    kgdb: KGDBReader | None = None
    identity_session: Session | None = None
    session_state_loader: Callable[[int], SessionStateLike | None] | None = None
    #: Capa knowledge_base (SLDB+KGDB+SQL) para resolver traits contra su
    #: TraitAtom. El orquestador crea UNA instancia (embedder cacheado por
    #: instancia) y la reutiliza en todos los turnos; si no se inyecta (tests
    #: unitarios del compilador), se resuelve localmente via ``reader``.
    knowledge_ops: "KnowledgeOperations | None" = None

    def compile(
        self,
        *,
        question: str,
        user_id: int | None,
        scenario: str | None = None,
        trigger: str = "user",
        session_state: SessionStateLike | None = None,
    ) -> CompiledDocument:
        resolved_scenario = self._resolve_scenario(
            user_id=user_id,
            scenario=scenario,
            trigger=trigger,
            session_state=session_state,
        )

        # Doctrina tipada: se selecciona por MODELO (type.knowledge.*). Cada tipo
        # aporta sus campos propios. El conversador arma su prompt desde persona /
        # strategy / fallback_text sin hardcodear nada del negocio.
        domain_facts = self._find_atoms("domain")
        rules = self._find_atoms("rule")
        tools = self._find_tools()
        user_traits = self._load_user_traits(user_id)

        persona = self._extract_persona()
        strategy = self._extract_strategy()
        fallback_text = self._extract_fallback()

        doc = CompiledDocument(
            scenario=resolved_scenario,
            question=question,
            user_traits=user_traits,
            domain_facts=domain_facts,
            rules=rules,
            tools=tools,
            persona=persona,
            strategy=strategy,
            fallback_text=fallback_text,
            is_empty=not domain_facts and not rules,
        )

        # Enriquecer con el diagrama de conversacion (KGDB), si hay grafo.
        # current_step viene del estado de sesion persistido en SQL (flow_node).
        if self.kgdb is not None:
            current_step = getattr(session_state, "flow_node", None)
            self._augment_from_kgdb(doc, resolved_scenario, current_step=current_step)

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
            for m in self.reader.find(f"type.knowledge.{tipo}"):
                seen[m["id"]] = m
        return list(seen.values())

    def _find_by_model(self, tipo: str) -> list[dict[str, Any]]:
        """Selecciona los atoms de un tipo tipado via ``type.knowledge.<tipo>``.

        Devuelve el doc completo (todos los campos del modelo) resuelto contra
        el store, ordenado por id para estabilidad.
        """
        matched = self.reader.find(f"type.knowledge.{tipo}")
        docs = []
        for m in matched:
            doc = self.reader.get_doc(m["id"]) or m
            docs.append(doc)
        return sorted(docs, key=lambda d: d.get("id", ""))

    #: modelo tipado por cada tipo que pasa por ``_find_atoms`` (domain/rule).
    #: Se usa solo para exponer ``family()`` (declarada en la clase, ClassVar
    #: ``__family__``) sin derivarla del prefijo del tag en el consumidor.
    _ATOM_MODEL_BY_TIPO: ClassVar[dict[str, type]] = {
        "domain": DomainAtom,
        "rule": RuleAtom,
    }

    def _find_atoms(self, tipo: str) -> list[dict[str, Any]]:
        """Grounding del negocio: domain/rule con su ``answer`` como body.

        Conserva tags y title para que el orquestador arme el contexto del turno
        sin re-leer el store (brecha #2). Tambien propaga ``family``, tomada de
        la CLASE del modelo tipado (``.family()``), no del prefijo del tag: un
        RuleAtom es familia "domain" aunque lleve tags "conversation:*".
        """
        model_cls = self._ATOM_MODEL_BY_TIPO.get(tipo)
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

    def _augment_from_kgdb(
        self,
        doc: CompiledDocument,
        scenario: str,
        current_step: str | None = None,
    ) -> None:
        """Enriquece el CompiledDocument con el diagrama de conversacion del KGDB.

        El grafo generado desde SLDB es tag-centrico: el diagrama de conversacion
        vive en la jerarquia ``conversation:steps.*``. Este metodo:
          1. determina el step actual (viene del SessionState via ``current_step``,
             o cae al onboarding si existe, o al primer step disponible),
          2. expone SOLO las transiciones que el step activo declara en su
             propia seccion "Allowed Transitions" (no todos los hermanos),
          3. resuelve los documentos que groundean el step contra SLDB.

        Nota: ``KGDBReader.get_next_transitions``/``get_grounding_atoms``
        leen aristas ``flows_to``/``grounded_by`` que el pipeline de ingest
        SLDB->KGDB (``kgdb.ingest.sldb``) nunca produce -- el grafo que arma
        ``KGDBReader.from_sldb`` es puramente tag-centrico (``tagged_as``,
        ``semantic_parent``). Por eso las transiciones se leen del campo
        tipado ``ConversationStep.allowed_transitions`` via el reader, que es
        la fuente real que ya declara cada step (y que ya usa, por el mismo
        motivo, ``frontends/flow_editor/export_flow.py``).
        """
        if self.kgdb is None:
            return

        steps = self.kgdb.steps_under("conversation:steps")
        if not steps:
            return

        # Step actual: el que trae la sesion, si es valido; si no, onboarding; si
        # no existe onboarding, el primer step del diagrama.
        active = current_step if current_step in steps else None
        if active is None:
            onboarding = next((s for s in steps if s.endswith(".onboarding")), None)
            active = onboarding or steps[0]

        doc.flow_node = active
        # Transiciones permitidas: SOLO las declaradas por el step activo,
        # filtradas contra el universo real de steps del diagrama (defensivo
        # ante typos o referencias colgantes en el campo libre).
        step_doc = self._find_step_by_tag(active)
        declared = self._split_declared_transitions(step_doc.get("allowed_transitions", "")) if step_doc else []
        doc.allowed_transitions = [t for t in declared if t in steps]
        # Grounding: documentos etiquetados con el step actual (resueltos en SLDB).
        doc.grounding_atoms = self.kgdb.docs_for_tag(active)

    def _load_user_traits(self, user_id: int | None) -> list[dict[str, Any]]:
        """Traits del usuario resueltos contra su TraitAtom (no solo el id).

        Via ``knowledge_ops.traits(external_id)`` cuando el orquestador
        inyecto una instancia de ``KnowledgeOperations`` (produccion: una
        sola instancia por proceso, embedder cacheado). Si no hay
        ``knowledge_ops`` (p.ej. tests unitarios del compilador solo), cae a
        la misma resolucion hecha a mano con lo que el compilador ya tiene
        inyectado (``identity_session`` + ``reader``), sin abrir una conexion
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
            trait_doc = self.reader.get_doc(ut.trait_id) or {}
            results.append({
                "trait_id": ut.trait_id,
                "title": trait_doc.get("title", ut.trait_id),
                "description": trait_doc.get("description", ""),
                "category": trait_doc.get("category", ""),
                "confidence": ut.confidence,
                "source": ut.source,
            })
        return results


def compile_context(
    question: str,
    user_id: int | None,
    *,
    reader: SLDBReader,
    scenario: str | None = None,
    trigger: str = "user",
    session_state: SessionStateLike | None = None,
    identity_session: Session | None = None,
    session_state_loader: Callable[[int], SessionStateLike | None] | None = None,
    kgdb: KGDBReader | None = None,
    knowledge_ops: "KnowledgeOperations | None" = None,
) -> CompiledDocument:
    """Atajo funcional sobre ``ContextCompiler`` (el reader es obligatorio)."""
    compiler = ContextCompiler(
        reader=reader,
        identity_session=identity_session,
        session_state_loader=session_state_loader,
        kgdb=kgdb,
        knowledge_ops=knowledge_ops,
    )
    return compiler.compile(
        question=question,
        user_id=user_id,
        scenario=scenario,
        trigger=trigger,
        session_state=session_state,
    )