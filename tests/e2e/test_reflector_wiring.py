from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from kb_agent.orchestrator import Orchestrator

STORE_ROOT = PROJECT_ROOT / ".sldb_e2e_donpeppe"


def test_run_reflector_materializes_proposed_atom_without_duplicates(tmp_path: Path) -> None:
    copied_store = tmp_path / ".sldb_e2e_donpeppe"
    shutil.copytree(STORE_ROOT, copied_store)
    db_file = tmp_path / "reflector.sqlite"
    evidence_path = PROJECT_ROOT / "runs" / "e2e" / "reflector-run.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    orch = Orchestrator(kb_root=copied_store, db_url=f"sqlite:///{db_file}")
    try:
        _seed_scrubbed_turns(
            orch,
            external_id="wa:+56924444999",
            messages=[
                "¿Hacen delivery?",
                "hacen delivery?!",
                "Hacen delivery",
                "¿hacen delivery?",
                "Hacen delivery...",
            ],
        )
        before_files = _atom_files(copied_store)
        first_generated = orch.run_reflector()
    finally:
        orch.engine.dispose()

    orch_second = Orchestrator(kb_root=copied_store, db_url=f"sqlite:///{db_file}")
    try:
        second_generated = orch_second.run_reflector()
    finally:
        orch_second.engine.dispose()

    after_files = _atom_files(copied_store)
    new_files = sorted(after_files - before_files)

    assert first_generated, "run_reflector() should generate at least one atom for 5 recurrent turns"
    assert second_generated == []
    assert len(new_files) == 1

    atom_path = Path(first_generated[0]["path"])
    assert atom_path.exists()
    content = atom_path.read_text(encoding="utf-8")
    assert atom_path.suffix == ".md"
    assert "- source:reflector" in content
    assert "status: proposed" in content

    evidence = {
        "db_file": str(db_file),
        "copied_store": str(copied_store),
        "first_generated": first_generated,
        "second_generated": second_generated,
        "generated_atom_path": str(atom_path),
        "new_files": [str(path) for path in new_files],
    }
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")


def test_run_reflector_does_not_generate_atoms_below_pattern_threshold(tmp_path: Path) -> None:
    copied_store = tmp_path / ".sldb_e2e_donpeppe"
    shutil.copytree(STORE_ROOT, copied_store)
    db_file = tmp_path / "reflector-below-threshold.sqlite"
    before_files = _atom_files(copied_store)

    orch = Orchestrator(kb_root=copied_store, db_url=f"sqlite:///{db_file}")
    try:
        _seed_scrubbed_turns(
            orch,
            external_id="wa:+56924444004",
            messages=[
                "¿Hacen delivery?",
                "hacen delivery?!",
                "Hacen delivery",
                "¿hacen delivery?",
            ],
        )
        generated = orch.run_reflector()
    finally:
        orch.engine.dispose()

    after_files = _atom_files(copied_store)

    assert generated == []
    assert after_files == before_files


def _seed_scrubbed_turns(orch: Orchestrator, *, external_id: str, messages: list[str]) -> None:
    session = orch.SessionLocal()
    try:
        user = orch.ensure_user(session, external_id)
        for message in messages:
            orch._persist_chat_history(session, user_id=user.id, role="user", content=message)
        session.commit()
    finally:
        session.close()


def _atom_files(store_root: Path) -> set[Path]:
    return {path.resolve() for path in (store_root / "atoms").glob("*.md")}
