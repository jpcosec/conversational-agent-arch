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
    #: TAMBIEN es la fuente del embedder para la similitud que arma el bundle
    #: del turno (ver ``_build_bundle``/``_semantic_candidates``); sin ella no
    #: hay ranking semantico y el bundle cae al modo legado (todo domain/rule,
    #: sin tope).
    knowledge_ops: "KnowledgeOperations | None" = None
    #: Tope del bundle justificado (ver ``_build_bundle``). Solo se aplica
    #: cuando hay ``knowledge_ops`` (hay ranking real con el que decidir que
    #: cae fuera); sin el, no hay tope (modo legado).
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
        history = self._load_history(user_id)

        persona = self._extract_persona()
        strategy = self._extract_strategy()
        fallback_text = self._extract_fallback()

        # Doctrina 1.3: el contexto ya no es "todo domain/rule" (score 1.0
        # hardcodeado); es un bundle JUSTIFICADO (ver ``_build_bundle``).
        # ``domain_facts``/``rules`` son la proyeccion tipada de ese bundle,
        # asi ``decide_turn``/``build_nl_prompt`` no cambian de forma.
        bundle, domain_facts, rules = self._build_bundle(
            question=question,
            active_step=active_step,
            grounding_ids=grounding_ids,
            user_traits=user_traits,
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

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    def _semantic_candidates(self, question: str, max_results: int) -> list[dict[str, Any]]:
        """Top-k por similitud coseno contra la pregunta, cualquier familia.

        Reimplementa el contrato de ``KnowledgeOperations.explore_multi``
        (misma formula de coseno, mismo piso de ruido) en vez de LLAMARLO:
        ``explore_multi`` -> ``_semantic_search`` llama ``self._read_doc(id)``
        por cada doc del loop, y ``_read_doc`` vuelve a escanear TODA la KB
        (``_find_records()``) en cada llamada -- O(n^2). Medido: ~4 min en la
        KB real (71 docs), 15-60s incluso en KBs de prueba de ~15 docs. Eso
        volveria cada turno de produccion (y toda la suite de tests) varios
        minutos mas lento. ``knowledge_base/operations.py`` esta PROHIBIDO
        para este cambio, asi que se reimplementa aca con lo que YA es rapido:
        ``self._records()`` (cacheado UNA vez en memoria por ``SLDBReader``,
        la misma cache que ya usan ``_find_atoms``/``_find_by_model``) y el
        embedder cacheado de ``knowledge_ops`` (misma instancia por proceso,
        sin recargar el modelo). No replica el merge con busqueda fuzzy de
        ``explore_multi`` (simplificacion deliberada: el top-k semantico solo
        ya cumple el criterio de exito 1.3).
        """
        if self.knowledge_ops is None or not question:
            return []
        try:
            embedder = self.knowledge_ops._embedder()
            query_vec = [float(v) for v in list(embedder.embed([question]))[0]]
        except Exception:
            return []

        scored: list[tuple[float, str]] = []
        for doc in self._records():
            emb = doc.get("embedding")
            if not emb or not isinstance(emb, list) or len(emb) < 2:
                continue
            score = self._cosine_sim(query_vec, [float(v) for v in emb])
            if score < self._SEMANTIC_NOISE_FLOOR:
                continue
            scored.append((score, doc.get("id", "")))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [{"id": doc_id, "score": round(score, 4)} for score, doc_id in scored[:max_results]]

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
        security_ids = {
            d.get("id", "")
            for d in self._find_by_model("rule")
            if self._SECURITY_FLOOR_TAG in (d.get("tags") or [])
        }
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
            doc = self.reader.get_doc(doc_id)
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
        tipado ``ConversationStep.allowed_transitions`` via el reader, que es
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

        # Step actual: el que trae la sesion, si es valido; si no, onboarding; si
        # no existe onboarding, el primer step del diagrama.
        active = current_step if current_step in steps else None
        if active is None:
            onboarding = next((s for s in steps if s.endswith(".onboarding")), None)
            active = onboarding or steps[0]

        # Transiciones permitidas: SOLO las declaradas por el step activo,
        # filtradas contra el universo real de steps del diagrama (defensivo
        # ante typos o referencias colgantes en el campo libre).
        step_doc = self._find_step_by_tag(active)
        declared = self._split_declared_transitions(step_doc.get("allowed_transitions", "")) if step_doc else []
        allowed_transitions = [t for t in declared if t in steps]
        # Grounding: documentos etiquetados con el step actual (resueltos en SLDB).
        grounding_atoms = self.kgdb.docs_for_tag(active)
        return active, allowed_transitions, grounding_atoms

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

    def _load_history(self, user_id: int | None, limit: int | None = None) -> list[dict[str, str]]:
        """Ultimos ``limit`` mensajes de ``chat_history`` del usuario, cronologicos.

        Usa la MISMA ``identity_session`` que el orquestador ya tiene abierta
        (nunca abre una conexion nueva). El orquestador llama al compilador
        ANTES de persistir el turno en curso (ver ``orchestrator.handle_turn``:
        el compile_context corre dentro de ``router.handle_user_message``,
        ``_persist_chat_history`` recien despues), asi que el mensaje actual
        (ya viene como ``question``) nunca aparece duplicado aca.
        """
        if user_id is None or self.identity_session is None:
            return []

        n = self.history_limit if limit is None else limit
        if n <= 0:
            return []

        statement = (
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.desc())
            .limit(n)
        )
        rows = list(self.identity_session.scalars(statement))
        rows.reverse()  # orden cronologico (mas viejo primero)
        return [{"role": row.role, "content": row.content} for row in rows]


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