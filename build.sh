#!/usr/bin/env bash
# Build pipeline: AST scan -> spec -> rendered -> catalogo HTML con atoms inyectados.
# Uso: ./build.sh   (desde software/kb-agent-runtime/)
set -euo pipefail
cd "$(dirname "$0")"

S=/home/jp/proyectos/hum-ecosystem/tools/spec2viz
python $S/spec2viz/cli.py diagram generate kb_agent --out specs/architecture.spec.yaml \
  --id kb-agent-runtime --title "KB Agent Runtime · Arquitectura AST"
python $S/spec2viz/cli.py diagram validate specs/architecture.spec.yaml
python $S/spec2viz/cli.py diagram render specs/architecture.spec.yaml --out rendered --renderer mermaid
python $S/spec2viz/cli.py diagram lint rendered/architecture.spec.mmd
python $S/spec2viz/cli.py catalog build --config docs/vistas/vistas.yml --out docs/kb_agent_runtime.html

# Inyectar atoms locales (desk/atoms/**) como window.ATOMS_DB (si existen).
if [ ! -d desk/atoms ]; then
  echo "Sin desk/atoms - HTML sin inyeccion de atoms"
  exit 0
fi
python - <<'PY'
import json, re, sys
sys.path.insert(0, '/home/jp/proyectos/hum-ecosystem/tools/spec2viz')
from pathlib import Path
from spec2viz.deskops import parse_atoms

atoms = {}
for d in Path('desk/atoms').iterdir():
    if d.is_dir():
        atoms.update(json.loads(parse_atoms(d)))
if not atoms:
    atoms = json.loads(parse_atoms(Path('desk/atoms')))

html_path = Path('docs/kb_agent_runtime.html')
html = html_path.read_text()
new, n = re.subn(r'window\.ATOMS_DB = \{\};',
                 'window.ATOMS_DB = ' + json.dumps(atoms, ensure_ascii=False) + ';',
                 html, count=1)
if n == 0:
    sys.exit('No se encontro window.ATOMS_DB = {} en el HTML')
html_path.write_text(new)
print(f'Atoms inyectados: {len(atoms)}')
PY
