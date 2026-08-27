"""``OrchestratorAgent``: el orquestador de turno como LLM-judge con salida tipada.

Fase 2.4, ultima pieza grande del plan de unificacion de agentes. Antes de
esto, ``decide_turn`` (``kb_agent/agent.py``) era una policy PURA sin LLM:
elegia tool por matching de keywords contra la pregunta
(``_select_relevant_tool``) y clasificaba la intencion de navegacion de flujo
tambien por keywords (``_classify_psp_intent``), fijando ``flow_target`` SIN
consultar ``allowed_transitions`` del step activo. Dos bugs medidos con LLM
real (no teoricos):

  1. El Conversador ve la tool en su contexto y REDACTA como si la hubiera
     llamado ("¡Listo! Te agendé...") aunque ``decide_turn`` haya devuelto
     ``kind: "nl"`` porque las keywords no matchearon -- la tool nunca se
     ejecuta, no hay fila en la tabla real.
  2. ``_classify_psp_intent`` fija un ``flow_target`` por keywords sin mirar
     ``allowed_transitions``: el turno navega a un step que el grafo NO
     declara como transicion valida desde el step actual.

Diseno (mismo patron que ``kb_agent.agents.gate.GateAgent``, fase 2.3): un
LLM con salida tipada (``OrchestratorDecision``) que ve el contexto COMPLETO
del turno (pregunta, step actual, transiciones permitidas, tools declaradas,
grounding), no solo la pregunta pelada. El grafo de steps se renderiza en
``static_instruction`` -- contexto FIJO, cargado una vez al construir el
agente (el grafo no cambia turno a turno, ver ``render_orchestrator_flow``) --
y el contexto propio del turno (incluidas las transiciones permitidas DESDE
el step activo) va en ``dynamic_context`` (ver ``decide``/``_dynamic_context``).

Guardia dura (pedido explicito, item 2 del plan): el modelo puede alucinar un
``step_target`` fuera de ``allowed_transitions`` aunque se lo hayamos pasado
en el contexto -- un LLM no es una garantia. Por eso ``decide`` NUNCA aplica
el ``step_target`` del modelo tal cual: lo pasa por ``apply_transition_guard``,
una funcion de codigo (no de prompt) que descarta cualquier transicion no
declarada por el step activo y deja registro explicito del veto
(``step_target_vetado``) para el rastro del turno. Se eligio una validacion
EXPLICITA en vez de modelar la navegacion como tool con
``before_tool_callback`` (que ``Agent`` si soporta, ver ``kb_agent/agents/base.py``)
porque la navegacion de step NO es una tool real del negocio (no tiene
handler, no groundea nada, no va a ``execute_tool``): es un efecto lateral
que ``Orchestrator.handle_turn`` aplica sobre ``SessionState`` a partir de la
DECISION. Forzarla a ser una ``Tool`` solo para reusar el callback hubiera
sido indireccion sin beneficio; una funcion pura y testeada in isolation
(``apply_transition_guard``) es la guardia mas simple que cumple "en codigo,
no solo en el prompt".

Compatibilidad: ``decide_turn`` NO se toca ni se llama desde este modulo --
sigue siendo la policy pura y testeada de siempre (``tests/unit/test_turn_policy.py``).
Ademas pasa a ser el fallback deterministico "sin LLM" para tests offline:
``tests.support.fakes.FakeOrchestratorAgent`` (analogo a ``FakeGate`` para el
gate) delega en ella para reproducir, sin red, el mismo comportamiento que
tenia el runtime antes de esta fase.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

from kb_agent.agent import build_function_declarations
from kb_agent.agents.base import Agent

__all__ = [
    "OrchestratorAgent",
    "OrchestratorDecision",
    "ToolCallDecision",
    "render_orchestrator_flow",
    "apply_transition_guard",
]


class ToolCallDecision(BaseModel):
    """Tool elegida por el modelo, con sus argumentos ya extraidos."""

    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class OrchestratorDecision(BaseModel):
    """Salida tipada del orquestador. Contrato que ``Orchestrator`` consume.

    ``reason`` es OBLIGATORIO (no ``= ""``): se audita, va al rastro del
    turno (``decisions.orquestador.reason``) -- queremos poder auditar POR
    QUE decidio, no solo QUE decidio.
    """

    kind: Literal["nl", "tool_call", "fallback"]
    step_target: str | None = None
    tool_call: ToolCallDecision | None = None
    reason: str


_NO_STEPS_INSTRUCTION = (
    "Eres el ORQUESTADOR de un agente conversacional. La base de "
    "conocimiento no tiene ningun ConversationStep cargado en este momento: "
    "no hay grafo de flujo que navegar, asi que 'step_target' debe ser "
    "siempre null. Decide solo entre 'tool_call' (si el contexto dinamico "
    "del turno trae una tool declarada que resuelve el pedido y TENES todos "
    "sus argumentos requeridos), 'fallback' (si no hay grounding para "
    "responder) o 'nl' (en cualquier otro caso, el Conversador redacta "
    "despues con lo disponible)."
)


def render_orchestrator_flow(step_atoms: Sequence[Mapping[str, Any]]) -> str:
    """Renderiza el grafo de ``ConversationStep`` para el ``static_instruction``.

    Contexto FIJO del orquestador (pedido explicito del plan): el grafo
    completo de steps del negocio, cargado una vez al construir el agente
    (no cambia turno a turno). Cada bloque aporta ``kind``, ``instructions``
    y sus ``allowed_transitions`` DECLARADAS -- el modelo ve el mapa
    completo, aunque la guardia dura (``apply_transition_guard``) solo
    permite aplicar una transicion si ademas esta en las
    ``allowed_transitions`` que ``Orchestrator`` resolvio para el step
    ACTIVO de ESTE turno (ver ``dynamic_context``/``decide``).
    """
    if not step_atoms:
        return _NO_STEPS_INSTRUCTION

    blocks: list[str] = []
    for step in step_atoms:
        step_id = str(step.get("id") or "")
        title = str(step.get("title") or step_id)
        kind = str(step.get("kind") or "")
        instructions = str(step.get("instructions") or "")
        transitions = str(step.get("allowed_transitions") or "").strip()
        blocks.append(
            f"### {step_id} — {title} (kind={kind})\n"
            f"Instrucciones: {instructions}\n"
            f"Transiciones declaradas desde aca: {transitions or '(ninguna, paso terminal)'}"
        )

    return (
        "Eres el ORQUESTADOR de un agente conversacional. Cada turno "
        "decides el TIPO DE TURNO ('kind') y, si corresponde, QUE TOOL "
        "llamar y A QUE STEP navegar -- NUNCA redactas la respuesta final "
        "(eso lo hace el Conversador despues de tu decision, con el "
        "resultado real de la tool si la llamaste).\n\n"
        "Este es el grafo COMPLETO de steps de la conversacion (contexto "
        "fijo del negocio, no cambia turno a turno):\n\n"
        + "\n\n".join(blocks)
        + "\n\n"
        "Responde en el formato estructurado pedido:\n"
        "- 'kind': 'tool_call' SOLO si el contexto dinamico del turno "
        "(pregunta + tools declaradas + grounding) deja claro que hay que "
        "EJECUTAR una tool y tenes TODOS sus argumentos requeridos (no "
        "inventes valores que el usuario no dio). 'fallback' si no hay "
        "contexto (grounding) para responder. 'nl' en cualquier otro caso.\n"
        "- 'tool_call': obligatorio si kind='tool_call', null en cualquier "
        "otro caso. {name, args} EXACTOS de una tool de la lista "
        "'tools_disponibles' del contexto dinamico -- nunca inventes un "
        "nombre de tool que no este ahi.\n"
        "- 'step_target': el id EXACTO del ConversationStep al que navegar, "
        "tomado EXCLUSIVAMENTE de 'allowed_transitions' del contexto "
        "dinamico del turno (las transiciones permitidas DESDE el step "
        "actual, un subconjunto del grafo de arriba). Si ninguna aplica, "
        "dejalo en null -- NUNCA selecciones una transicion que no este en "
        "esa lista, aunque el grafo completo muestre otros steps.\n"
        "- 'reason': por que decidiste esto. Obligatorio, breve y "
        "concreto -- se audita en el rastro del turno."
    )


def apply_transition_guard(
    step_target: str | None, allowed_transitions: Sequence[str]
) -> tuple[str | None, str | None]:
    """Guardia dura sobre la navegacion de steps: no confia en el prompt.

    Devuelve ``(step_target_efectivo, step_target_vetado)``: si
    ``step_target`` esta vacio, ``(None, None)``; si esta pero NO figura en
    ``allowed_transitions`` (las declaradas por el step ACTIVO de este
    turno), se descarta -- el turno se queda en el step actual -- y se
    devuelve el valor original en la segunda posicion para dejar registro
    EXPLICITO del veto en el rastro (``decisions.orquestador.step_target_vetado``,
    ver ``Orchestrator.handle_turn``); si esta y es valido, ``(step_target, None)``.

    Es la UNICA fuente de verdad de este chequeo: la llaman tanto
    ``OrchestratorAgent.decide`` (LLM real) como el fallback deterministico
    de test (``tests.support.fakes.FakeOrchestratorAgent``) -- un LLM con
    alucinaciones y una policy sin LLM quedan sujetos a la MISMA guardia de
    codigo.
    """
    if not step_target:
        return None, None
    if step_target not in set(allowed_transitions):
        return None, step_target
    return step_target, None


class OrchestratorAgent:
    """Orquestador: decide ``kind``/``tool_call``/``step_target`` con LLM + guardia dura.

    Se construye UNA vez por proceso (el grafo de ``ConversationStep`` es fijo
    por negocio, igual que los ``GateCriterion`` de ``GateAgent``) y se reusa
    en todos los turnos via ``decide``.
    """

    def __init__(
        self,
        *,
        name: str = "orquestador",
        client: Any,
        model: str,
        step_atoms: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        self.static_instruction = render_orchestrator_flow(step_atoms)
        self._agent = Agent(
            name=name,
            client=client,
            model=model,
            static_instruction=self.static_instruction,
            include_contents=False,
            output_schema=OrchestratorDecision,
        )

    def decide(self, compiled_context: Mapping[str, Any]) -> dict[str, Any]:
        """Decision tipada del turno a partir del Contexto Compilado.

        Devuelve un dict compatible con lo que antes producia ``decide_turn``
        (``kind``, ``function_call`` si aplica, ``flow_target`` si aplica),
        mas ``reason`` (siempre) y ``step_target_vetado`` (solo si el modelo
        propuso una transicion no permitida -- ver ``apply_transition_guard``).

        Prefiltro deterministico (ahorra una llamada al modelo, mismo
        espiritu que el pre-filtro de ``GateAgent``): si el contexto no trae
        NINGUN grounding (``is_empty``) y tampoco hay tools declaradas para
        este turno, no hay con que fundamentar ni una respuesta ni una
        accion -- fallback inmediato, sin llamar al LLM.
        """
        function_declarations = build_function_declarations(compiled_context)
        allowed_transitions = [str(t) for t in (compiled_context.get("allowed_transitions") or [])]

        if bool(compiled_context.get("is_empty")) and not function_declarations:
            return {
                "kind": "fallback",
                "reason": (
                    "Contexto vacio (sin grounding) y sin tools declaradas para este "
                    "turno: no hay con que fundamentar una respuesta ni una accion. "
                    "Decision determinista, no se llamo al modelo."
                ),
            }

        dynamic_context = self._dynamic_context(compiled_context, function_declarations, allowed_transitions)
        decision = self._agent.run(dynamic_context)
        assert isinstance(decision, OrchestratorDecision)
        return self._to_turn_decision(decision, allowed_transitions)

    @staticmethod
    def _dynamic_context(
        compiled_context: Mapping[str, Any],
        function_declarations: list[dict[str, Any]],
        allowed_transitions: list[str],
    ) -> dict[str, Any]:
        return {
            "pregunta": compiled_context.get("question", ""),
            "step_actual": compiled_context.get("flow_node"),
            "allowed_transitions": allowed_transitions,
            "tools_disponibles": function_declarations,
            "domain_facts": compiled_context.get("domain_facts", []),
            "rules": compiled_context.get("rules", []),
            "user_traits": compiled_context.get("user_traits", []),
            "bundle": compiled_context.get("bundle", []),
            "is_empty": bool(compiled_context.get("is_empty", False)),
        }

    @staticmethod
    def _to_turn_decision(decision: OrchestratorDecision, allowed_transitions: list[str]) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": decision.kind, "reason": decision.reason}

        step_target, vetoed = apply_transition_guard(decision.step_target, allowed_transitions)
        if step_target:
            result["flow_target"] = step_target
        if vetoed:
            result["step_target_vetado"] = vetoed

        if decision.kind == "tool_call":
            if decision.tool_call is not None:
                result["function_call"] = {"name": decision.tool_call.name, "args": dict(decision.tool_call.args)}
            else:
                # Guardia adicional: el modelo dijo 'tool_call' pero no dio
                # la tool -- no hay accion que ejecutar. Degradar a 'nl' en
                # vez de propagar una function_call vacia (que rompería
                # ``execute_tool``/``RouterStateMachine``).
                result["kind"] = "nl"
                result["reason"] = f"{decision.reason} (kind='tool_call' sin 'tool_call' -- degradado a 'nl')"

        return result
