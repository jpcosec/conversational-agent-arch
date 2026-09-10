"""KnowledgeOperations: acceso del runtime al store, por modelo tipado.

Este modulo era ``test_sldb_reader.py``. ``SLDBReader`` vivia en
``kb_agent/knowledge/`` y reimplementaba, con match por substring, lo que
``KnowledgeOperations`` ya hacia sobre el MISMO store. Ahora hay un solo dueno
del acceso a la KB y estos tests cubren su contrato de runtime.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from knowledge_base.operations import KnowledgeOperations
from tests.support.sldb_seed import seed_store

CLINICA = [
    {
        "type": "tool", "id": "atom-tool-calendar", "title": "Calendar Tool", "tags": ["self:tools", "channel:calendar"],
        "fields": {"description": "Agenda una cita.", "parameters": '{"name": "calendar", "parameters": {"type": "object", "properties": {"date": {"type": "string"}}, "required": ["date"]}}'},
    },
    {
        "type": "rule", "id": "atom-rule-cancelacion", "title": "Rule Cancelacion", "tags": ["domain:reglas.cancelacion", "system:clinica"], "five_wh": "how",
        "fields": {"answer": "Cancelar con menos de 24h requiere penalidad.", "conditions": "Al cancelar."},
    },
    {
        "type": "domain", "id": "atom-domain-horarios", "title": "Domain Horarios", "tags": ["domain:horarios", "system:clinica"], "five_wh": "when",
        "fields": {"answer": "Lunes a viernes de 09:00 a 18:00."},
    },
    {
        "type": "trait", "id": "trait-paciente-frecuente", "title": "Trait Paciente Frecuente", "tags": ["user:traits.frecuente", "system:clinica"], "category": "loyalty",
        "fields": {"description": "Ofrecer descuento por recurrencia."},
    },
]
METEO = [
    {
        "type": "tool", "id": "atom-tool-weather", "title": "Weather Tool", "tags": ["self:tools", "channel:weather"],
        "fields": {"description": "Consulta el clima.", "parameters": '{"name": "weather", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}'},
    },
    {"type": "domain", "id": "atom-domain-clima", "title": "Domain Clima", "tags": ["domain:clima", "system:meteo"], "five_wh": "what", "fields": {"answer": "Pronóstico por ciudad."}},
]


@pytest.fixture(scope="module")
def roots(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    base = tmp_path_factory.mktemp("kbs")
    return seed_store(base / "clinica", CLINICA), seed_store(base / "meteo", METEO)


def test_fetch_tool_returns_only_tool_atoms_with_schema(roots: tuple[Path, Path]) -> None:
    atoms = KnowledgeOperations(kb_root=roots[0]).docs_by_type("tool")
    assert [a["id"] for a in atoms] == ["atom-tool-calendar"]
    assert '"name": "calendar"' in atoms[0]["parameters"]


def test_two_kb_roots_isolate_businesses(roots: tuple[Path, Path]) -> None:
    ids_a = {a["id"] for a in KnowledgeOperations(kb_root=roots[0]).docs_by_type("tool")}
    ids_b = {a["id"] for a in KnowledgeOperations(kb_root=roots[1]).docs_by_type("tool")}
    assert (ids_a, ids_b) == ({"atom-tool-calendar"}, {"atom-tool-weather"})


@pytest.mark.parametrize("atom_type,expected_id", [
    ("rule", "atom-rule-cancelacion"),
    ("domain", "atom-domain-horarios"),
    ("trait", "trait-paciente-frecuente"),
])
def test_fetch_supports_all_declared_atom_types(roots: tuple[Path, Path], atom_type: str, expected_id: str) -> None:
    assert [a["id"] for a in KnowledgeOperations(kb_root=roots[0]).docs_by_type(atom_type)] == [expected_id]


def test_get_doc_returns_resolved_fields_and_tags(roots: tuple[Path, Path]) -> None:
    reader = KnowledgeOperations(kb_root=roots[0])
    doc = reader.doc("atom-rule-cancelacion")
    assert doc is not None
    assert doc["answer"] == "Cancelar con menos de 24h requiere penalidad."
    assert doc["conditions"] == "Al cancelar."
    assert "domain:reglas.cancelacion" in doc["tags"]
    assert doc["path"] and doc["path"].endswith("atom-rule-cancelacion.md")
    assert reader.doc("no-existe") is None


def test_find_by_semantic_tag_and_by_hierarchy_prefix(roots: tuple[Path, Path]) -> None:
    reader = KnowledgeOperations(kb_root=roots[0])
    assert [d["id"] for d in reader.docs_by_tag("domain:horarios")] == ["atom-domain-horarios"]
    assert {d["id"] for d in reader.docs_by_tag("system:clinica")} == {"atom-rule-cancelacion", "atom-domain-horarios", "trait-paciente-frecuente"}
    assert reader.docs_by_tag("domain:inexistente") == []
