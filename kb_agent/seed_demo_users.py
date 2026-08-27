"""Siembra la DB de perfilado con usuarios demo (Antonia / PSP Selfix).

Crea usuarios con historial de chat AGRUPADO EN CONVERSACIONES REALES
(``chat_history.session_id``) y su rastro por turno en ``turns`` -- el mismo
par de tablas que llena ``Orchestrator.handle_turn``/``_persist_turn`` en
produccion -- para que ``/users`` muestre conversaciones (no mensajes
sueltos) y el Turn Inspector tenga algo que auditar al reabrir una
conversacion pasada.

El rastro por turno es la respuesta de cada subagente + los ATOMOS POR ID
(nunca el texto de los documentos, solo sus ids -- igual que hace el
Ruteador real, ver ``ContextCompiler._build_bundle``): ``bundle`` con
``doc_id`` reales de ``knowledge/atoms/`` (family: domain/conversation/user/
gate, motivo: piso de seguridad / grounding de <step> / trait del usuario /
similitud <score>), ``decision`` del orquestador, ``gate`` del policy gate y
``draft`` del conversador ANTES del gate (se conserva aunque el gate lo
reemplace, igual que en produccion).

Uso:
    python -m kb_agent.seed_demo_users            # usa PROFILING_DB del config
    python -m kb_agent.seed_demo_users --db ruta.sqlite

Idempotente: hace upsert por external_id (borra y recrea el usuario demo,
su ChatHistory y sus Turns).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kb_agent.models_sql.identity import Base as IdentityBase, Users, UserTraits
from kb_agent.models_sql.session import ChatHistory
from kb_agent.models_sql.turns import Turns
from kb_agent.project_config import load_project_config

# trait_ids reales de la KB de Antonia (cruzan con fichas SLDB type.knowledge.trait)
TRAITS = {
    "primera_vez": "trait-antonia-primera-vez",
    "ansioso": "trait-antonia-ansioso-aplicacion",
    "adherencia": "trait-antonia-buena-adherencia",
    "dudas": "trait-antonia-dudas-efectos",
    "recordatorios": "trait-antonia-prefiere-recordatorios",
}

# Respuesta estandar de handoff que emite Orchestrator.handle_turn cuando el
# Gate rechaza el borrador (ver kb_agent/orchestrator.py, rama `kind = "derived"`).
GATE_HANDOFF_TEXT = (
    "He preparado una respuesta pero prefiero que un profesional "
    "del programa la revise antes de enviarla. Alguien del equipo "
    "te contactará a la brevedad."
)

APPROVED_GATE = {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}
SKIPPED_GATE_TOOL_CALL = {"approved": None, "skipped": "tool_call"}

# Usuarios demo: perfiles distintos del PSP Selfix. Cada uno es UNA
# conversacion (session_id propio) con sus turnos y el rastro que hoy
# arma Orchestrator.handle_turn en `decisions` (ver su docstring y
# `_persist_turn`): step antes/despues, bundle justificado (doc_id real +
# family + motivo + score), decision del orquestador, gate y draft.
DEMO_USERS = [
    {
        "external_id": "wa-56991112233",
        "channel": "whatsapp",
        "traits": [
            (TRAITS["primera_vez"], 0.92, "reflector"),
            (TRAITS["ansioso"], 0.85, "reflector"),
            (TRAITS["dudas"], 0.71, "perfilador"),
        ],
        # Onboarding de una paciente primeriza con miedo a la aguja.
        "turns": [
            {
                "user": "hola, me acaban de recetar Selfix y nunca me he inyectado nada",
                "assistant": "Hola, tranquila. Te acompaño en tu primera aplicación paso a paso.",
                "step_before": None,
                "step_after": "steps.onboarding",
                "allowed_transitions": ["steps.onboarding", "steps.evento_adverso", "steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "rule-antonia-eventos-adversos", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-onboarding", "family": "conversation", "motivo": "grounding de steps.onboarding", "score": None},
                    {"doc_id": "atom-antonia-bienvenida", "family": "domain", "motivo": "grounding de steps.onboarding", "score": None},
                    {"doc_id": "trait-antonia-primera-vez", "family": "user", "motivo": "trait del usuario", "score": None},
                    {"doc_id": "atom-antonia-primeras-semanas", "family": "domain", "motivo": "similitud 0.78", "score": 0.78},
                ],
                "reason": "Saludo inicial de una paciente que declara ser primeriza; no hay tool que llamar, corresponde dar la bienvenida y anticipar el acompañamiento.",
                "step_target": "steps.onboarding",
                "step_target_vetado": None,
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
            {
                "user": "me da miedo la aguja, es muy grande?",
                "assistant": "La aguja es muy fina y corta. Muchas personas no sienten casi nada.",
                "step_before": "steps.onboarding",
                "step_after": "steps.onboarding",
                "allowed_transitions": ["steps.onboarding", "steps.evento_adverso", "steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-onboarding", "family": "conversation", "motivo": "grounding de steps.onboarding", "score": None},
                    {"doc_id": "atom-antonia-aplicacion", "family": "domain", "motivo": "grounding de steps.onboarding", "score": None},
                    {"doc_id": "trait-antonia-ansioso-aplicacion", "family": "user", "motivo": "trait del usuario", "score": None},
                    {"doc_id": "atom-antonia-primeras-semanas", "family": "domain", "motivo": "similitud 0.69", "score": 0.69},
                ],
                "reason": "Pregunta sobre el dispositivo de aplicación; se responde con la ficha de aplicación aprobada, sin agregar indicaciones clínicas nuevas.",
                "step_target": "steps.onboarding",
                "step_target_vetado": None,
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
            {
                "user": "y si me equivoco en la dosis?",
                "assistant": "El dispositivo tiene tope de dosis, es difícil equivocarse. Te muestro el video aprobado.",
                "step_before": "steps.onboarding",
                "step_after": "steps.onboarding",
                "allowed_transitions": ["steps.onboarding", "steps.evento_adverso", "steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "gate-antonia-dosis", "family": "gate", "motivo": "similitud 0.74", "score": 0.74},
                    {"doc_id": "step-antonia-onboarding", "family": "conversation", "motivo": "grounding de steps.onboarding", "score": None},
                    {"doc_id": "atom-antonia-titulacion", "family": "domain", "motivo": "similitud 0.81", "score": 0.81},
                    {"doc_id": "trait-antonia-ansioso-aplicacion", "family": "user", "motivo": "trait del usuario", "score": None},
                ],
                # Violacion atrapada: el modelo propuso saltar a revision humana:
                # la guardia dura la veta porque no esta en allowed_transitions
                # del step activo (ver apply_transition_guard).
                "reason": "Pregunta por error de dosis; se responde con la ficha de titulación. El modelo propuso escalar a revisión humana pero la transición no está permitida desde onboarding.",
                "step_target": None,
                "step_target_vetado": "steps.revision_humana",
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
        ],
    },
    {
        "external_id": "wa-56944455566",
        "channel": "whatsapp",
        "traits": [
            (TRAITS["adherencia"], 0.96, "reflector"),
            (TRAITS["recordatorios"], 0.88, "perfilador"),
        ],
        # Activacion de recordatorios: incluye un tool_call real (gate skipped).
        "turns": [
            {
                "user": "quiero activar los recordatorios semanales",
                "assistant": "Perfecto. ¿Qué día y hora prefieres para tu aplicación?",
                "step_before": None,
                "step_after": "steps.agendar_recordatorio",
                "allowed_transitions": ["steps.agendar_recordatorio", "steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-agendar-recordatorio", "family": "conversation", "motivo": "grounding de steps.agendar_recordatorio", "score": None},
                    {"doc_id": "tool-antonia-agendar-recordatorio", "family": "self", "motivo": "similitud 0.83", "score": 0.83},
                    {"doc_id": "trait-antonia-prefiere-recordatorios", "family": "user", "motivo": "trait del usuario", "score": None},
                ],
                "reason": "El usuario pide activar recordatorios; falta día/hora para poder llamar la tool, se pregunta antes de invocarla.",
                "step_target": "steps.agendar_recordatorio",
                "step_target_vetado": None,
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
            {
                "user": "los domingos a las 9am",
                "assistant": "Listo, te recordaré cada domingo 9am. Vas muy bien con tu adherencia.",
                "step_before": "steps.agendar_recordatorio",
                "step_after": "steps.agendar_recordatorio",
                "allowed_transitions": ["steps.agendar_recordatorio", "steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-agendar-recordatorio", "family": "conversation", "motivo": "grounding de steps.agendar_recordatorio", "score": None},
                    {"doc_id": "tool-antonia-agendar-recordatorio", "family": "self", "motivo": "similitud 0.88", "score": 0.88},
                    {"doc_id": "trait-antonia-prefiere-recordatorios", "family": "user", "motivo": "trait del usuario", "score": None},
                    {"doc_id": "trait-antonia-buena-adherencia", "family": "user", "motivo": "trait del usuario", "score": None},
                ],
                "reason": "Ya hay día y hora; corresponde llamar la tool agendar_recordatorio con esos datos.",
                "step_target": None,
                "step_target_vetado": None,
                "kind": "tool_call",
                # kind=tool_call: el Gate se salta (solo aplica a redacciones NL,
                # ver Orchestrator.handle_turn), igual que en produccion.
                "gate": SKIPPED_GATE_TOOL_CALL,
                "tool": {"called": True, "tool": "agendar_recordatorio", "status": "ok", "dia": "domingo", "hora": "09:00"},
            },
            {
                "user": "gracias, no he fallado ninguna semana",
                "assistant": "Excelente constancia. Eso es clave para el tratamiento.",
                "step_before": "steps.agendar_recordatorio",
                "step_after": "steps.despedida",
                "allowed_transitions": ["steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-despedida", "family": "conversation", "motivo": "grounding de steps.despedida", "score": None},
                    {"doc_id": "trait-antonia-buena-adherencia", "family": "user", "motivo": "trait del usuario", "score": None},
                    {"doc_id": "atom-antonia-primeras-semanas", "family": "domain", "motivo": "similitud 0.62", "score": 0.62},
                ],
                "reason": "Cierre positivo de la interacción; se refuerza la adherencia declarada por la paciente.",
                "step_target": "steps.despedida",
                "step_target_vetado": None,
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
        ],
    },
    {
        "external_id": "web-anon-4821",
        "channel": "web",
        "traits": [
            (TRAITS["dudas"], 0.79, "perfilador"),
            (TRAITS["ansioso"], 0.64, "perfilador"),
        ],
        # Duda sobre dolor en sitio de inyeccion: el PRIMER turno muestra un
        # rechazo real del Gate (el borrador suena a diagnostico -> handoff).
        "turns": [
            {
                "user": "es normal sentir dolor en el sitio de inyección?",
                # Texto final que SI vio la paciente (post-gate): handoff.
                "assistant": GATE_HANDOFF_TEXT,
                # Borrador del Conversador ANTES del gate -- el gate lo reemplazo.
                "draft": "Sí, es completamente normal, no te preocupes y continúa con tu tratamiento sin problema.",
                "step_before": None,
                "step_after": "steps.evento_adverso",
                "allowed_transitions": ["steps.evento_adverso", "steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "rule-antonia-eventos-adversos", "family": "domain", "motivo": "similitud 0.72", "score": 0.72},
                    {"doc_id": "step-antonia-evento-adverso", "family": "conversation", "motivo": "grounding de steps.evento_adverso", "score": None},
                    {"doc_id": "atom-antonia-ea-esperados", "family": "domain", "motivo": "similitud 0.85", "score": 0.85},
                    {"doc_id": "gate-antonia-diagnostico", "family": "gate", "motivo": "similitud 0.69", "score": 0.69},
                    {"doc_id": "trait-antonia-dudas-efectos", "family": "user", "motivo": "trait del usuario", "score": None},
                    {"doc_id": "trait-antonia-ansioso-aplicacion", "family": "user", "motivo": "trait del usuario", "score": None},
                ],
                "reason": "La paciente pregunta si un síntoma es 'normal', lo que roza un juicio clínico; se redacta igual para que el Gate evalúe antes de enviar.",
                "step_target": "steps.evento_adverso",
                "step_target_vetado": None,
                # kind final queda "derived" (el Gate rechazo el NL) -- ver
                # Orchestrator.handle_turn, rama `if not gate_result["approved"]`.
                "kind": "derived",
                "gate": {
                    "approved": False,
                    "reasons": [
                        "la respuesta afirma que un síntoma es 'normal' sin criterio clínico explícito de la KB (rule-antonia-no-deducir)",
                        "no deriva a farmacovigilancia ante un posible evento adverso",
                    ],
                    "action": "handoff",
                    "criterion_ids": ["gate-antonia-diagnostico"],
                },
                "tool": {"called": False},
            },
            {
                "user": "cuánto dura ese efecto?",
                "assistant": "Normalmente unas horas. Si persiste más de 2 días, conviene consultar.",
                "step_before": "steps.evento_adverso",
                "step_after": "steps.evento_adverso",
                "allowed_transitions": ["steps.evento_adverso", "steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-evento-adverso", "family": "conversation", "motivo": "grounding de steps.evento_adverso", "score": None},
                    {"doc_id": "atom-antonia-ea-esperados", "family": "domain", "motivo": "similitud 0.88", "score": 0.88},
                    {"doc_id": "atom-antonia-ea-administracion", "family": "domain", "motivo": "similitud 0.71", "score": 0.71},
                    {"doc_id": "trait-antonia-dudas-efectos", "family": "user", "motivo": "trait del usuario", "score": None},
                ],
                "reason": "Pregunta de seguimiento sobre duración de un efecto esperado; se responde con la ficha de eventos adversos esperados, sin diagnosticar.",
                "step_target": "steps.evento_adverso",
                "step_target_vetado": None,
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
        ],
    },
    {
        "external_id": "wa-56977788899",
        "channel": "whatsapp",
        "traits": [
            (TRAITS["primera_vez"], 0.68, "perfilador"),
            (TRAITS["recordatorios"], 0.72, "perfilador"),
            (TRAITS["adherencia"], 0.55, "reflector"),
        ],
        # Preguntas operativas: conservacion y viaje.
        "turns": [
            {
                "user": "cómo conservo el producto?",
                "assistant": "En refrigeración entre 2 y 8°C, sin congelar. Te explico el detalle.",
                "step_before": None,
                "step_after": "steps.journey_operativo",
                "allowed_transitions": ["steps.journey_operativo", "steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-journey-operativo", "family": "conversation", "motivo": "grounding de steps.journey_operativo", "score": None},
                    {"doc_id": "atom-antonia-aplicacion", "family": "domain", "motivo": "similitud 0.66", "score": 0.66},
                    {"doc_id": "trait-antonia-primera-vez", "family": "user", "motivo": "trait del usuario", "score": None},
                ],
                "reason": "Pregunta operativa sobre conservación del producto; se responde con la ficha operativa correspondiente.",
                "step_target": "steps.journey_operativo",
                "step_target_vetado": None,
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
            {
                "user": "y si viajo?",
                "assistant": "Usa una nevera portátil con gel refrigerante. No lo expongas al calor.",
                "step_before": "steps.journey_operativo",
                "step_after": "steps.journey_operativo",
                "allowed_transitions": ["steps.journey_operativo", "steps.despedida"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-journey-operativo", "family": "conversation", "motivo": "grounding de steps.journey_operativo", "score": None},
                    {"doc_id": "atom-antonia-aplicacion", "family": "domain", "motivo": "similitud 0.73", "score": 0.73},
                    {"doc_id": "trait-antonia-prefiere-recordatorios", "family": "user", "motivo": "trait del usuario", "score": None},
                    {"doc_id": "trait-antonia-buena-adherencia", "family": "user", "motivo": "trait del usuario", "score": None},
                ],
                "reason": "Pregunta de seguimiento sobre viajes; se refuerza la indicación de conservación en frío.",
                "step_target": "steps.journey_operativo",
                "step_target_vetado": None,
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
        ],
    },
    {
        "external_id": "wa-56933344455",
        "channel": "whatsapp",
        "traits": [
            (TRAITS["dudas"], 0.88, "reflector"),
            (TRAITS["adherencia"], 0.64, "perfilador"),
        ],
        # Evento adverso: la rama de farmacovigilancia. Es el caso que mas
        # importa del PSP y el que ejercita el gate de verdad.
        "turns": [
            {
                "user": "me salio una roncha roja donde me inyecte y me arde",
                "assistant": "Gracias por contarme. Voy a registrar lo que me describes para que el equipo del programa lo revise.",
                "step_before": "steps.registro_estado",
                "step_after": "steps.evento_adverso",
                "allowed_transitions": ["steps.evento_adverso", "steps.agendar_recordatorio", "steps.derivacion_medinfo"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "rule-antonia-eventos-adversos", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "rule-antonia-no-diagnosticar", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-evento-adverso", "family": "conversation", "motivo": "grounding de steps.evento_adverso", "score": None},
                    {"doc_id": "atom-antonia-ea", "family": "domain", "motivo": "similitud 0.84", "score": 0.84},
                    {"doc_id": "atom-antonia-ea-administracion", "family": "domain", "motivo": "similitud 0.77", "score": 0.77},
                ],
                "reason": "La paciente describe una reaccion local en el sitio de aplicacion: es un evento adverso y corresponde navegar a esa rama y registrarlo sin interpretar el sintoma.",
                "step_target": "steps.evento_adverso",
                "step_target_vetado": None,
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
            {
                "user": "es grave? me tengo que preocupar?",
                "assistant": GATE_HANDOFF_TEXT,
                "draft": "No parece grave, suele ser una reaccion local leve que pasa sola en un par de dias.",
                "step_before": "steps.evento_adverso",
                "step_after": "steps.derivacion_medinfo",
                "allowed_transitions": ["steps.despedida", "steps.derivacion_medinfo"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "rule-antonia-no-diagnosticar", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "gate-antonia-diagnostico", "family": "gate", "motivo": "similitud 0.86", "score": 0.86},
                    {"doc_id": "atom-antonia-ea-esperados", "family": "domain", "motivo": "similitud 0.79", "score": 0.79},
                    {"doc_id": "step-antonia-derivacion-medinfo", "family": "conversation", "motivo": "grounding de steps.derivacion_medinfo", "score": None},
                ],
                "reason": "Pregunta por gravedad: es una valoracion clinica que Antonia no puede hacer; corresponde derivar.",
                "step_target": "steps.derivacion_medinfo",
                "step_target_vetado": None,
                # El borrador calificaba la gravedad ("no parece grave", "pasa
                # sola"): el gate lo rechaza por gate-antonia-diagnostico y lo
                # reemplaza por el handoff. draft y texto final quedan distintos.
                "gate": {
                    "approved": False,
                    "reasons": [
                        "La respuesta califica la gravedad de un sintoma y anticipa su evolucion, lo que constituye una valoracion clinica no sostenida por el corpus.",
                    ],
                    "action": "handoff",
                    "criterion_ids": ["gate-antonia-diagnostico"],
                },
                "tool": {"called": False},
            },
        ],
    },
    {
        "external_id": "wa-56911122233",
        "channel": "whatsapp",
        "traits": [
            (TRAITS["recordatorios"], 0.81, "perfilador"),
        ],
        # Enrolamiento: paciente que NO viene inscrita en el PSP (users.enrolled
        # False). Ejercita el step nuevo y la tool registrar_enrolamiento.
        "turns": [
            {
                "user": "hola, me hablaron del programa de acompañamiento pero no se si estoy inscrita",
                "assistant": "Hola. Te cuento en que consiste y, si quieres, te inscribo. Necesito tu nombre, un telefono y un correo de contacto.",
                "step_before": None,
                "step_after": "steps.enrolamiento",
                "allowed_transitions": ["steps.derivacion_medinfo", "steps.onboarding"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-enrolamiento", "family": "conversation", "motivo": "grounding de steps.enrolamiento", "score": None},
                    {"doc_id": "self-antonia", "family": "self", "motivo": "grounding de steps.enrolamiento", "score": None},
                    {"doc_id": "atom-antonia-bienvenida", "family": "domain", "motivo": "similitud 0.73", "score": 0.73},
                ],
                "reason": "La persona no figura inscrita (enrolled=False): corresponde el step de enrolamiento y pedir los datos de contacto de a uno.",
                "step_target": "steps.enrolamiento",
                "step_target_vetado": None,
                "gate": APPROVED_GATE,
                "tool": {"called": False},
            },
            {
                "user": "Carolina Rojas, +56911122233, carolina.rojas@ejemplo.cl",
                "assistant": "Listo Carolina, quedaste inscrita en el programa. Ahora te acompaño con tu tratamiento.",
                "step_before": "steps.enrolamiento",
                "step_after": "steps.onboarding",
                "allowed_transitions": ["steps.derivacion_medinfo", "steps.onboarding"],
                "bundle": [
                    {"doc_id": "rule-antonia-anti-alucinacion", "family": "domain", "motivo": "piso de seguridad", "score": None},
                    {"doc_id": "step-antonia-enrolamiento", "family": "conversation", "motivo": "grounding de steps.enrolamiento", "score": None},
                    {"doc_id": "tool-antonia-registrar-enrolamiento", "family": "self", "motivo": "la tool del step activo, con los tres slots completos", "score": None},
                ],
                "reason": "Estan los tres slots requeridos (nombre, telefono, correo): corresponde ejecutar registrar_enrolamiento y pasar a onboarding.",
                "step_target": "steps.onboarding",
                "step_target_vetado": None,
                "gate": SKIPPED_GATE_TOOL_CALL,
                # PII: el rastro guarda si el dato se entrego, NUNCA su valor
                # (ver kb_agent/tools/enrolamiento.py).
                "tool": {
                    "called": True,
                    "tool": "registrar_enrolamiento",
                    "status": "ok",
                    "args": {"nombre_provisto": True, "telefono_provisto": True, "mail_provisto": True},
                    "enrolled": True,
                },
            },
        ],
    },
]


def _session_id_for(external_id: str) -> str:
    """session_id demo, estable por usuario (una conversacion por usuario demo)."""
    return f"demo-{external_id}"


def seed(db_path: str) -> dict:
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    IdentityBase.metadata.create_all(engine)  # misma metadata que ChatHistory y Turns
    Session = sessionmaker(bind=engine, future=True)

    now = datetime.now(timezone.utc)
    created = {"users": 0, "traits": 0, "chats": 0, "turns": 0}

    with Session() as s:
        for i, spec in enumerate(DEMO_USERS):
            # upsert: borra usuario demo previo (cascade borra traits/chats/turns)
            existing = s.query(Users).filter(Users.external_id == spec["external_id"]).first()
            if existing:
                s.query(ChatHistory).filter(ChatHistory.user_id == existing.id).delete()
                s.query(Turns).filter(Turns.user_id == existing.id).delete()
                s.delete(existing)
                s.flush()

            u = Users(
                external_id=spec["external_id"],
                channel=spec["channel"],
                created_at=now - timedelta(days=7 - i),
            )
            s.add(u)
            s.flush()  # obtener u.id
            created["users"] += 1

            # traits
            for trait_id, conf, source in spec["traits"]:
                s.add(UserTraits(
                    user_id=u.id,
                    trait_id=trait_id,
                    confidence=conf,
                    source=source,
                    created_at=now - timedelta(days=5 - i, hours=2),
                ))
                created["traits"] += 1

            # conversacion: UNA session_id para todos los turnos de este usuario
            # demo (chat_history.session_id, migracion 8df38d93ccd7) + su rastro
            # en `turns` (mismo shape que Orchestrator._persist_turn).
            session_id = _session_id_for(spec["external_id"])
            base = now - timedelta(days=5 - i)
            for j, turn in enumerate(spec["turns"]):
                ts_user = base + timedelta(minutes=j * 3)
                ts_assistant = ts_user + timedelta(seconds=20)
                s.add(ChatHistory(
                    user_id=u.id,
                    session_id=session_id,
                    role="user",
                    content=turn["user"],
                    pii_scrubbed=True,
                    created_at=ts_user,
                ))
                s.add(ChatHistory(
                    user_id=u.id,
                    session_id=session_id,
                    role="assistant",
                    content=turn["assistant"],
                    pii_scrubbed=False,
                    created_at=ts_assistant,
                ))
                created["chats"] += 2

                orquestador_decision = {"kind": turn.get("kind", "nl"), "reason": turn["reason"]}
                if turn.get("step_target") is not None:
                    orquestador_decision["step_target"] = turn["step_target"]
                if turn.get("step_target_vetado") is not None:
                    orquestador_decision["step_target_vetado"] = turn["step_target_vetado"]

                decisions = {
                    "step": {
                        "before": turn["step_before"],
                        "after": turn["step_after"],
                        "target": turn.get("step_target"),
                        "allowed_transitions": turn.get("allowed_transitions", []),
                        "missing_slots": [],
                    },
                    "ruteador": {
                        "bundle": turn["bundle"],
                        "atoms": len(turn["bundle"]),
                        "grounding_atoms": [
                            b["doc_id"] for b in turn["bundle"] if "grounding de" in b["motivo"]
                        ],
                        "user_traits": [
                            b["doc_id"] for b in turn["bundle"] if b["motivo"] == "trait del usuario"
                        ],
                        "is_empty": False,
                    },
                    "orquestador": {
                        "kind": turn.get("kind", "nl"),
                        "decision": orquestador_decision,
                        "state_trace": ["idle", "evaluating_context", "drafting_response", "idle"],
                        "reason": turn["reason"],
                        "step_target_vetado": turn.get("step_target_vetado"),
                    },
                    "conversador": {"draft": turn.get("draft", turn["assistant"])},
                    "gate": turn["gate"],
                    "tool": turn["tool"],
                }

                s.add(Turns(
                    turn_id=f"t{j + 1}",
                    session_id=session_id,
                    user_id=u.id,
                    step_before=turn["step_before"],
                    step_after=turn["step_after"],
                    decision=decisions["orquestador"],
                    draft=turn.get("draft", turn["assistant"]),
                    gate=turn["gate"],
                    bundle=turn["bundle"],
                    tool=turn["tool"] if turn["tool"] else None,
                    created_at=ts_assistant,
                ))
                created["turns"] += 1

        s.commit()

    engine.dispose()
    return created


def main() -> None:
    ap = argparse.ArgumentParser(description="Siembra usuarios demo en la DB de perfilado")
    ap.add_argument("--db", default=None, help="ruta al sqlite de perfilado (default: config)")
    args = ap.parse_args()

    db_path = args.db
    if db_path is None:
        cfg = load_project_config()
        db_path = str(cfg.profiling_db)

    result = seed(db_path)
    print(f"Sembrado en {db_path}:")
    print(f"  usuarios: {result['users']}")
    print(f"  traits:   {result['traits']}")
    print(f"  chats:    {result['chats']}")
    print(f"  turns:    {result['turns']}")


if __name__ == "__main__":
    main()
