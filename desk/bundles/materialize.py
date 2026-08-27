#!/usr/bin/env python
"""Proyecta desk/bundles/bundle-*.md sobre README.md y docs/*.md expandiendo cada ![[atom-id]].
Uso: python desk/bundles/materialize.py          -> reescribe los 4 docs generados
     python desk/bundles/materialize.py --check  -> exit 1 si algun doc difiere de su proyeccion (CI)
Los docs son GENERADOS: para corregirlos se edita el atom (deskops edit atom ...) o el bundle, nunca el doc.

Lee los atoms directo de desk/atoms/*.md con stdlib (frontmatter minimo + texto bajo `## Answer`) para que
el gate `static` de CI corra sin instalar sldb. La autoridad sigue siendo el store .sldb: el script exige que
cada atom transcluido figure en .sldb/core/documents/AtomDoc.yaml y falla si no esta trackeado.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLES = ROOT / "desk" / "bundles"
ATOMS = ROOT / "desk" / "atoms"
TRACKED_INDEX = ROOT / ".sldb" / "core" / "documents" / "AtomDoc.yaml"
TARGETS = {
    "bundle-readme": "README.md",
    "bundle-arquitectura": "docs/ARCHITECTURE.md",
    "bundle-glosario": "docs/GLOSSARY.md",
    "bundle-operaciones": "docs/OPERATIONS.md",
}
TRANSCLUSION = re.compile(r"^!\[\[([^\]|]+)\]\]\s*$", re.M)


def tracked_atoms() -> set[str]:
    """Nombres trackeados en el store (indice de documentos del modelo AtomDoc)."""
    if not TRACKED_INDEX.exists():
        sys.exit(f"ERROR: no existe {TRACKED_INDEX}; el store .sldb es la autoridad de los atoms")
    names = re.findall(r"^- name: (.+)$", TRACKED_INDEX.read_text(encoding="utf-8"), re.M)
    return {yaml_scalar(n) for n in names}


def yaml_scalar(raw: str) -> str:
    """Escalar YAML de una linea: los entrecomillados (escapes tipo backslash-xNN) se leen como literal Python."""
    raw = raw.strip()
    return ast.literal_eval(raw) if raw[:1] in "\"'" else raw


def atom_title_and_answer(atom_id: str) -> tuple[str, str]:
    text = (ATOMS / f"{atom_id}.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        sys.exit(f"ERROR: {atom_id}: sin frontmatter")
    front, body = m.groups()
    title = re.search(r"^title: (.+)$", front, re.M)
    if not title:
        sys.exit(f"ERROR: {atom_id}: sin title en el frontmatter")
    title_txt = yaml_scalar(title.group(1))
    answer = re.search(r"^## Answer\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    if not answer or not answer.group(1).strip():
        sys.exit(f"ERROR: {atom_id}: sin seccion '## Answer'")
    return title_txt, answer.group(1).strip()


def render(bundle: str, tracked: set[str]) -> str:
    src = (BUNDLES / f"{bundle}.md").read_text(encoding="utf-8")
    missing = [a for a in TRANSCLUSION.findall(src) if a not in tracked or not (ATOMS / f"{a}.md").exists()]
    if missing:
        sys.exit(f"ERROR: {bundle}: atoms no trackeados en .sldb o inexistentes: {', '.join(missing)}")

    def expand(m: re.Match) -> str:
        title, answer = atom_title_and_answer(m.group(1))
        return f"### {title}\n{answer}\n"

    header = f"<!-- generado desde desk/bundles/{bundle}.md — no editar a mano; python desk/bundles/materialize.py -->\n"
    return header + TRANSCLUSION.sub(expand, src)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    tracked = tracked_atoms()
    drift = []
    for bundle, target in TARGETS.items():
        out = ROOT / target
        rendered = render(bundle, tracked)
        current = out.read_text(encoding="utf-8") if out.exists() else None
        if rendered == current:
            print(f"ok       {target}")
            continue
        if check:
            drift.append(target)
            print(f"DRIFT    {target}  (regenerar con: python desk/bundles/materialize.py)")
        else:
            out.write_text(rendered, encoding="utf-8")
            print(f"escrito  {target}")
    if drift:
        print(f"ERROR: {len(drift)} doc(s) con drift respecto a desk/bundles: {', '.join(drift)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
