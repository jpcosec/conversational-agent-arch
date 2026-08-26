"""SLDBReader: seleccion por modelo tipado sobre la libreria real de sldb."""
from __future__ import annotations

from pathlib import Path

import pytest

from kb_agent.ontologizador.sldb_reader import SLDBReader
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
    return seed_store(base / "clinica", CLINICA), seed_store(base / "meteo", METEO, store_name=".sldb_custom")


def test_fetch_tool_returns_only_tool_atoms_with_schema(roots: tuple[Path, Path]) -> None:
    atoms = SLDBReader(kb_root=roots[0]).fetch("tool")
    assert [a["id"] for a in atoms] == ["atom-tool-calendar"]
    assert '"name": "calendar"' in atoms[0]["parameters"]


def test_kb_root_and_store_name_swap_isolate_businesses(roots: tuple[Path, Path]) -> None:
    ids_a = {a["id"] for a in SLDBReader(kb_root=roots[0]).fetch("tool")}
    ids_b = {a["id"] for a in SLDBReader(kb_root=roots[1], store_name=".sldb_custom").fetch("tool")}
    assert (ids_a, ids_b) == ({"atom-tool-calendar"}, {"atom-tool-weather"})


@pytest.mark.parametrize("atom_type,expected_id", [
    ("rule", "atom-rule-cancelacion"),
    ("domain", "atom-domain-horarios"),
    ("trait", "trait-paciente-frecuente"),
])
def test_fetch_supports_all_declared_atom_types(roots: tuple[Path, Path], atom_type: str, expected_id: str) -> None:
    assert [a["id"] for a in SLDBReader(kb_root=roots[0]).fetch(atom_type)] == [expected_id]


def test_get_doc_returns_resolved_fields_and_tags(roots: tuple[Path, Path]) -> None:
    reader = SLDBReader(kb_root=roots[0])
    doc = reader.get_doc("atom-rule-cancelacion")
    assert doc is not None
    assert doc["answer"] == "Cancelar con menos de 24h requiere penalidad."
    assert doc["conditions"] == "Al cancelar."
    assert "domain:reglas.cancelacion" in doc["tags"]
    assert doc["path"] and doc["path"].endswith("atom-rule-cancelacion.md")
    assert reader.get_doc("no-existe") is None


def test_find_by_semantic_tag_and_by_hierarchy_prefix(roots: tuple[Path, Path]) -> None:
    reader = SLDBReader(kb_root=roots[0])
    assert [d["id"] for d in reader.find("domain:horarios")] == ["atom-domain-horarios"]
    assert {d["id"] for d in reader.find("system:clinica")} == {"atom-rule-cancelacion", "atom-domain-horarios", "trait-paciente-frecuente"}
    assert reader.find("domain:inexistente") == []
