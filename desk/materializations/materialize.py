#!/usr/bin/env python
"""Proyecta desk/materializations/composition-*.md sobre sus target_path.
Uso: python desk/materializations/materialize.py          -> reescribe los docs generados
     python desk/materializations/materialize.py --check  -> exit 1 si algun doc difiere
Los docs son GENERADOS: para corregirlos se edita la composicion SLDB o el atom,
no el doc final.

El source surface vive en docs trackeados por el modelo local CompositionDoc.
La expansion de transclusiones `![[...]]` mantiene el contrato historico del repo:
cada atom se proyecta como `### <title>` + `<answer>`.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSITIONS = ROOT / "desk" / "materializations"
ATOMS = ROOT / "desk" / "atoms"
ATOM_INDEX = ROOT / ".sldb" / "core" / "documents" / "AtomDoc.yaml"
COMPOSITION_INDEX = ROOT / ".sldb" / "core" / "documents" / "CompositionDoc.yaml"
TRANSCLUSION = re.compile(r"^!\[\[([^\]|]+)\]\]\s*$", re.M)
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


def yaml_scalar(raw: str) -> str:
    raw = raw.strip()
    return ast.literal_eval(raw) if raw[:1] in "\"'" else raw


def tracked_names(index_path: Path) -> set[str]:
    if not index_path.exists():
        sys.exit(f"ERROR: no existe {index_path}")
    names = re.findall(r"^- name: (.+)$", index_path.read_text(encoding="utf-8"), re.M)
    return {yaml_scalar(n) for n in names}


def tracked_paths(index_path: Path) -> set[str]:
    if not index_path.exists():
        sys.exit(f"ERROR: no existe {index_path}")
    return set(re.findall(r"^  path: (.+)$", index_path.read_text(encoding="utf-8"), re.M))


def split_frontmatter(text: str, *, label: str) -> tuple[str, str]:
    m = FRONTMATTER.match(text)
    if not m:
        sys.exit(f"ERROR: {label}: sin frontmatter")
    return m.group(1), m.group(2)


def frontmatter_field(front: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}: (.+)$", front, re.M)
    if not m:
        sys.exit(f"ERROR: falta {name} en frontmatter")
    return yaml_scalar(m.group(1))


def composition_payload(path: Path) -> tuple[str, str]:
    front, body = split_frontmatter(path.read_text(encoding="utf-8"), label=str(path.relative_to(ROOT)))
    target_path = frontmatter_field(front, "target_path")
    return target_path, body.lstrip("\n")


def resolve_atom_path(raw: str) -> Path:
    cand = Path(raw.strip())
    if cand.suffix == ".md":
        p = (ROOT / cand).resolve() if not cand.is_absolute() else cand.resolve()
        if p.exists():
            return p
    atom_id = cand.stem if cand.suffix == ".md" else raw.strip()
    p = ATOMS / f"{atom_id}.md"
    if p.exists():
        return p
    sys.exit(f"ERROR: atom transcluido inexistente: {raw}")


def atom_title_and_answer(atom_ref: str) -> tuple[str, str]:
    path = resolve_atom_path(atom_ref)
    front, body = split_frontmatter(path.read_text(encoding="utf-8"), label=str(path.relative_to(ROOT)))
    title = frontmatter_field(front, "title")
    answer = re.search(r"^## Answer\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    if not answer or not answer.group(1).strip():
        sys.exit(f"ERROR: {path.relative_to(ROOT)}: sin seccion '## Answer'")
    return title, answer.group(1).strip()


def render_composition(source: Path, tracked_atoms: set[str], tracked_compositions: set[str]) -> tuple[str, str]:
    rel = str(source.relative_to(ROOT))
    if rel not in tracked_compositions:
        sys.exit(f"ERROR: composicion no trackeada en .sldb: {rel}")
    target_path, body = composition_payload(source)
    missing: list[str] = []
    for ref in TRANSCLUSION.findall(body):
        atom_path = resolve_atom_path(ref)
        atom_id = atom_path.stem
        if atom_id not in tracked_atoms:
            missing.append(atom_id)
    if missing:
        sys.exit(f"ERROR: {rel}: atoms no trackeados en .sldb: {', '.join(sorted(set(missing)))}")

    def expand(m: re.Match[str]) -> str:
        title, answer = atom_title_and_answer(m.group(1))
        return f"### {title}\n{answer}\n"

    header = (
        f"<!-- generado desde {rel} — no editar a mano; "
        f"python desk/materializations/materialize.py -->\n"
    )
    return target_path, header + TRANSCLUSION.sub(expand, body)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    tracked_atoms = tracked_names(ATOM_INDEX)
    tracked_compositions = tracked_paths(COMPOSITION_INDEX)
    drift: list[str] = []
    for source in sorted(COMPOSITIONS.glob("composition-*.md")):
        target_path, rendered = render_composition(source, tracked_atoms, tracked_compositions)
        out = ROOT / target_path
        current = out.read_text(encoding="utf-8") if out.exists() else None
        if rendered == current:
            print(f"ok       {target_path}")
            continue
        if check:
            drift.append(target_path)
            print(f"DRIFT    {target_path}  (regenerar con: python desk/materializations/materialize.py)")
        else:
            out.write_text(rendered, encoding="utf-8")
            print(f"escrito  {target_path}")
    if drift:
        print(
            f"ERROR: {len(drift)} doc(s) con drift respecto a desk/materializations: {', '.join(drift)}"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
