"""``RouterAgent``: el ruteador de contexto como agente LLM con tools de KB.

Fase 2.2, el cuarto y ultimo agente del diseno (Conversador, Ruteador,
Orquestador, Gate). Antes de esto, el bundle justificado del turno lo
armaba enteramente ``ContextCompiler._build_bundle``
(``kb_agent/ontologizador/compiler.py``): una union DETERMINISTICA de 4
vias (piso de seguridad, grounding del step activo, traits del usuario,
similitud top-k contra la pregunta). Funciona bien y sigue siendo el
fallback (ver mas abajo) -- pero es una politica fija, no un agente: no
puede, por ejemplo, decidir que un ``TraitAtom`` de ansiedad conviene
meterlo aunque no gane el top-k de similitud, ni leer un documento
completo (``show``) antes de decidir si aporta, ni navegar el grafo
(``explore``) para encontrar algo que la pregunta no menciona literalmente.

Diseno (mismo patron que ``GateAgent``/``OrchestratorAgent``, fase 2.3/2.4):
un LLM con salida tipada (``RouterDecision``) y ``tools`` reales -- el
modelo puede LLAMAR a ``explore_multi``/``explore``/``show`` sobre la KB
antes de responder, en vez de recibir todo pre-resuelto. El
``static_instruction`` es el prompt de COMO buscar: que familias existen,
que significa cada motivo, y la regla de oro del ruteador (pedido explicito
del usuario, citado en el plan): "el ruteador puede meter cualquier
documento dentro del bundle de contexto, no solo domain, si lo mete debe
estar justificado".

Piso de seguridad NO NEGOCIABLE (farmacovigilancia): las ``RuleAtom`` con
tag ``conversation:security`` DEBEN entrar al bundle SIEMPRE, decida lo que
decida el modelo. Igual que la guardia de transiciones de
``orchestrator_agent.apply_transition_guard``, esto NO se implementa como
instruccion de prompt (un LLM puede olvidarla) sino como CODIGO alrededor
del agente: ``apply_security_floor`` fuerza la presencia de esos ids
despues de que el modelo respondio, sin importar si los pidio o no. La
resuelve el LLAMADOR (``ContextCompiler``, que sabe cuales son esos ids
via el reader) -- este modulo solo expone la funcion pura que los inyecta.

Fallback deterministico: ``ContextCompiler._build_bundle`` (SIN tocar, ver
su docstring) sigue siendo el camino cuando no hay ``RouterAgent`` inyectado
(tests offline, ver ``tests.support.fakes.FakeRouterAgent``) o cuando el
agente falla -- mismo patron fail-open que ``Orchestrator._policy_gate``.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from kb_agent.agents.base import Agent, AgentRole, Tool

if TYPE_CHECKING:
    from knowledge_base.operations import KnowledgeOperations

__all__ = [
    "RouterAgent",
    "RouterDecision",
    "BundleEntry",
    "apply_security_floor",
    "render_router_instruction",
]


class BundleEntry(BaseModel):
    """Un documento elegido por el ruteador, con su justificacion.

    ``motivo`` es el contrato de auditoria (pedido explicito del usuario):
    es lo que hace el contexto explicable sin tener que abrir la KB. Nunca
    es opcional -- un documento sin motivo no entra.
    """

    doc_id: str
    motivo: str
    family: str | None = None
    score: float | None = None


class RouterDecision(BaseModel):
    """Salida tipada del ruteador. Contrato que ``ContextCompiler`` consume."""

    bundle: list[BundleEntry] = Field(default_factory=list)


_ROUTER_INSTRUCTION = """\
Eres el RUTEADOR DE CONTEXTO de un agente conversacional. Tu trabajo es \
decidir QUE documentos de la base de conocimiento (KB) entran al "bundle" \
de contexto de este turno -- el conjunto que van a ver el Orquestador y el \
Conversador para decidir que hacer y redactar la respuesta. NO redactas \
nada vos mismo: solo eliges documentos y los justificas.

REGLA DE ORO (no negociable): todo documento que agregues DEBE llevar un \
motivo concreto que lo justifique. Nunca agregues un documento "porque si" \
o "por si acaso". Si no podes explicar en una frase por que ese documento \
ayuda a responder ESTE turno, no lo incluyas.

Familias de documentos que existen en la KB (el eje `family`, no confundir \
con el tipo tipado del atom):
  - self         identidad, estilo y limites del asistente (SelfDeclaration, \
StyleGuide, CapabilityBoundary, ToolAtom). Rara vez hace falta meterlos al \
bundle -- ya los tiene el Conversador aparte -- salvo que el usuario \
pregunte directamente sobre el asistente o sus capacidades.
  - domain       conocimiento del negocio: DomainAtom (hechos) y RuleAtom \
(reglas). Es la familia mas comun del bundle.
  - conversation flujo de la conversacion: ConversationStep, StrategyRule, \
FallbackRule. Util cuando el turno depende de en que paso del flujo estamos \
o de hacia donde puede navegar.
  - user         TraitAtom: rasgos de personalidad o situacion de ESTE \
usuario (ansiedad, primera vez, preferencias, etc.). Si el usuario expresa \
algo que coincide con un trait -- lo diga en la pregunta o ya conste en sus \
"traits_usuario" -- casi siempre conviene incluirlo: da contexto emocional \
o practico para la respuesta.
  - gate         GateCriterion: criterios de aprobacion de respuestas. Son \
para el Gate, no para redactar -- normalmente NO van en el bundle salvo que \
el propio usuario pregunte por politicas o limites de aprobacion.

Motivos: usa estas frases tal cual cuando apliquen (son el contrato de \
auditoria, el resto del sistema las reconoce por texto):
  - "grounding de <step_actual>" -- el documento groundea el step activo de \
la conversacion (esta en "grounding_atoms_del_step" del contexto dinamico). \
Sustituye <step_actual> por el NOMBRE DEL STEP tal cual viene en \
"step_actual", NO por el id del documento. Ejemplo: si step_actual es \
"conversation:steps.onboarding", el motivo correcto es "grounding de \
steps.onboarding" -- nunca "grounding de steps.atom-antonia-bienvenida".
  - "trait del usuario" -- un TraitAtom que aplica al usuario de este turno.
  - "similitud <score>" -- relevante por similitud semantica con la \
pregunta (usa el score real que te devuelve `explore_multi`, con 2 \
decimales).
  - Cualquier otro motivo TUYO, explicito y concreto: si el usuario expresa \
algo (una emocion, una situacion, una preferencia) que un documento cubre, \
metelo aunque no sea el de mayor score literal, con un motivo que explique \
que aporta al turno. Podes meter CUALQUIER documento de CUALQUIER familia \
si esta justificado -- no estas limitado a domain/rule.

NO hace falta que busques ni repitas el "piso de seguridad": las reglas \
marcadas con el tag conversation:security las agrega el CODIGO despues de \
tu respuesta, siempre, decidas lo que decidas. Concentrate en lo que \
depende del contexto de este turno.

Herramientas disponibles -- USALAS, no inventes ids ni contenido:
  - explore_multi(query, max_results): similitud semantica + fuzzy contra \
TODA la KB, con score. Es tu primera herramienta: arranca buscando la \
pregunta del usuario tal cual, y si hace falta, conceptos sueltos que \
mencione (sintomas, emociones, nombres de pasos).
  - explore(tag= | atom=): navega el grafo. `tag` para ver hijos y \
documentos de un tag (p.ej. "conversation:steps", "domain:aplicacion"); \
`atom` para ver los tags y vecinos de un documento puntual. Util cuando \
`explore_multi` no alcanza o queres ver que mas hay en una zona de la KB.
  - show(atom_id): lee un documento COMPLETO por su id. Usala antes de \
decidir si un candidato de explore_multi/explore realmente aporta -- el \
titulo y el score solos no siempre alcanzan para juzgar.

Responde en el formato estructurado pedido: `bundle`, la lista de \
documentos elegidos, cada uno con `doc_id` (id EXACTO, verificado con las \
herramientas, nunca inventado), `motivo` (obligatorio) y, si los tenes, \
`family` y `score`. Una lista vacia es una respuesta valida si de verdad \
no hay nada que justifique agregar mas alla de lo que ya carga el sistema."""


def render_router_instruction(*, framing: str | None = None) -> str:
    """``static_instruction`` del ``RouterAgent``: como buscar, no que buscar.

    El cuerpo (``_ROUTER_INSTRUCTION``) es la doctrina fija del sistema
    (familias, motivos, regla de oro) que no cambia por negocio. El
    ``framing`` (opcional) es el encuadre de negocio -- ejemplos concretos
    del dominio (que traits meter ante que sintoma, etc.) -- y viene de un
    ``AgentFraming`` de la KB (rol ``router``). Se antepone como lead-in:
    guia al ruteador sin ensuciar la doctrina con vocabulario de un negocio
    puntual.
    """
    lead_in = (framing or "").strip()
    if lead_in:
        return f"{lead_in}\n\n{_ROUTER_INSTRUCTION}"
    return _ROUTER_INSTRUCTION


def _explore_multi_tool(
    knowledge_ops: "KnowledgeOperations", *, default_max_results: int = 10
) -> Tool:
    def handler(args: Mapping[str, Any]) -> dict[str, Any]:
        query = str(args.get("query") or "").strip()
        if not query:
            return {"query": "", "results": [], "top_score": 0.0, "results_count": 0, "is_empty": True}
        raw_max = args.get("max_results")
        try:
            max_results = int(raw_max) if raw_max is not None else default_max_results
        except (TypeError, ValueError):
            max_results = default_max_results
        return knowledge_ops.explore_multi(query, max_results=max(1, max_results))

    return Tool(
        name="explore_multi",
        description=(
            "Busca documentos por similitud semantica + fuzzy contra TODA la KB "
            "(cualquier familia), devueltos con su score. Primera herramienta para "
            "encontrar candidatos a partir de la pregunta del usuario o de cualquier "
            "concepto suelto que quieras explorar (un sintoma, una emocion, el nombre "
            "de un step)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Texto a buscar (pregunta, concepto, sintoma, etc.)."},
                "max_results": {"type": "integer", "description": f"Tope de resultados (default {default_max_results})."},
            },
            "required": ["query"],
        },
        handler=handler,
    )


def _explore_tool(knowledge_ops: "KnowledgeOperations") -> Tool:
    def handler(args: Mapping[str, Any]) -> dict[str, Any]:
        tag = str(args["tag"]).strip() if args.get("tag") else None
        atom = str(args["atom"]).strip() if args.get("atom") else None
        return knowledge_ops.explore(tag=tag, atom=atom)

    return Tool(
        name="explore",
        description=(
            "Navega el grafo de la KB. Pasa 'tag' para ver el padre, los hijos y los "
            "documentos de un tag (p.ej. 'conversation:steps', 'domain:aplicacion'), o "
            "'atom' para ver los tags y documentos vecinos de un documento puntual. Sin "
            "argumentos, devuelve los tags raiz de la KB."
        ),
        parameters={
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Tag a expandir (padre/hijos/documentos)."},
                "atom": {"type": "string", "description": "Id de un documento a inspeccionar (tags + vecinos)."},
            },
            "required": [],
        },
        handler=handler,
    )


def _show_tool(knowledge_ops: "KnowledgeOperations") -> Tool:
    def handler(args: Mapping[str, Any]) -> dict[str, Any]:
        atom_id = str(args.get("atom_id") or "").strip()
        if not atom_id:
            return {"error": "atom_id vacio"}
        doc = knowledge_ops.show(atom_id)
        return doc if doc is not None else {"error": f"atom '{atom_id}' no encontrado"}

    return Tool(
        name="show",
        description=(
            "Lee un documento COMPLETO por su id (todos sus campos, no solo title/score). "
            "Usala antes de decidir si un candidato de explore_multi/explore realmente "
            "aporta al contexto de este turno."
        ),
        parameters={
            "type": "object",
            "properties": {"atom_id": {"type": "string", "description": "Id exacto del documento."}},
            "required": ["atom_id"],
        },
        handler=handler,
    )


def _build_tools(
    knowledge_ops: "KnowledgeOperations", *, default_max_results: int = 10
) -> list[Tool]:
    """Herramientas de busqueda de KB expuestas al MODELO.

    Se eligieron 3 de las operaciones de ``KnowledgeOperations`` (el modulo
    ofrece mas, pensadas para el CLI de administracion, no para ruteo de
    contexto por turno):
      - ``explore_multi``: la busqueda real (embeddings + fuzzy + score), el
        equivalente agentico del top-k que hoy hace
        ``ContextCompiler._semantic_candidates`` a mano.
      - ``explore``: navegacion del grafo por tag/atom -- encuentra cosas que
        la similitud semantica sola no encuentra (p.ej. "que mas hay bajo
        domain:aplicacion").
      - ``show``: lee un documento completo antes de decidir si aporta (los
        resultados de las otras dos solo traen title/tags/score, no el
        cuerpo).
    Deliberadamente NO se exponen ``traits``/``self_context`` como tools: el
    contexto dinamico del turno (``RouterAgent.route``) ya le pasa los
    traits del usuario resueltos -- pedirle al modelo una llamada extra para
    releer lo que ya tiene es indireccion sin beneficio.

    ``knowledge_ops`` es la instancia UNICA que crea el orquestador por
    proceso (cachea el embedder de jina, ~1 min en frio) -- estas funciones
    la reusan, nunca instancian una nueva.
    """
    return [
        _explore_multi_tool(knowledge_ops, default_max_results=default_max_results),
        _explore_tool(knowledge_ops),
        _show_tool(knowledge_ops),
    ]


def apply_security_floor(bundle: Sequence[Mapping[str, Any]], security_ids: Iterable[str]) -> list[dict[str, Any]]:
    """Fuerza la presencia de las RuleAtom del piso de seguridad en ``bundle``.

    Guardia dura (pedido explicito, farmacovigilancia): no depende de que el
    ``RouterAgent`` se acuerde de incluir las reglas de seguridad -- es
    CODIGO, no una instruccion de prompt. Mismo espiritu que
    ``orchestrator_agent.apply_transition_guard``: una funcion pura, testeada
    sola, que el llamador (``ContextCompiler``) aplica DESPUES de que el
    agente (o su fake) respondio, sin importar que haya decidido.

    Para cada id en ``security_ids``:
      - si ya esta en ``bundle`` (el agente lo incluyo por su cuenta, quiza
        con otro motivo), se le antepone "piso de seguridad" al motivo
        existente sin perderlo.
      - si no esta, se agrega con motivo "piso de seguridad" puro (``family``
        y ``score`` en ``None`` -- el llamador los resuelve contra el
        reader, igual que a cualquier otro id).

    Preserva el orden original del bundle del agente; los ids de seguridad
    faltantes se agregan al final, ordenados por id (estable, no depende del
    orden de iteracion de un ``set``).
    """
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for entry in bundle:
        doc_id = str(entry.get("doc_id") or "").strip()
        if not doc_id:
            continue
        if doc_id not in by_id:
            order.append(doc_id)
        merged = dict(entry)
        merged["doc_id"] = doc_id
        by_id[doc_id] = merged

    for doc_id in sorted({str(s) for s in security_ids if s}):
        if doc_id in by_id:
            motivo = str(by_id[doc_id].get("motivo") or "").strip()
            if "piso de seguridad" not in motivo:
                by_id[doc_id]["motivo"] = "; ".join(p for p in ("piso de seguridad", motivo) if p)
        else:
            by_id[doc_id] = {"doc_id": doc_id, "motivo": "piso de seguridad", "family": None, "score": None}
            order.append(doc_id)

    return [by_id[doc_id] for doc_id in order]


class RouterAgent:
    """Ruteador de contexto: agente LLM con tools de KB sobre ``kb_agent.agents.base.Agent``.

    Se construye UNA vez por proceso (igual que ``GateAgent``/
    ``OrchestratorAgent``) y se reusa en todos los turnos via ``route``.
    ``knowledge_ops`` DEBE ser la instancia unica que crea el orquestador
    (cachea el embedder por instancia, ver ``knowledge_base.operations.
    KnowledgeOperations._embedder``) -- construir una instancia nueva aca
    pagaria de nuevo el costo de carga en frio.
    """

    def __init__(
        self,
        *,
        name: str = "ruteador",
        client: Any,
        model: str,
        knowledge_ops: "KnowledgeOperations",
        framing: str | None = None,
        default_max_results: int = 10,
    ) -> None:
        self.static_instruction = render_router_instruction(framing=framing)
        self._agent = Agent(
            name=name,
            client=client,
            model=model,
            role=AgentRole.ROUTER,
            static_instruction=self.static_instruction,
            tools=_build_tools(knowledge_ops, default_max_results=default_max_results),
            include_contents=True,
            output_schema=RouterDecision,
        )

    def route(
        self,
        *,
        question: str,
        active_step: str | None,
        grounding_atoms: Sequence[str] = (),
        user_traits: Sequence[Mapping[str, Any]] = (),
        history: Sequence[Mapping[str, Any]] = (),
    ) -> list[dict[str, Any]]:
        """Bundle decidido por el agente (SIN el piso de seguridad -- ver
        ``apply_security_floor``, que el llamador aplica sobre el resultado).

        ``history`` viene en la forma de ``CompiledDocument.history``
        (``{role, content}``, ver ``ContextCompiler._load_history``); se
        traduce a la forma que espera ``Agent._build_request``
        (``{role, text}``, ver ``kb_agent.agents.base._content_from_turn``).
        """
        dynamic_context = {
            "pregunta": question,
            "step_actual": active_step,
            "grounding_atoms_del_step": list(grounding_atoms),
            "traits_usuario": [dict(t) for t in user_traits],
        }
        agent_history = [
            {"role": str(turn.get("role") or "user"), "text": str(turn.get("content") or "")}
            for turn in history
        ]
        decision = self._agent.run(dynamic_context, history=agent_history)
        assert isinstance(decision, RouterDecision)
        return [entry.model_dump() for entry in decision.bundle]
