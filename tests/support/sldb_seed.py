"""Seed de stores SLDB tipados para tests (helper unico, antes duplicado en 4 archivos).

Uso::

    root = seed_store(tmp_path / "kb", atoms=[
        {"type": "domain", "id": "domain-menu", "title": "Menu",
         "tags": ["domain:catalogo"], "five_wh": "what",
         "fields": {"answer": "La margarita cuesta 10."}},
        {"type": "tool", "id": "tool-reserva", "title": "Reserva",
         "tags": ["self:tools"],
         "fields": {"description": "Crea una reserva.",
                    "parameters": '{"name": "crear_reserva", "parameters": {...}}'}},
    ])
    reader = KnowledgeOperations(kb_root=root)

Cada atom se escribe como markdown segun el template de su modelo tipado
(``kb_agent.models.knowledge``) y se trackea con el CLI real de ``sldb``.
"""
from __future__ import annotations

import hashlib
import os
import random
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL_BY_TYPE: dict[str, str] = {
    "self": "SelfDeclaration",
    "style": "StyleGuide",
    "boundary": "CapabilityBoundary",
    "strategy": "StrategyRule",
    "fallback": "FallbackRule",
    "domain": "DomainAtom",
    "rule": "RuleAtom",
    "tool": "ToolAtom",
    "trait": "TraitAtom",
    "step": "ConversationStep",
    "gate": "GateCriterion",
}

SECTION_TITLES: dict[str, str] = {
    "statement": "Statement",
    "tone": "Tone",
    "language_register": "Language Register",
    "phrase_preferences": "Phrase Preferences",
    "length_guidelines": "Length Guidelines",
    "fallback_message": "Fallback Message",
    "conditions": "Conditions",
    "answer": "Answer",
    "description": "Description",
    "parameters": "Parameters",
    "restriction": "Restriction",
    "escalation": "Escalation",
    "goal": "Goal",
    "approach": "Approach",
    "priorities": "Priorities",
    "instructions": "Instructions",
    "required_slots": "Required Slots",
    "handout_target": "Handout Target",
    "tool_ref": "Tool",
    "allowed_transitions": "Allowed Transitions",
    "grounding_atoms": "Grounding Atoms",
    "completion_condition": "Completion Condition",
    "criterion": "Criterion",
    "approval_condition": "Approval Condition",
    "rejection_action": "Rejection Action",
}


def run_sldb(*args: str, cwd: Path | None = None) -> str:
    """Ejecuta el CLI real ``sldb`` con el repo en PYTHONPATH."""
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPO_ROOT) if not pythonpath else f"{REPO_ROOT}{os.pathsep}{pythonpath}"
    proc = subprocess.run(
        ["sldb", *args],
        check=True,
        cwd=str(cwd or REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.stdout


EMBED_DIM = 768


def hash_vector(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Vector pseudo-aleatorio estable derivado del texto (sha256 -> semilla).
    Textos distintos dan vectores distintos y ~ortogonales. Es el mismo doble
    que usa ``tests.support.fakes.FakeEmbedder`` para embeder queries."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) & 0xFFFFFFFF
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(dim)]


def fake_embedding(atom: dict[str, Any]) -> list[float]:
    """Embedding determinista con ESTRUCTURA: 0.8 * vector del namespace del primer
    tag + 0.6 * vector del id. Dos atoms del mismo namespace (``domain:*``,
    ``self:*``...) quedan a coseno ~0.64 (por sobre el umbral de aristas del
    visualizador, 0.55) y atoms de namespaces distintos ~0. Asi la KB de prueba
    tiene un grafo semantico con aristas sin cargar un modelo real."""
    tags = atom.get("tags") or []
    namespace = str(tags[0]).split(":", 1)[0] if tags else "none"
    a, b = hash_vector(namespace), hash_vector(str(atom["id"]))
    return [round(0.8 * x + 0.6 * y, 6) for x, y in zip(a, b)]


def atom_markdown(atom: dict[str, Any]) -> str:
    tipo = str(atom["type"])
    tags = "\n".join(f"- {tag}" for tag in atom.get("tags", []))
    lines = ["---", f"id: {atom['id']}", f"title: {atom['title']}"]
    lines.append(f"summary: {atom.get('summary') or atom['title']}")
    if atom.get("embedding"):
        lines.append("embedding:")
        lines += [f"- {v}" for v in atom["embedding"]]
    if atom.get("five_wh"):
        lines.append(f"five_wh_one_plus: {atom['five_wh']}")
    lines.append(f"atom_type: {tipo}")
    if tipo == "step":
        lines.append(f"kind: {atom.get('kind', 'interaccion_simple')}")
    lines.append("tags:")
    if tags:
        lines.append(tags)
    else:
        lines[-1] = "tags: []"
    if tipo in {"domain", "step"}:
        lines.append(f"domain_ref: {atom.get('domain_ref', 'negocio')}")
    if tipo == "rule":
        lines.append(f"applies_to: {atom.get('applies_to', 'negocio')}")
    if tipo == "trait":
        lines.append(f"category: {atom.get('category', 'general')}")
    if tipo != "step":
        lines.append("provenance: null")
    lines += ["---", "", f"# {atom['title']}", ""]
    fields: dict[str, Any] = atom.get("fields", {})
    for field, value in fields.items():
        lines.append(f"## {SECTION_TITLES.get(field, field.replace('_', ' ').title())}")
        lines.append("")
        if tipo == "tool" and field == "parameters":
            lines += ["```json", str(value), "```"]
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines)


DEFAULT_NAMESPACES_REGISTRY = """namespaces:
  domain:
    meaning: Problem domain or durable area of concern.
    use_when: The atom belongs to a reusable problem domain.
    do_not_use_when: A more specific tag applies.
    examples:
      - domain:knowledge-management
  layer:
    meaning: Architectural layer where the atom applies.
    use_when: The atom is scoped to a layer of the system.
    do_not_use_when: The tag names only a broad topic or system.
    examples:
      - layer:runtime
  source:
    meaning: Provenance channel or producer that originated the atom draft.
    use_when: The atom is machine-generated and needs source attribution.
    do_not_use_when: The tag expresses the atom subject instead of origin.
    examples:
      - source:reflector
  system:
    meaning: System, project, or tool the atom belongs to.
    use_when: The atom is about a specific system.
    do_not_use_when: The tag is only a general topic.
    examples:
      - system:deskops
  topic:
    meaning: Subject area discussed by the atom.
    use_when: The atom is about a conceptual topic.
    do_not_use_when: The atom describes a reusable implementation shape.
    examples:
      - topic:ontology
      - topic:rules
  conversation:
    meaning: Step or moment of a conversational flow.
    use_when: The atom describes or grounds a conversation step.
    do_not_use_when: The tag is not about the conversation flow.
    examples:
      - conversation:steps.booking
  self:
    meaning: The assistant's own identity, capabilities, or configuration.
    use_when: The atom is about the assistant itself.
    do_not_use_when: The tag is about the business domain instead.
    examples:
      - self:whoami
"""


def seed_store(
    root: Path,
    atoms: list[dict[str, Any]],
    *,
    store_name: str = ".sldb",
    namespaces_registry: str | None = None,
    embed: bool = False,
) -> Path:
    """Crea un store SLDB en ``root`` con los atoms tipados dados. Devuelve ``root``.

    ``embed=True`` escribe en cada atom un embedding determinista con estructura
    (ver ``fake_embedding``), para tests que necesitan vectores sin modelo real.

    ``namespaces_registry`` (opcional): si se entrega, se escribe como
    ``<root>/desk/atoms/tag-namespaces.yaml`` -- requerido por validaciones
    que consultan el registro de namespaces de tags (p.ej. el Reflector).
    Pase ``DEFAULT_NAMESPACES_REGISTRY`` para un registro minimo ya cubierto,
    o un YAML propio si el test necesita otros namespaces.
    """
    root.mkdir(parents=True, exist_ok=True)
    if namespaces_registry is not None:
        namespaces_dir = root / "desk" / "atoms"
        namespaces_dir.mkdir(parents=True, exist_ok=True)
        (namespaces_dir / "tag-namespaces.yaml").write_text(namespaces_registry, encoding="utf-8")
    run_sldb("stores", "init", "--path", str(root))
    store = root / ".sldb"
    if store_name != ".sldb":
        os.rename(store, root / store_name)
        store = root / store_name

    registered: set[str] = set()
    for atom in atoms:
        tipo = str(atom["type"])
        model = MODEL_BY_TYPE[tipo]
        if tipo not in registered:
            run_sldb(
                "models", "add", f"kb_agent.models.knowledge:{model}",
                "--store", str(store), "--pythonpath", str(REPO_ROOT),
            )
            registered.add(tipo)

        if embed and not atom.get("embedding"):
            atom = dict(atom, embedding=fake_embedding(atom))
        out_path = root / "atoms" / f"{atom['id']}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(atom_markdown(atom), encoding="utf-8")
        run_sldb(
            "docs", "track", str(out_path.resolve()),
            "--model", model, "--store", str(store), "--pythonpath", str(REPO_ROOT),
        )

    run_sldb("stores", "update", "--store", str(store), "--pythonpath", str(REPO_ROOT))
    return root


# ── un negocio minimo completo (reutilizable) ─────────────────────────────────

def minimal_business_atoms(*, with_fallback: bool = True, with_tool: bool = True) -> list[dict[str, Any]]:
    atoms: list[dict[str, Any]] = [
        {
            "type": "self", "id": "self-negocio", "title": "Asistente",
            "tags": ["self:whoami", "system:negocio"],
            "fields": {"statement": "Soy el asistente de la pizzeria."},
        },
        {
            "type": "style", "id": "style-negocio", "title": "Estilo",
            "tags": ["self:estilo", "system:negocio"],
            "fields": {
                "tone": "Responde breve y amable.",
                "language_register": "Español chileno, trato de tú.",
                "phrase_preferences": "Frases cortas.",
                "length_guidelines": "Bajo 300 caracteres.",
            },
        },
        {
            "type": "domain", "id": "domain-menu", "title": "Domain Menu",
            "tags": ["domain:catalogo", "system:negocio"], "five_wh": "what",
            "fields": {"answer": "Pizza margarita 8900. Pizza cuatro quesos 9900."},
        },
        {
            "type": "domain", "id": "domain-horarios", "title": "Domain Horarios",
            "tags": ["domain:horarios", "system:negocio"], "five_wh": "when",
            "fields": {"answer": "Atendemos de 12:00 a 23:00."},
        },
        {
            "type": "rule", "id": "rule-reservas", "title": "Regla Reservas",
            "tags": ["domain:reglas.reservas", "system:negocio"], "five_wh": "how",
            "fields": {"answer": "Las reservas requieren confirmación previa.", "conditions": "Aplica al reservar mesa."},
        },
    ]
    if with_fallback:
        atoms.append({
            "type": "fallback", "id": "fallback-negocio", "title": "Fallback",
            "tags": ["conversation:fallback", "system:negocio"],
            "fields": {"fallback_message": "Si no hay contexto suficiente, pide una aclaración.", "conditions": "Cuando falta contexto."},
        })
    if with_tool:
        atoms.append({
            "type": "tool", "id": "tool-reserva", "title": "Tool Reserva",
            "tags": ["self:tools", "conversation:steps.booking", "system:negocio"],
            "fields": {
                "description": "Crea una reserva.",
                "parameters": '{"name": "crear_reserva", "parameters": {"type": "object", "properties": {"fecha": {"type": "string"}}, "required": ["fecha"]}}',
            },
        })
    return atoms


def test_business_atoms() -> list[dict[str, Any]]:
    """El negocio de prueba del repo (``test_kb_root``): el minimo mas un diagrama de
    conversacion de dos pasos (onboarding <-> booking), traits, estrategia y limites.
    Contenido generico de una pizzeria; no es ninguna KB real."""
    atoms = minimal_business_atoms()
    for atom in atoms:
        if atom["id"] == "domain-menu":
            atom["tags"].insert(1, "conversation:steps.onboarding")
        if atom["id"] == "rule-reservas":
            atom["tags"].insert(1, "conversation:steps.booking")
        if atom["id"] == "tool-reserva":
            atom["tags"] = ["self:tools", "domain:pizzeria", "conversation:steps.booking", "system:negocio"]
            atom["fields"]["description"] = (
                "Crea una reserva de mesa. Llamar solo con fecha, hora y cantidad de personas confirmados."
            )
            atom["fields"]["parameters"] = (
                '{"name": "crear_reserva", "parameters": {"type": "object", "properties": '
                '{"fecha": {"type": "string"}, "hora": {"type": "string"}, "personas": {"type": "integer"}, '
                '"nombre": {"type": "string"}}, "required": ["fecha", "hora", "personas"]}}'
            )
    atoms += [
        {
            "type": "domain", "id": "domain-promos", "title": "Domain Promos",
            "tags": ["domain:promociones", "conversation:steps.booking", "system:negocio"], "five_wh": "what",
            "fields": {"answer": "Martes y miércoles: 2x1 en pizzas margarita. Las promociones no son acumulables."},
        },
        {
            "type": "domain", "id": "domain-ubicacion", "title": "Domain Ubicacion",
            "tags": ["domain:ubicacion", "system:negocio"], "five_wh": "where",
            "fields": {"answer": "Estamos en Avenida Principal 123."},
        },
        {
            "type": "strategy", "id": "strategy-negocio", "title": "Estrategia",
            "tags": ["conversation:strategy", "system:negocio"],
            "fields": {
                "goal": "Resolver la consulta de la persona y facilitar reservas de mesa cuando lo pida.",
                "approach": "Responder primero lo que la persona pregunto con datos de la base.",
                "priorities": "Exactitud, brevedad, reserva cuando hay intencion.",
            },
        },
        {
            "type": "boundary", "id": "boundary-negocio", "title": "Limites",
            "tags": ["self:limites", "system:negocio"],
            "fields": {
                "restriction": "No invento datos que no esten en la base. No proceso pagos.",
                "conditions": "",
                "escalation": "Derivar al local para lo que no puedo resolver.",
            },
        },
        {
            "type": "trait", "id": "trait-vegetariano", "title": "Cliente vegetariano",
            "tags": ["user:traits.vegetariano", "system:negocio"], "category": "dietary",
            "fields": {"description": "La persona es vegetariana: no consume carne. Priorizar pizzas sin carne."},
        },
        {
            "type": "trait", "id": "trait-sin-gluten", "title": "Cliente sin gluten",
            "tags": ["user:traits.sin_gluten", "system:negocio"], "category": "dietary",
            "fields": {"description": "La persona evita el gluten. Ofrecer masa sin gluten."},
        },
        {
            "type": "step", "id": "step-onboarding", "title": "Onboarding — atencion general",
            "kind": "interaccion_simple",
            "tags": ["conversation:steps.onboarding", "system:negocio"],
            "fields": {
                "instructions": "Saludar una vez, responder consultas de menu, horarios, ubicacion y promociones; pasar a reserva si hay intencion.",
                "required_slots": "consulta de la persona",
                "handout_target": "no aplica",
                "tool_ref": "no aplica",
                "allowed_transitions": "conversation:steps.booking",
                "grounding_atoms": "domain-menu, domain-horarios, domain-ubicacion, domain-promos, self-negocio",
                "completion_condition": "La persona recibio respuesta, o expreso intencion de reservar.",
            },
        },
        {
            "type": "step", "id": "step-booking", "title": "Reserva de mesa",
            "kind": "llamado_tool",
            "tags": ["conversation:steps.booking", "system:negocio"],
            "fields": {
                "instructions": "Recolectar fecha, hora y cantidad de personas una pregunta a la vez, confirmar y ejecutar la tool crear_reserva.",
                "required_slots": "fecha, hora, personas, nombre",
                "handout_target": "no aplica",
                "tool_ref": "crear_reserva",
                "allowed_transitions": "conversation:steps.onboarding",
                "grounding_atoms": "rule-reservas, domain-promos, tool-reserva",
                "completion_condition": "La reserva fue creada con la tool, o la persona decide no continuar.",
            },
        },
    ]
    return atoms
