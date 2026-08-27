from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

DEMO_CONFIG: dict[str, Any] = {
    "name": "Demo Agent",
    "slug": "antonia-demo",
    "model": "fake-llm-demo",
    "runtime_title": "Demo Agent",
    "kb_label": "Antonia · Demo",
    "greeting": "Hola. Soy **Antonia** en modo demo. Puedo orientarte sobre aplicación, recordatorios y derivación a soporte del programa.",
    "input_placeholder": "Escribe algo…",
    "mode": "demo",
    "nav_labels": {"chat": "Chat", "flow": "Flow", "mindmap": "Mindmap", "users": "Users"},
}

FLOW_NODES = ["bienvenida", "consulta", "obtencion_datos", "tool", "despedida"]

DEMO_ATOMS: dict[str, dict[str, Any]] = {
    "self-antonia": {
        "atom_id": "self-antonia",
        "title": "Antonia — PSP Selfix",
        "family": "self",
        "role": "identity",
        "tags": ["self:whoami", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/self-antonia.md",
        "body": "## Statement\n\nSoy Antonia, asistente del programa de acompañamiento de Selfix. Acompaño, no reemplazo al médico tratante.",
        "summary": "Identidad y alcance de Antonia.",
    },
    "style-antonia": {
        "atom_id": "style-antonia",
        "title": "Style Antonia",
        "family": "self",
        "role": "style",
        "tags": ["self:style", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/style-antonia.md",
        "body": "## Tone\n\nCálida, cercana y clara.\n\n## Length\n\nRespuestas breves, concretas y sin jerga técnica.",
        "summary": "Guía de tono y longitud.",
    },
    "atom-antonia-aplicacion": {
        "atom_id": "atom-antonia-aplicacion",
        "title": "Administración de Selfix",
        "family": "domain",
        "role": "grounding",
        "tags": ["domain:tratamiento", "conversation:steps.recompra", "system:laboratorio-chile"],
        "five_wh_one_plus": "how",
        "path": "knowledge/atoms/atom-antonia-aplicacion.md",
        "body": "## Answer\n\nLa aplicación es semanal. Conviene mantener día y hora estables, rotar el sitio de aplicación y conservar el producto según indicación del programa.",
        "summary": "Aplicación semanal, rotación y conservación.",
    },
    "atom-antonia-primeras-semanas": {
        "atom_id": "atom-antonia-primeras-semanas",
        "title": "Primeras semanas de tratamiento",
        "family": "domain",
        "role": "grounding",
        "tags": ["domain:onboarding", "conversation:steps.onboarding", "system:laboratorio-chile"],
        "five_wh_one_plus": "what",
        "path": "knowledge/atoms/atom-antonia-primeras-semanas.md",
        "body": "## Answer\n\nEn las primeras semanas es útil anticipar dudas frecuentes, validar cómo se siente la persona y reforzar adherencia sin prometer resultados clínicos.",
        "summary": "Expectativas y acompañamiento inicial.",
    },
    "rule-antonia-eventos-adversos": {
        "atom_id": "rule-antonia-eventos-adversos",
        "title": "Detección de eventos adversos",
        "family": "domain",
        "role": "safety_rule",
        "tags": ["domain:seguridad", "conversation:pharmacovigilance", "system:laboratorio-chile"],
        "five_wh_one_plus": "how",
        "path": "knowledge/atoms/rule-antonia-eventos-adversos.md",
        "body": "## Answer\n\nSi la persona reporta malestar o una reacción, se responde con calidez, no se interpreta gravedad y se deriva a un profesional del programa.",
        "summary": "Regla de seguridad para farmacovigilancia.",
    },
    "rule-antonia-no-deducir": {
        "atom_id": "rule-antonia-no-deducir",
        "title": "No deducir datos faltantes",
        "family": "domain",
        "role": "policy_rule",
        "tags": ["domain:integridad", "conversation:steps.registro_estado", "system:laboratorio-chile"],
        "five_wh_one_plus": "why",
        "path": "knowledge/atoms/rule-antonia-no-deducir.md",
        "body": "## Answer\n\nNo inventar día, hora ni datos clínicos. Si falta algo, pedirlo explícitamente.",
        "summary": "Regla de integridad para slots y contexto.",
    },
    "step-antonia-saludo": {
        "atom_id": "step-antonia-saludo",
        "title": "Saludo inicial",
        "family": "conversation",
        "role": "flow_step",
        "tags": ["conversation:steps.saludo", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/step-antonia-saludo.md",
        "body": "## Instructions\n\nSaludar con calidez y ubicar a la persona en el flujo demo.",
        "summary": "Paso de bienvenida.",
    },
    "step-antonia-registro-estado": {
        "atom_id": "step-antonia-registro-estado",
        "title": "Registro de estado",
        "family": "conversation",
        "role": "flow_step",
        "tags": ["conversation:steps.registro_estado", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/step-antonia-registro-estado.md",
        "body": "## Instructions\n\nDetectar intención principal: duda práctica, ansiedad, recordatorio o posible evento adverso.",
        "summary": "Clasificación de intención.",
    },
    "step-antonia-agendar-recordatorio": {
        "atom_id": "step-antonia-agendar-recordatorio",
        "title": "Agendar recordatorio",
        "family": "conversation",
        "role": "flow_step",
        "tags": ["conversation:steps.agendar_recordatorio", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/step-antonia-agendar-recordatorio.md",
        "body": "## Instructions\n\nPedir día y hora antes de ejecutar la tool de recordatorio.",
        "summary": "Paso de captura de slots para tool.",
    },
    "step-antonia-despedida": {
        "atom_id": "step-antonia-despedida",
        "title": "Despedida",
        "family": "conversation",
        "role": "flow_step",
        "tags": ["conversation:steps.despedida", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/step-antonia-despedida.md",
        "body": "## Instructions\n\nCerrar con amabilidad y resumir la acción tomada.",
        "summary": "Paso terminal del flujo demo.",
    },
    "trait-antonia-ansioso-aplicacion": {
        "atom_id": "trait-antonia-ansioso-aplicacion",
        "title": "Ansioso/a con la aplicación",
        "family": "user",
        "role": "user_trait",
        "tags": ["user:traits.ansioso_aplicacion", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/trait-antonia-ansioso-aplicacion.md",
        "body": "## Description\n\nMuestra miedo o ansiedad ante la auto-aplicación. Conviene validar la emoción y ofrecer una pauta simple.",
        "summary": "Rasgo de ansiedad frente a agujas o dolor.",
        "category": "behavior",
    },
    "trait-antonia-prefiere-recordatorios": {
        "atom_id": "trait-antonia-prefiere-recordatorios",
        "title": "Prefiere recordatorios",
        "family": "user",
        "role": "user_trait",
        "tags": ["user:traits.recordatorios", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/trait-antonia-prefiere-recordatorios.md",
        "body": "## Description\n\nValora ayudas prácticas para sostener la adherencia semanal.",
        "summary": "Preferencia por apoyos prácticos de adherencia.",
        "category": "preference",
    },
    "trait-antonia-primera-vez": {
        "atom_id": "trait-antonia-primera-vez",
        "title": "Primera vez en tratamiento",
        "family": "user",
        "role": "user_trait",
        "tags": ["user:traits.primera_vez", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/trait-antonia-primera-vez.md",
        "body": "## Description\n\nEstá iniciando y necesita más acompañamiento práctico.",
        "summary": "Usuario nuevo en el programa.",
        "category": "journey",
    },
    "agendar_recordatorio": {
        "atom_id": "agendar_recordatorio",
        "title": "Tool agendar recordatorio de aplicación",
        "family": "self",
        "role": "tool",
        "tags": ["self:tools", "conversation:steps.agendar_recordatorio", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/tool-antonia-agendar-recordatorio.md",
        "body": "## Description\n\nAgenda un recordatorio semanal de aplicación cuando día y hora ya están confirmados.\n\n## Parameters\n\n- dia\n- hora\n- nombre",
        "summary": "Tool para programar un recordatorio semanal.",
        "schema": {
            "name": "agendar_recordatorio",
            "parameters": {
                "type": "object",
                "properties": {
                    "dia": {"type": "string"},
                    "hora": {"type": "string"},
                    "nombre": {"type": "string"},
                },
                "required": ["dia", "hora"],
            },
        },
    },
    "tool-antonia-derivacion-medinfo": {
        "atom_id": "tool-antonia-derivacion-medinfo",
        "title": "Tool derivación a soporte",
        "family": "self",
        "role": "tool",
        "tags": ["self:tools", "conversation:handoff", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/tool-antonia-derivacion-medinfo.md",
        "body": "## Description\n\nEscala el caso a un profesional del programa cuando hay dudas clínicas o seguridad.",
        "summary": "Tool de handoff a soporte humano.",
        "schema": {
            "name": "derivar_a_soporte",
            "parameters": {
                "type": "object",
                "properties": {
                    "motivo": {"type": "string"},
                    "urgencia": {"type": "string"},
                },
                "required": ["motivo"],
            },
        },
    },
    "tool-antonia-registrar-evento": {
        "atom_id": "tool-antonia-registrar-evento",
        "title": "Tool registrar evento adverso",
        "family": "self",
        "role": "tool",
        "tags": ["self:tools", "conversation:pharmacovigilance", "system:laboratorio-chile"],
        "five_wh_one_plus": None,
        "path": "knowledge/atoms/tool-antonia-registrar-evento.md",
        "body": "## Description\n\nRegistra un reporte textual para revisión posterior de farmacovigilancia.",
        "summary": "Tool para registrar un posible evento adverso.",
        "schema": {
            "name": "registrar_evento_adverso",
            "parameters": {
                "type": "object",
                "properties": {
                    "descripcion": {"type": "string"},
                    "severidad": {"type": "string"},
                },
                "required": ["descripcion"],
            },
        },
    },
}

DEMO_TOOLS = [
    {
        "tool_id": "agendar_recordatorio",
        "name": "agendar_recordatorio",
        "description": "Agenda un recordatorio semanal de aplicación.",
        "schema": deepcopy(DEMO_ATOMS["agendar_recordatorio"]["schema"]),
        "tags": DEMO_ATOMS["agendar_recordatorio"]["tags"],
    },
    {
        "tool_id": "tool-antonia-derivacion-medinfo",
        "name": "derivar_a_soporte",
        "description": "Deriva el caso a un profesional del programa.",
        "schema": deepcopy(DEMO_ATOMS["tool-antonia-derivacion-medinfo"]["schema"]),
        "tags": DEMO_ATOMS["tool-antonia-derivacion-medinfo"]["tags"],
    },
    {
        "tool_id": "tool-antonia-registrar-evento",
        "name": "registrar_evento_adverso",
        "description": "Registra un posible evento adverso para revisión.",
        "schema": deepcopy(DEMO_ATOMS["tool-antonia-registrar-evento"]["schema"]),
        "tags": DEMO_ATOMS["tool-antonia-registrar-evento"]["tags"],
    },
]

DEMO_FLOW = {
    "nodes": [
        {
            "id": "bienvenida",
            "title": "Bienvenida",
            "kind": "interaccion_simple",
            "instructions": "Saludar y ubicar rápidamente el motivo principal.",
            "required_slots": [],
            "handout_target": "",
            "tool_ref": "",
            "tool_params": [],
            "allowed_transitions": ["consulta"],
            "grounding_atoms": ["self-antonia", "style-antonia", "step-antonia-saludo"],
            "completion_condition": "La persona expresa su motivo inicial.",
        },
        {
            "id": "consulta",
            "title": "Consulta",
            "kind": "interaccion_simple",
            "instructions": "Detectar si es duda práctica, ansiedad, recordatorio o seguridad.",
            "required_slots": [],
            "handout_target": "",
            "tool_ref": "",
            "tool_params": [],
            "allowed_transitions": ["obtencion_datos", "despedida"],
            "grounding_atoms": ["atom-antonia-aplicacion", "rule-antonia-eventos-adversos", "step-antonia-registro-estado"],
            "completion_condition": "La intención queda clasificada.",
        },
        {
            "id": "obtencion_datos",
            "title": "Obtención de datos",
            "kind": "obtencion_datos",
            "instructions": "Pedir día y hora del recordatorio antes de usar la tool.",
            "required_slots": ["dia", "hora"],
            "handout_target": "",
            "tool_ref": "agendar_recordatorio",
            "tool_params": ["dia", "hora", "nombre"],
            "allowed_transitions": ["tool", "consulta"],
            "grounding_atoms": ["rule-antonia-no-deducir", "step-antonia-agendar-recordatorio"],
            "completion_condition": "Se cuenta con día y hora confirmados.",
        },
        {
            "id": "tool",
            "title": "Llamado a tool",
            "kind": "llamado_tool",
            "instructions": "Ejecutar la tool con argumentos confirmados y resumir la acción.",
            "required_slots": [],
            "handout_target": "",
            "tool_ref": "agendar_recordatorio",
            "tool_params": ["dia", "hora", "nombre"],
            "allowed_transitions": ["despedida"],
            "grounding_atoms": ["agendar_recordatorio"],
            "completion_condition": "La acción queda confirmada al usuario.",
        },
        {
            "id": "despedida",
            "title": "Despedida",
            "kind": "handout",
            "instructions": "Cerrar, resumir y dejar claro el siguiente paso o derivación.",
            "required_slots": [],
            "handout_target": "equipo PSP",
            "tool_ref": "",
            "tool_params": [],
            "allowed_transitions": [],
            "grounding_atoms": ["step-antonia-despedida"],
            "completion_condition": "Turno finalizado.",
        },
    ],
    "edges": [
        {"source": "bienvenida", "target": "consulta"},
        {"source": "consulta", "target": "obtencion_datos"},
        {"source": "consulta", "target": "despedida"},
        {"source": "obtencion_datos", "target": "tool"},
        {"source": "obtencion_datos", "target": "consulta"},
        {"source": "tool", "target": "despedida"},
    ],
}


def _tax_atom(atom_id: str) -> dict[str, Any]:
    atom = DEMO_ATOMS[atom_id]
    return {
        "id": atom["atom_id"],
        "title": atom["title"],
        "atom_type": atom["role"],
        "summary": atom["summary"],
        "five_wh_one_plus": atom.get("five_wh_one_plus"),
        "tags": atom.get("tags", []),
    }


DEMO_TAXONOMY = {
    "self": {
        "label": "self",
        "children": [
            {
                "name": "whoami",
                "path": "self.whoami",
                "atoms": [_tax_atom("self-antonia")],
                "children": [],
            },
            {
                "name": "tools",
                "path": "self.tools",
                "atoms": [_tax_atom("agendar_recordatorio"), _tax_atom("tool-antonia-derivacion-medinfo")],
                "children": [],
            },
        ],
        "orphans": [_tax_atom("style-antonia")],
    },
    "domain": {
        "label": "domain",
        "children": [
            {
                "name": "tratamiento",
                "path": "domain.tratamiento",
                "atoms": [_tax_atom("atom-antonia-aplicacion")],
                "children": [
                    {
                        "name": "primeras_semanas",
                        "path": "domain.tratamiento.primeras_semanas",
                        "atoms": [_tax_atom("atom-antonia-primeras-semanas")],
                        "children": [],
                    }
                ],
            },
            {
                "name": "seguridad",
                "path": "domain.seguridad",
                "atoms": [_tax_atom("rule-antonia-eventos-adversos"), _tax_atom("rule-antonia-no-deducir")],
                "children": [],
            },
        ],
        "orphans": [],
    },
    "conversation": {
        "label": "conversation",
        "children": [
            {
                "name": "steps",
                "path": "conversation.steps",
                "atoms": [_tax_atom("step-antonia-saludo"), _tax_atom("step-antonia-registro-estado")],
                "children": [
                    {
                        "name": "tooling",
                        "path": "conversation.steps.tooling",
                        "atoms": [_tax_atom("step-antonia-agendar-recordatorio"), _tax_atom("step-antonia-despedida")],
                        "children": [],
                    }
                ],
            }
        ],
        "orphans": [],
    },
    "user": {
        "label": "user",
        "children": [
            {
                "name": "traits",
                "path": "user.traits",
                "atoms": [_tax_atom("trait-antonia-ansioso-aplicacion"), _tax_atom("trait-antonia-prefiere-recordatorios")],
                "children": [
                    {
                        "name": "journey",
                        "path": "user.traits.journey",
                        "atoms": [_tax_atom("trait-antonia-primera-vez")],
                        "children": [],
                    }
                ],
            }
        ],
        "orphans": [],
    },
    "gate": {"label": "gate", "children": [], "orphans": []},
}


TRAIT_FICHAS = {
    atom_id: {
        "id": atom["atom_id"],
        "title": atom["title"],
        "description": atom["summary"],
        "category": atom.get("category", "general"),
        "tags": atom.get("tags", []),
    }
    for atom_id, atom in DEMO_ATOMS.items()
    if atom.get("family") == "user"
}

BASE_TS = datetime(2026, 8, 20, 9, 0, 0)

DEMO_USERS = [
    {
        "user_id": 101,
        "external_id": "demo:maria",
        "channel": "whatsapp",
        "traits": [
            {"trait_id": "trait-antonia-ansioso-aplicacion", "confidence": 0.93, "source": "extractor", "created_at": (BASE_TS + timedelta(days=1)).isoformat()},
            {"trait_id": "trait-antonia-primera-vez", "confidence": 0.86, "source": "extractor", "created_at": (BASE_TS + timedelta(days=2)).isoformat()},
        ],
        "events": [
            {"timestamp": (BASE_TS + timedelta(days=1)).isoformat(), "kind": "chat", "label": "Consulta por primera aplicación"},
            {"timestamp": (BASE_TS + timedelta(days=2)).isoformat(), "kind": "trait", "label": "Ansiedad detectada", "confidence": 0.93},
            {"timestamp": (BASE_TS + timedelta(days=3)).isoformat(), "kind": "tool", "label": "Recordatorio agendado lunes 20:00"},
        ],
        "conversations": [
            {"session_id": "demo-maria-1", "created_at": (BASE_TS + timedelta(days=1)).isoformat(), "summary": "Preguntó por dolor y primera aplicación.", "n_turns": 4, "result": "guided"},
            {"session_id": "demo-maria-2", "created_at": (BASE_TS + timedelta(days=3)).isoformat(), "summary": "Agendó recordatorio semanal.", "n_turns": 3, "result": "tool_call"},
        ],
        "history": [
            {"role": "user", "content": "Hola, mañana me toca la primera aplicación y estoy nerviosa.", "created_at": (BASE_TS + timedelta(days=1)).isoformat()},
            {"role": "assistant", "content": "Es normal sentir nervios. Podemos repasarlo paso a paso.", "created_at": (BASE_TS + timedelta(days=1, minutes=1)).isoformat()},
        ],
    },
    {
        "user_id": 102,
        "external_id": "demo:carlos",
        "channel": "web",
        "traits": [
            {"trait_id": "trait-antonia-prefiere-recordatorios", "confidence": 0.91, "source": "extractor", "created_at": (BASE_TS + timedelta(days=4)).isoformat()},
        ],
        "events": [
            {"timestamp": (BASE_TS + timedelta(days=4)).isoformat(), "kind": "chat", "label": "Solicitó recordatorio de adherencia"},
            {"timestamp": (BASE_TS + timedelta(days=5)).isoformat(), "kind": "tool", "label": "Recordatorio agendado jueves 09:30"},
        ],
        "conversations": [
            {"session_id": "demo-carlos-1", "created_at": (BASE_TS + timedelta(days=4)).isoformat(), "summary": "Quería automatizar su recordatorio.", "n_turns": 3, "result": "tool_call"},
        ],
        "history": [
            {"role": "user", "content": "Necesito un recordatorio para los jueves a las 9:30.", "created_at": (BASE_TS + timedelta(days=4)).isoformat()},
            {"role": "assistant", "content": "Perfecto, lo dejo listo para los jueves a las 09:30.", "created_at": (BASE_TS + timedelta(days=4, minutes=1)).isoformat()},
        ],
    },
    {
        "user_id": 103,
        "external_id": "demo:sofia",
        "channel": "whatsapp",
        "traits": [
            {"trait_id": "trait-antonia-primera-vez", "confidence": 0.84, "source": "extractor", "created_at": (BASE_TS + timedelta(days=6)).isoformat()},
        ],
        "events": [
            {"timestamp": (BASE_TS + timedelta(days=6)).isoformat(), "kind": "chat", "label": "Preguntó por conservación del producto"},
            {"timestamp": (BASE_TS + timedelta(days=7)).isoformat(), "kind": "chat", "label": "Volvió a consultar por aplicación semanal"},
        ],
        "conversations": [
            {"session_id": "demo-sofia-1", "created_at": (BASE_TS + timedelta(days=6)).isoformat(), "summary": "Consultó por conservación y horario estable.", "n_turns": 2, "result": "guided"},
        ],
        "history": [
            {"role": "user", "content": "¿Cómo guardo el medicamento?", "created_at": (BASE_TS + timedelta(days=6)).isoformat()},
            {"role": "assistant", "content": "Debe mantenerse según la indicación del programa y en refrigeración cuando corresponda.", "created_at": (BASE_TS + timedelta(days=6, minutes=1)).isoformat()},
        ],
    },
    {
        "user_id": 104,
        "external_id": "demo:jorge",
        "channel": "web",
        "traits": [
            {"trait_id": "trait-antonia-ansioso-aplicacion", "confidence": 0.74, "source": "extractor", "created_at": (BASE_TS + timedelta(days=8)).isoformat()},
            {"trait_id": "trait-antonia-prefiere-recordatorios", "confidence": 0.67, "source": "extractor", "created_at": (BASE_TS + timedelta(days=9)).isoformat()},
        ],
        "events": [
            {"timestamp": (BASE_TS + timedelta(days=8)).isoformat(), "kind": "chat", "label": "Mencionó mareos y dolor estomacal"},
            {"timestamp": (BASE_TS + timedelta(days=8, minutes=5)).isoformat(), "kind": "handoff", "label": "Derivación a soporte del programa"},
        ],
        "conversations": [
            {"session_id": "demo-jorge-1", "created_at": (BASE_TS + timedelta(days=8)).isoformat(), "summary": "Se detectó posible evento adverso.", "n_turns": 2, "result": "handoff"},
        ],
        "history": [
            {"role": "user", "content": "Me mareé y tuve dolor de estómago fuerte después de aplicármelo.", "created_at": (BASE_TS + timedelta(days=8)).isoformat()},
            {"role": "assistant", "content": "Gracias por contarlo. Lo revisará un profesional del programa y, si es urgente, contacta a tu médico o urgencias.", "created_at": (BASE_TS + timedelta(days=8, minutes=1)).isoformat()},
        ],
    },
]


def demo_health() -> dict[str, str]:
    return {"status": "ok"}


def demo_config() -> dict[str, Any]:
    return deepcopy(DEMO_CONFIG)


def demo_flow() -> dict[str, Any]:
    return deepcopy(DEMO_FLOW)


def demo_taxonomy() -> dict[str, Any]:
    return deepcopy(DEMO_TAXONOMY)


def demo_tools() -> list[dict[str, Any]]:
    return deepcopy(DEMO_TOOLS)


def demo_atom(atom_id: str) -> dict[str, Any] | None:
    atom = DEMO_ATOMS.get(atom_id)
    return deepcopy(atom) if atom else None


def demo_profiles_payload() -> dict[str, Any]:
    users = []
    for user in DEMO_USERS:
        users.append(
            {
                "user_id": user["user_id"],
                "external_id": user["external_id"],
                "channel": user["channel"],
                "traits": deepcopy(user["traits"]),
                "traits_count": len(user["traits"]),
                "total_turns": sum(conv.get("n_turns", 0) for conv in user["conversations"]),
                "last_active": user["events"][-1]["timestamp"] if user["events"] else None,
                "created_at": user["events"][0]["timestamp"] if user["events"] else None,
                "conversations": deepcopy(user["conversations"]),
                "events": deepcopy(user["events"]),
            }
        )
    return {"users": users, "fichas": deepcopy(TRAIT_FICHAS), "missing_fichas": []}


def demo_events(user_id: int | None) -> dict[str, Any]:
    if user_id is None:
        return {"events": []}
    user = next((u for u in DEMO_USERS if u["user_id"] == user_id), None)
    return {"user_id": user_id, "events": deepcopy(user["events"] if user else [])}


def demo_history(external_id: str) -> dict[str, Any]:
    user = next((u for u in DEMO_USERS if u["external_id"] == external_id), None)
    return {"external_id": external_id, "messages": deepcopy(user["history"] if user else [])}


def demo_viz_graph() -> dict[str, Any]:
    positions = {
        "self-antonia": (-620, -220),
        "style-antonia": (-540, -120),
        "agendar_recordatorio": (-560, 40),
        "tool-antonia-derivacion-medinfo": (-510, 130),
        "atom-antonia-aplicacion": (-40, -170),
        "atom-antonia-primeras-semanas": (50, -70),
        "rule-antonia-eventos-adversos": (120, 90),
        "rule-antonia-no-deducir": (-120, 120),
        "step-antonia-saludo": (420, -170),
        "step-antonia-registro-estado": (520, -40),
        "step-antonia-agendar-recordatorio": (610, 80),
        "step-antonia-despedida": (740, 180),
        "trait-antonia-ansioso-aplicacion": (180, 320),
        "trait-antonia-prefiere-recordatorios": (40, 350),
        "trait-antonia-primera-vez": (300, 410),
    }
    nodes = []
    for atom_id, atom in DEMO_ATOMS.items():
        if atom_id not in positions:
            continue
        x, y = positions[atom_id]
        nodes.append(
            {
                "id": atom_id,
                "label": atom["title"],
                "family": atom["family"],
                "position": {"x": x, "y": y},
                "tags": atom.get("tags", []),
            }
        )
    edges = [
        {"source": "self-antonia", "target": "step-antonia-saludo"},
        {"source": "style-antonia", "target": "step-antonia-saludo"},
        {"source": "atom-antonia-aplicacion", "target": "step-antonia-registro-estado"},
        {"source": "rule-antonia-no-deducir", "target": "step-antonia-agendar-recordatorio"},
        {"source": "agendar_recordatorio", "target": "step-antonia-agendar-recordatorio"},
        {"source": "rule-antonia-eventos-adversos", "target": "step-antonia-registro-estado"},
        {"source": "trait-antonia-ansioso-aplicacion", "target": "atom-antonia-aplicacion"},
    ]
    return {"kb": "Antonia", "nodes": nodes, "edges": edges}


DAY_RE = re.compile(r"\b(lunes|martes|miercoles|miércoles|jueves|viernes|sabado|sábado|domingo)\b", re.I)
HOUR_RE = re.compile(r"\b([01]?\d|2[0-3])(?::([0-5]\d))?\s*(am|pm|hs|h)?\b", re.I)


def normalize(text: str) -> str:
    return text.lower().strip()


def infer_intent(message: str) -> str:
    m = normalize(message)
    if any(k in m for k in ["mare", "náuse", "nause", "vomit", "dolor fuerte", "hinch", "reacción", "reaccion", "malestar"]):
        return "evento_adverso"
    if any(k in m for k in ["recordatorio", "recuérd", "recuerd", "agenda", "avis", "lunes", "martes", "miércoles", "miercoles", "jueves", "viernes", "sábado", "sabado", "domingo"]):
        return "recordatorio"
    if any(k in m for k in ["miedo", "nerv", "ans", "aguja", "duele"]):
        return "ansiedad"
    if any(k in m for k in ["aplic", "inyec", "conservar", "guardar", "selfix"]):
        return "aplicacion"
    if any(k in m for k in ["hola", "buenas", "buen día", "buen dia"]):
        return "saludo"
    return "fallback"


def extract_slots(message: str) -> dict[str, str]:
    out: dict[str, str] = {}
    md = DAY_RE.search(message)
    if md:
        out["dia"] = md.group(1).lower().replace("miércoles", "miercoles").replace("sábado", "sabado")
    mh = HOUR_RE.search(message)
    if mh:
        hour = int(mh.group(1))
        minute = mh.group(2) or "00"
        suffix = (mh.group(3) or "").lower()
        if suffix == "pm" and hour < 12:
            hour += 12
        if suffix == "am" and hour == 12:
            hour = 0
        out["hora"] = f"{hour:02d}:{minute}"
    return out


def next_flow_node(current: str | None, intent: str, slots: dict[str, str], *, tool_just_ran: bool = False) -> str:
    if tool_just_ran:
        return "tool"
    if current in (None, "bienvenida"):
        if intent == "recordatorio":
            return "obtencion_datos"
        return "consulta"
    if current == "consulta":
        if intent == "recordatorio":
            return "obtencion_datos"
        if intent == "evento_adverso":
            return "despedida"
        return "consulta"
    if current == "obtencion_datos":
        if slots.get("dia") and slots.get("hora"):
            return "tool"
        return "obtencion_datos"
    if current == "tool":
        return "despedida" if intent in {"saludo", "fallback", "aplicacion", "ansiedad", "recordatorio"} else "tool"
    return "despedida"


def demo_context_items(intent: str, flow_node: str, session: dict[str, Any], message: str) -> list[dict[str, Any]]:
    ids = ["self-antonia", "style-antonia"]
    if flow_node == "consulta":
        ids += ["step-antonia-registro-estado"]
    if flow_node == "obtencion_datos":
        ids += ["step-antonia-agendar-recordatorio", "rule-antonia-no-deducir", "agendar_recordatorio"]
    if flow_node == "tool":
        ids += ["agendar_recordatorio", "step-antonia-agendar-recordatorio"]
    if flow_node == "despedida":
        ids += ["step-antonia-despedida"]
    if intent == "aplicacion":
        ids += ["atom-antonia-aplicacion", "atom-antonia-primeras-semanas"]
    if intent == "ansiedad":
        ids += ["trait-antonia-ansioso-aplicacion", "atom-antonia-aplicacion"]
    if intent == "evento_adverso":
        ids += ["rule-antonia-eventos-adversos", "tool-antonia-derivacion-medinfo"]
    if intent == "recordatorio":
        ids += ["trait-antonia-prefiere-recordatorios", "agendar_recordatorio"]
    if not any(k in normalize(message) for k in ["hola", "buenas"]):
        ids += ["step-antonia-saludo"]

    ordered = []
    seen = set()
    for atom_id in ids:
        if atom_id in seen or atom_id not in DEMO_ATOMS:
            continue
        seen.add(atom_id)
        atom = DEMO_ATOMS[atom_id]
        motivo = {
            "self-antonia": "Entra por piso de seguridad: identidad base del agente.",
            "style-antonia": "Entra por piso de seguridad: estilo base de redacción.",
            "step-antonia-saludo": "grounding del step: ubica el turno en el flujo.",
            "step-antonia-registro-estado": "grounding del step activo de clasificación.",
            "step-antonia-agendar-recordatorio": "grounding del step activo de captura de slots.",
            "step-antonia-despedida": "grounding del step terminal de cierre.",
            "atom-antonia-aplicacion": "Entra por similitud con la consulta de aplicación.",
            "atom-antonia-primeras-semanas": "Entra por similitud: refuerzo de onboarding.",
            "rule-antonia-eventos-adversos": "Entra por similitud con señales de malestar o reacción.",
            "rule-antonia-no-deducir": "grounding: regla de integridad porque faltan slots.",
            "trait-antonia-ansioso-aplicacion": "trait del usuario activado por señales de ansiedad.",
            "trait-antonia-prefiere-recordatorios": "trait del usuario por preferencia de adherencia.",
            "agendar_recordatorio": "grounding: tool declarada y visible para el orquestador.",
            "tool-antonia-derivacion-medinfo": "Entra por similitud: capacidad de handoff por seguridad.",
        }.get(atom_id, "Documento relevante para el turno.")
        score = None if atom["family"] in {"self", "conversation", "user"} else 0.98 if intent != "fallback" else 0.42
        ordered.append(
            {
                "atom_id": atom["atom_id"],
                "title": atom["title"],
                "role": atom["role"],
                "family": atom["family"],
                "tags": deepcopy(atom.get("tags", [])),
                "motivo": motivo,
                "score": score,
                "grounds_step": atom["family"] in {"conversation", "domain"},
                "body": atom["body"],
            }
        )
    return ordered


def build_reply_text(intent: str, flow_node: str, session: dict[str, Any], message: str) -> str:
    slots = session.get("slots", {})
    if intent == "evento_adverso":
        return "Gracias por contarlo. Lo voy a dejar marcado para revisión del programa. No voy a interpretar la gravedad aquí; si esto es urgente, contacta a tu médico o a urgencias."
    if flow_node == "tool":
        return f"Listo: dejé un recordatorio semanal para **{slots.get('dia', 'el día indicado')}** a las **{slots.get('hora', 'la hora indicada')}**."
    if flow_node == "obtencion_datos":
        missing = [k for k in ["dia", "hora"] if not slots.get(k)]
        if missing == ["dia", "hora"]:
            return "Puedo dejarlo agendado. Decime **qué día** y **a qué hora** quieres el recordatorio semanal."
        if missing == ["hora"]:
            return f"Perfecto, tomo **{slots.get('dia')}**. Ahora dime **la hora** para dejar el recordatorio listo."
        if missing == ["dia"]:
            return f"Perfecto, tomo **{slots.get('hora')}**. Ahora dime **el día** para dejar el recordatorio listo."
    if intent == "ansiedad":
        return "Es normal sentir nervios con la aplicación. Podemos ir paso a paso: respira, prepara el material con calma y mantén un día y hora fijos para que se vuelva más predecible."
    if intent == "aplicacion":
        return "Selfix se aplica de forma **semanal**. Conviene sostener un día y hora estables, rotar el sitio de aplicación y conservarlo según la indicación del programa."
    if intent == "recordatorio":
        return "Te ayudo con eso. Para agendarlo bien necesito el **día** y la **hora** del recordatorio semanal."
    if flow_node == "despedida":
        return "Queda listo por ahora. Si te sirve, podemos retomar más tarde con otra duda práctica del tratamiento."
    return "Puedo ayudarte con aplicación, recordatorios y derivación a soporte del programa."
