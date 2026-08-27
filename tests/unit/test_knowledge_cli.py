"""knowledge CLI (operaciones in-process): explore, show, step next, traits, self, context, propose."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kb_agent.models_sql.identity import Base, UserTraits, Users
from kb_agent.models_sql.session import ChatHistory, SessionNode, SessionState
from knowledge_base.operations import KnowledgeOperations, derive_path
from tests.support.sldb_seed import DEFAULT_NAMESPACES_REGISTRY, REPO_ROOT, seed_store

USER = "wa:+56900000000"
ATOMS = [
    {"type": "self", "id": "self-bot", "title": "Bot Identity", "tags": ["self:whoami", "system:test"], "fields": {"statement": "Soy un bot de prueba para el sistema de conocimiento."}},
    {"type": "style", "id": "style-bot", "title": "Bot Style", "tags": ["self:estilo", "system:test"], "fields": {"tone": "Amable y conciso.", "language_register": "Formal, trato de usted.", "phrase_preferences": "", "length_guidelines": ""}},
    {"type": "boundary", "id": "boundary-bot", "title": "Bot Limits", "tags": ["self:limites", "system:test"], "fields": {"restriction": "No puedo dar consejo legal.", "conditions": "", "escalation": "Derivar a un abogado."}},
    {"type": "domain", "id": "atom-carta", "title": "Carta", "tags": ["domain:catalogo", "system:test"], "five_wh": "what", "domain_ref": "test-biz", "fields": {"answer": "Pizza Margherita 8900, Napolitana 9800."}},
    {"type": "trait", "id": "trait-vegetariano", "title": "Vegetariano", "tags": ["user:traits.vegetariano", "system:test"], "category": "dietary", "fields": {"description": "Cliente que no consume carne."}},
    {"type": "step", "id": "step-onboarding", "title": "Onboarding", "kind": "interaccion_simple", "tags": ["conversation:steps.onboarding", "system:test"], "domain_ref": "test-biz",
     "fields": {"instructions": "Dar la bienvenida.", "required_slots": "nombre", "allowed_transitions": "conversation:steps.booking", "grounding_atoms": "atom-carta", "completion_condition": "Usuario saludado."}},
]


@pytest.fixture(scope="module")
def kb_store(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return seed_store(
        tmp_path_factory.mktemp("kb") / "store",
        ATOMS,
        namespaces_registry=DEFAULT_NAMESPACES_REGISTRY,
    )


def _seed_db(db_url: str, *, flow_node: str | None = "conversation:steps.onboarding", flow_slots: dict | None = {"missing_slots": ["nombre"]}, history: bool = False) -> None:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        user = Users(external_id=USER, channel="whatsapp")
        session.add(user)
        session.flush()
        session.add(SessionState(user_id=user.id, current_node=SessionNode.IDLE, flow_node=flow_node, flow_slots=flow_slots))
        session.add(UserTraits(user_id=user.id, trait_id="trait-vegetariano", confidence=0.9, source="perfilador"))
        if history:
            session.add_all([
                ChatHistory(user_id=user.id, role="user", content="hola", pii_scrubbed=True),
                ChatHistory(user_id=user.id, role="assistant", content="¿cómo estás?", pii_scrubbed=True),
            ])
        session.commit()
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seeded_db(tmp_path: Path) -> str:
    url = f"sqlite:///{tmp_path / 'test.db'}"
    _seed_db(url)
    return url


def _ops(kb_store: Path, db_url: str | None = None) -> KnowledgeOperations:
    return KnowledgeOperations(kb_store, db_url, pythonpath=str(REPO_ROOT))


# ── explore / show ────────────────────────────────────────────────────────────

def test_explore_root_tag_leaf_and_atom(kb_store: Path) -> None:
    ops = _ops(kb_store)
    root = ops.explore()
    assert root["mode"] == "root" and "system:test" in {r["tag"] for r in root["root_tags"]}

    tag = ops.explore(tag="conversation:steps")
    assert tag["mode"] == "tag" and "conversation:steps.onboarding" in tag["children"]
    assert "step-onboarding" in ops.explore(tag="conversation:steps.onboarding")["docs"]

    atom = ops.explore(atom="step-onboarding")
    assert atom["mode"] == "atom" and "conversation:steps.onboarding" in atom["tags"]
    assert not any(t.startswith(("type.", "workspace.")) for t in atom["tags"])


def test_show_returns_typed_document_or_none(kb_store: Path) -> None:
    ops = _ops(kb_store)
    doc = ops.show("self-bot")
    assert doc["id"] == "self-bot" and doc["_model"] == "SelfDeclaration" and "bot de prueba" in doc["statement"]
    assert ops.show("atom-carta")["_model"] == "DomainAtom"
    assert ops.show("does-not-exist") is None


# ── step next ─────────────────────────────────────────────────────────────────

def test_step_next_reads_flow_node_and_slots_from_sql(kb_store: Path, seeded_db: str) -> None:
    result = _ops(kb_store, seeded_db).step_next(USER)
    assert result["flow_node"] == "conversation:steps.onboarding"
    assert result["missing_slots"] == ["nombre"]


@pytest.mark.parametrize(
    "db_kwargs",
    [
        pytest.param({"flow_node": None}, id="flow_node-None"),
        pytest.param({"flow_slots": None}, id="flow_slots-None"),
    ],
)
def test_step_next_tolerates_null_session_fields(kb_store: Path, tmp_path: Path, db_kwargs: dict) -> None:
    url = f"sqlite:///{tmp_path / 'edge.db'}"
    _seed_db(url, **db_kwargs)
    result = _ops(kb_store, url).step_next(USER)
    assert result["flow_node"] is not None  # None -> fallback a busqueda semantica
    assert isinstance(result["missing_slots"], list)


@pytest.mark.parametrize("db_url", [None, "sqlite:///{tmp}/noexiste.db"], ids=["sin-db", "db-inexistente"])
def test_step_next_and_traits_degrade_gracefully_without_sql(kb_store: Path, tmp_path: Path, db_url: str | None) -> None:
    url = db_url.format(tmp=tmp_path) if db_url else None
    ops = _ops(kb_store, url)
    assert ops.step_next("unknown-user")["flow_node"] is not None
    assert ops.traits("unknown-user") == []


# ── traits / self / context ───────────────────────────────────────────────────

def test_traits_resolve_sql_rows_against_trait_atoms(kb_store: Path, seeded_db: str) -> None:
    [trait] = _ops(kb_store, seeded_db).traits(USER)
    assert (trait["trait_id"], trait["title"], trait["category"], trait["confidence"]) == ("trait-vegetariano", "Vegetariano", "dietary", 0.9)
    assert _ops(kb_store, seeded_db).traits("wa:+56999999999") == []


def test_self_context_compiles_identity_style_boundaries(kb_store: Path) -> None:
    result = _ops(kb_store).self_context()
    assert result["identity"][0]["id"] == "self-bot"
    assert result["style"][0]["tone"] == "Amable y conciso."
    assert "consejo legal" in result["boundaries"][0]["restriction"]


def test_context_aggregates_step_traits_self(kb_store: Path, seeded_db: str) -> None:
    result = _ops(kb_store, seeded_db).context(USER)
    assert set(result) == {"step", "traits", "self"}
    assert result["step"]["flow_node"] == "conversation:steps.onboarding"
    assert len(result["traits"]) == 1 and len(result["self"]["identity"]) == 1


# ── propose / reflect ─────────────────────────────────────────────────────────

def test_propose_writes_proposed_atom_in_isolated_copy(kb_store: Path, tmp_path: Path) -> None:
    isolated = tmp_path / "kb_propose"
    shutil.copytree(kb_store, isolated)
    result = _ops(isolated).propose("domain", "id: atom-nueva\ntitle: Nueva\nsummary: Nueva atom de dominio para test.\nfive_wh_one_plus: what\nanswer: Contenido\ntags:\n- domain:test\n")
    assert (result["status"], result["source"]) == ("proposed", "reflector")
    assert Path(result["path"]) == derive_path(isolated, "atom-nueva", ["domain:test", "status:proposed", "source:reflector"])
    content = Path(result["path"]).read_text(encoding="utf-8")
    assert "status:proposed" in content and "source:reflector" in content


def test_propose_validates_model_and_body(kb_store: Path) -> None:
    with pytest.raises(ValueError, match="Unknown model"):
        _ops(kb_store).propose("nonexistent", "id: x\ntitle: y")
    with pytest.raises(ValueError, match="must be a YAML"):
        _ops(kb_store).propose("domain", "just a string")


def test_reflect_reads_chat_history_and_returns_list(kb_store: Path, tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'reflect.db'}"
    _seed_db(url, history=True)
    isolated = tmp_path / "kb_reflect"
    shutil.copytree(kb_store, isolated)
    assert _ops(isolated, url).reflect() == []  # < PATTERN_MIN_COUNT repeticiones
    with pytest.raises(ValueError, match="--db"):
        _ops(isolated).reflect()


def test_organize_dry_run_reports_semantic_destinations(kb_store: Path) -> None:
    result = _ops(kb_store).organize(dry_run=True)
    destinations = {item["id"]: Path(item["destination"]) for item in result["moves"]}
    assert destinations["self-bot"] == kb_store / "self" / "whoami" / "self-bot.md"
    assert destinations["step-onboarding"] == kb_store / "conversation" / "steps" / "onboarding" / "step-onboarding.md"
    assert destinations["atom-carta"] == kb_store / "domain" / "catalogo" / "atom-carta.md"


# ── cache invalidation ──────────────────────────────────────────────────────────

def test_promote_invalidates_cache_for_subsequent_read(tmp_path_factory: pytest.TempPathFactory) -> None:
    """`KnowledgeOperations` cachea records/docs por instancia (ver `_find_records`,
    `_read_doc`). `promote` escribe tags nuevos al `.md` del atom: una lectura
    posterior EN EL MISMO PROCESO (misma instancia de `ops`) debe ver el cambio,
    no el payload que `show()` ya había cacheado antes del `promote`. Sin la
    invalidación en `promote` (`self._invalidate_cache()`), este `after` sería
    idéntico al `before` (todavía con `status:proposed`) porque `_read_doc`
    devolvería el dict guardado en `self._doc_cache` en vez de releer el store.
    """
    root = seed_store(
        tmp_path_factory.mktemp("kb_promote") / "store",
        [{
            "type": "domain", "id": "atom-nueva", "title": "Nueva",
            "tags": ["domain:test", "status:proposed"], "five_wh": "what",
            "fields": {"answer": "Contenido"},
        }],
        namespaces_registry=DEFAULT_NAMESPACES_REGISTRY,
    )
    ops = _ops(root)

    before = ops.show("atom-nueva")
    assert before is not None
    assert "status:proposed" in before["tags"]

    result = ops.promote("atom-nueva")
    assert result["status"] == "active"

    after = ops.show("atom-nueva")
    assert after is not None
    assert "status:proposed" not in after["tags"]
    assert "status:active" in after["tags"]


# ── derive_path (funcion pura) ────────────────────────────────────────────────

def test_derive_path_uses_single_semantic_tag() -> None:
    assert derive_path(Path("/kb"), "step-onboarding", ["conversation:steps.onboarding"]) == Path(
        "/kb/conversation/steps/onboarding/step-onboarding.md"
    )


def test_derive_path_skips_excluded_namespaces_and_uses_first_significant_tag() -> None:
    assert derive_path(
        Path("/kb"),
        "trait-vegetariano",
        ["type.knowledge.trait", "workspace:tests", "source:reflector", "user:traits.vegetariano", "domain:catalogo"],
    ) == Path("/kb/user/traits/vegetariano/trait-vegetariano.md")


def test_derive_path_falls_back_to_flat_atoms_when_only_excluded_tags_exist() -> None:
    assert derive_path(
        Path("/kb"),
        "orphan-atom",
        ["type.knowledge.domain", "workspace:desk", "source:x"],
    ) == Path("/kb/atoms/orphan-atom.md")


# ── index embeddings ──────────────────────────────────────────────────────────

EMBED_ATOMS = [
    {"type": "domain", "id": "atom-carta", "title": "Carta", "summary": "Resumen de la carta del negocio.",
     "tags": ["domain:catalogo", "system:test"], "five_wh": "what", "domain_ref": "test-biz",
     "fields": {"answer": "Pizza Margherita 8900."}},
    {"type": "gate", "id": "gate-corpus", "title": "Gate Corpus", "summary": "Valido que la respuesta use solo el corpus aprobado.",
     "tags": ["gate:corpus", "system:test"],
     "fields": {"criterion": "Usa solo información del corpus.", "approval_condition": "Cita el corpus.", "rejection_action": "Encola revisión humana."}},
]

EMBED_DIM = 768


class _FakeEmbedder:
    """Embedder determinista para tests: evita la descarga del modelo real.

    Reproduce el contrato de fastembed.TextEmbedding.embed(): recibe una lista
    de textos y devuelve un iterable de vectores (uno por texto).
    """

    def __init__(self, dim: int = EMBED_DIM) -> None:
        self._dim = dim

    def embed(self, texts: list[str]):
        for i, text in enumerate(texts):
            seed = (len(text) + i) % 7 + 1
            yield [float(seed) * 0.001 * (j + 1) for j in range(self._dim)]


def _embedding_line(doc_path: Path) -> list[float]:
    import yaml

    parts = doc_path.read_text(encoding="utf-8").split("---", 2)
    data = yaml.safe_load(parts[1]) or {}
    return data.get("embedding")


@pytest.fixture()
def embed_kb(tmp_path: Path) -> Path:
    return seed_store(
        tmp_path / "embed_store",
        EMBED_ATOMS,
        namespaces_registry=DEFAULT_NAMESPACES_REGISTRY,
    )


def test_index_embeddings_persists_vectors_to_frontmatter(embed_kb: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ops = _ops(embed_kb)
    monkeypatch.setattr(ops, "_embedder", lambda: _FakeEmbedder())
    # Evitar dependencia de `sldb stores update` subprocess en el aserto de persistencia.
    monkeypatch.setattr(ops, "_run_sldb", lambda *args: None)

    domain_path = embed_kb / "atoms" / "atom-carta.md"
    gate_path = embed_kb / "atoms" / "gate-corpus.md"
    # Partimos sin embedding en disco.
    assert _embedding_line(domain_path) is None
    assert _embedding_line(gate_path) is None

    stats = ops.index_embeddings()

    # Procesa TODOS los tipos, incluido gate (Bug 1).
    assert stats["processed"] == 2
    assert stats["errors"] == 0
    assert stats["dimension"] == EMBED_DIM

    # Persiste realmente al .md (Bug 2): vectores no vacíos de dimensión esperada.
    domain_vec = _embedding_line(domain_path)
    gate_vec = _embedding_line(gate_path)
    assert isinstance(domain_vec, list) and len(domain_vec) == EMBED_DIM
    assert isinstance(gate_vec, list) and len(gate_vec) == EMBED_DIM
    assert any(v != 0.0 for v in gate_vec)


def test_index_embeddings_survives_store_update_failure(embed_kb: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ops = _ops(embed_kb)
    monkeypatch.setattr(ops, "_embedder", lambda: _FakeEmbedder())

    def _boom(*args: str) -> None:
        raise RuntimeError("returned non-zero exit status 1")

    monkeypatch.setattr(ops, "_run_sldb", _boom)

    stats = ops.index_embeddings()

    # Un fallo del store NO aborta el pipeline ni descarta lo ya escrito.
    assert stats["processed"] == 2
    assert "store_update_error" in stats
    gate_vec = _embedding_line(embed_kb / "atoms" / "gate-corpus.md")
    assert isinstance(gate_vec, list) and len(gate_vec) == EMBED_DIM
