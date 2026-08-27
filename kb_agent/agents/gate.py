"""``GateAgent``: el policy gate como juez LLM que USA los criterios de la KB.

Fase 2.3. Antes de esto, ``Orchestrator._validate_response`` leia los
``GateCriterion`` (``type.knowledge.gate``) de la KB y los IGNORABA: decidia
con heuristicas de string hardcodeadas sobre el ``atom_id``
(``if "dosis" in atom_id: ...``). Agregar un ``GateCriterion`` nuevo a la KB
no cambiaba nada, salvo que su id contuviera una palabra que el codigo ya
conocia -- la KB era decorativa para este agente.

Diseno (pedido explicito del usuario): un LLM-judge con salida tipada
(``GateVerdict``). Los 5 criterios de la KB se renderizan en
``static_instruction`` -- contexto FIJO, cargado una vez al construir el
agente (los criterios no cambian turno a turno) -- y el LLM evalua la
respuesta redactada contra ELLOS, no contra un ``if`` por atom_id. Agregar un
``GateCriterion`` a la KB ahora cambia el prompt del juez sin tocar codigo:
ver ``render_gate_criteria`` y el test de gobernanza en
``tests/unit/test_gate_agent.py``.

``GateAgent`` se construye sobre ``kb_agent.agents.base.Agent`` (la base
comun de los 4 agentes del sistema, fase 2.1): ``static_instruction`` con los
criterios, ``include_contents=False`` (el gate juzga la respuesta ya
redactada, no necesita el historial de la conversacion) y
``output_schema=GateVerdict``.

Pre-filtro determinista (``response_claims_completed_action``): ver su
docstring para la heuristica exacta y sus limites documentados. Es la UNICA
parte de este modulo que no esta gobernada por la KB.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

from kb_agent.agents.base import Agent

__all__ = [
    "GateAgent",
    "GateVerdict",
    "render_gate_criteria",
    "response_claims_completed_action",
    "PREFILTER_CRITERION_ID",
]

#: Id sintetico (no viene de la KB) para el veredicto del pre-filtro
#: deterministico. Se distingue de los ids reales de ``GateCriterion``
#: (``gate-antonia-*``) a proposito: este chequeo no lo gobierna la KB, lo
#: gobierna el codigo -- ver docstring de ``response_claims_completed_action``.
PREFILTER_CRITERION_ID = "gate-integridad-accion-no-ejecutada"

_NO_CRITERIA_INSTRUCTION = (
    "Eres el GATE regulatorio de un programa de soporte a pacientes "
    "(farmacovigilancia). La base de conocimiento no tiene ningun "
    "GateCriterion cargado en este momento: aprueba por defecto cualquier "
    "respuesta razonable, sin inventar criterios propios."
)


class GateVerdict(BaseModel):
    """Salida tipada del juez. Contrato que ``Orchestrator`` consume."""

    approved: bool
    reasons: list[str] = Field(default_factory=list)
    action: Literal["pass", "handoff", "protocol"] = "pass"
    criterion_ids: list[str] = Field(default_factory=list)


def render_gate_criteria(gate_atoms: Sequence[Mapping[str, Any]]) -> str:
    """Renderiza los ``GateCriterion`` de la KB para el ``static_instruction``.

    Cada atom aporta ``criterion`` (que evaluar), ``approval_condition``
    (cuando pasa) y ``rejection_action`` (que hacer si no pasa) -- los 3
    campos que el gate viejo leia y despues ignoraba. Aca son el prompt
    completo: el LLM no tiene otra fuente de criterios.
    """
    if not gate_atoms:
        return _NO_CRITERIA_INSTRUCTION

    blocks: list[str] = []
    for atom in gate_atoms:
        atom_id = str(atom.get("id") or "")
        title = str(atom.get("title") or atom_id)
        criterion = str(atom.get("criterion") or "")
        approval = str(atom.get("approval_condition") or "")
        rejection = str(atom.get("rejection_action") or "")
        blocks.append(
            f"### {atom_id} — {title}\n"
            f"Criterio: {criterion}\n"
            f"Condicion de aprobacion: {approval}\n"
            f"Accion de rechazo: {rejection}"
        )

    criteria_ids = ", ".join(str(atom.get("id") or "") for atom in gate_atoms)
    return (
        "Eres el GATE regulatorio de un programa de soporte a pacientes "
        "(farmacovigilancia). Tu trabajo es juzgar la RESPUESTA REDACTADA "
        "por el agente conversador (no la pregunta del usuario) contra CADA "
        "UNO de los siguientes criterios, cargados desde la base de "
        "conocimiento. Si la respuesta viola alguno, recházala.\n\n"
        + "\n\n".join(blocks)
        + "\n\n"
        "Responde en el formato estructurado pedido: "
        "'approved' (true solo si TODOS los criterios se cumplen), "
        "'reasons' (una explicacion breve por cada criterio violado), "
        "'action' ('pass' si aprueba; 'handoff' si corresponde derivar la "
        "revision a un humano; 'protocol' si corresponde aplicar un "
        "protocolo especifico, p.ej. farmacovigilancia) y 'criterion_ids' "
        f"(los ids violados, tomados EXACTAMENTE de esta lista: {criteria_ids})."
    )


# ── pre-filtro deterministico: afirmar una accion que no se ejecuto ────────
#
# Los verbos cubiertos son, a proposito, los de acciones operativas tipicas
# de este agente (agendar/reservar/programar/registrar/confirmar/cancelar/
# modificar/enviar/crear/generar/guardar/actualizar/anotar/completar), todos
# verbos regulares terminados en "-ar". Se derivan programaticamente la forma
# de preterito 1a persona ("agendar" -> "agende", que normalizado sin tilde
# coincide con "agendé") y el participio ("agendad-" -> agendado/agendada/...).
_ACTION_VERBS_AR = (
    "agendar", "reservar", "programar", "registrar", "confirmar",
    "cancelar", "modificar", "enviar", "crear", "generar", "guardar",
    "actualizar", "anotar", "completar",
)


def _verb_stem(verb: str) -> str:
    return verb[:-2]


_PRETERITE_1P = sorted({_verb_stem(v) + "e" for v in _ACTION_VERBS_AR}, key=len, reverse=True)
_PARTICIPLE_STEM = sorted({_verb_stem(v) + "ad" for v in _ACTION_VERBS_AR}, key=len, reverse=True)

_CLAIM_RE = re.compile(r"\b(" + "|".join(_PRETERITE_1P) + r")\b")
_PASSIVE_RE = re.compile(
    r"\b(?:qued\w*|esta\w*|fue|ha sido|han sido)\s+\w*(?:" + "|".join(_PARTICIPLE_STEM) + r")\w*\b"
)

#: Marcadores de OFERTA ("¿querés que te agende?", "puedo reservarte si
#: quieres") -- si aparecen en la misma oracion que un verbo de accion, la
#: oracion NO cuenta como afirmacion de accion completada. Cubren tanto el
#: signo de pregunta como los lead-ins tipicos de ofrecimiento en espanol.
_OFFER_MARKERS = (
    "quieres", "queres", "quisieras", "desea", "deseas",
    "te gustaria", "prefieres", "gustarias",
    "puedo agendar", "puedo reservar", "puedo programar", "puedo registrar",
    "puedo confirmar", "puedo enviarte", "puedo enviar",
    "si quieres", "si queres", "si gustas", "si deseas",
    "te parece si", "avisame si", "me confirmas si", "confirmame si",
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold()


def _split_sentences(text: str) -> list[str]:
    return [s for s in re.split(r"[.!?\n]+", text) if s.strip()]


def response_claims_completed_action(response: str) -> bool:
    """Heuristica deterministica: la respuesta AFIRMA haber ejecutado una accion.

    Se usa como pre-filtro, ANTES de gastar una llamada al LLM: si la
    respuesta afirma "te agendé"/"ya quedó agendado"/"listo, programé" (o
    equivalentes con los verbos de ``_ACTION_VERBS_AR``) y no hubo tool real
    en el turno (``tool_called=False``), es un caso claro de rechazo -- el
    caso medido en el CLI real (Conversador respondiendo "¡Listo! Te agendé
    el recordatorio..." con ``tool.called: false``).

    Metodo: por ORACION (separada por ``. ! ? \\n``), sobre texto normalizado
    (sin tildes, casefold):
      1. si la oracion tiene un marcador de OFERTA (``_OFFER_MARKERS``) o
         signo de pregunta, se descarta -- ofrecer no es afirmar.
      2. si la oracion tiene un verbo de accion en preterito 1a persona
         ("agende" <- agendé, "reserve" <- reservé, ...) o una forma pasiva/
         copulativa + participio ("quedo agendado", "esta confirmado", "fue
         registrado"), cuenta como afirmacion.

    Limites conocidos (documentados a proposito, no corregidos aca):
      - Es SOLO espanol y SOLO cubre los verbos de ``_ACTION_VERBS_AR``. Una
        KB con otro dominio de tools (p.ej. "cotizar", "facturar") necesita
        extender la lista.
      - El preterito ("agendé") y el subjuntivo presente ("que (yo/el) agende")
        de un verbo ``-ar`` normalizan a la MISMA forma sin tilde ("agende").
        La oracion "¿Querés que te agende...?" se descarta por el signo de
        pregunta, y "si quieres que te agende" por el marcador de oferta
        "si quieres" -- pero una oferta SIN pregunta ni lead-in reconocido
        (p.ej. "Que te agende entonces." dicho por el USUARIO, no el agente)
        podria dar falso positivo si apareciera como respuesta del agente.
      - No entiende negacion ("no te agendé todavia") ni condicionales
        complejos: es lexica, no sintactica.
      - Es intencionalmente conservadora hacia MENOS falsos positivos
        (prioriza no bloquear ofertas legitimas) a costa de poder dejar
        pasar alguna afirmacion fraseada de forma atipica -- el pre-filtro
        es una red de seguridad barata, no el gate completo; el LLM-judge
        (cuando corre) sigue evaluando el resto de los criterios.
    """
    if not response or not response.strip():
        return False
    for sentence in _split_sentences(response):
        normalized = _normalize(sentence)
        if "?" in sentence or any(marker in normalized for marker in _OFFER_MARKERS):
            continue
        if _CLAIM_RE.search(normalized) or _PASSIVE_RE.search(normalized):
            return True
    return False


def _prefilter_verdict(response: str, *, tool_name: str | None) -> dict[str, Any]:
    reason = (
        "La respuesta afirma haber ejecutado una accion"
        + (f" ({tool_name})" if tool_name else "")
        + ", pero no hubo ninguna ejecucion real de tool en este turno "
        "(tool_called=False). Afirmar una accion que no ocurrio no se envia."
    )
    return {
        "approved": False,
        "reasons": [reason],
        "action": "handoff",
        "criterion_ids": [PREFILTER_CRITERION_ID],
    }


def _dynamic_context(
    response: str, *, tool_called: bool, tool_name: str | None, step: str | None
) -> dict[str, Any]:
    return {
        "respuesta_redactada": response,
        "tool_called": bool(tool_called),
        "tool_name": tool_name,
        "step": step,
    }


class GateAgent:
    """Policy gate: juez LLM sobre ``kb_agent.agents.base.Agent``.

    Se construye UNA vez (los ``GateCriterion`` son fijos por proceso) y se
    reusa en todos los turnos via ``evaluate``. No decide fail-open: eso es
    responsabilidad del llamador (``Orchestrator._policy_gate``), que envuelve
    ``evaluate`` en un ``try/except`` -- ver su docstring.
    """

    def __init__(self, *, name: str = "gate", client: Any, model: str, gate_atoms: Sequence[Mapping[str, Any]]) -> None:
        self._has_criteria = bool(gate_atoms)
        self.static_instruction = render_gate_criteria(gate_atoms)
        self._agent = Agent(
            name=name,
            client=client,
            model=model,
            static_instruction=self.static_instruction,
            include_contents=False,
            output_schema=GateVerdict,
        )

    def evaluate(
        self,
        response: str,
        *,
        tool_called: bool,
        tool_name: str | None = None,
        step: str | None = None,
        session_tools_called: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Veredicto sobre ``response``. Puede lanzar (ver ``Orchestrator._policy_gate``).

        ``session_tools_called`` son las tools que YA se ejecutaron antes en
        esta conversacion. El pre-filtro es por turno, pero la afirmacion del
        agente puede referirse legitimamente a algo hecho en un turno previo:
        medido en el CLI real, "agendame un recordatorio" ejecuto la tool en el
        turno 2 y en el turno 3 ("si, dale, confirmalo") el agente respondio
        "ya esta confirmado tu recordatorio" -- cierto, con ``tool_called``
        False en ESE turno. Sin este dato el gate derivaba a un humano una
        respuesta correcta.
        """
        if not isinstance(response, str) or not response.strip():
            return {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}

        if (
            not tool_called
            and not session_tools_called
            and response_claims_completed_action(response)
        ):
            return _prefilter_verdict(response, tool_name=tool_name)

        if not self._has_criteria:
            return {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}

        verdict = self._agent.run(
            _dynamic_context(response, tool_called=tool_called, tool_name=tool_name, step=step)
        )
        assert isinstance(verdict, GateVerdict)
        return verdict.model_dump()
