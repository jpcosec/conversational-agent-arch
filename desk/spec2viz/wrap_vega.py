#!/usr/bin/env python3
"""Envuelve un spec Vega (.vega.json) en un fragmento HTML embebible por el catalogo spec2viz.

El template builtin del catalogo solo sabe embeber mermaid (.mmd), .svg y .html.
Para incluir una vista `component_view_matrix` (que spec2viz renderiza a Vega JSON)
la envolvemos en un <div class="board"> + vega-embed por CDN. El fragmento se
inserta por string-replace en el HTML del catalogo, asi que su <script> corre al
cargar la pagina.

Como el renderer Vega de spec2viz no siempre pinta los labels de texto (bbox 0x0
en algunos motores; afecta tambien al ejemplo oficial), acompanamos la matriz con
una leyenda HTML derivada del spec (filas, stages por vista, colores por kind)
para que la vista sea auto-legible en el catalogo pase lo que pase con el texto SVG.

Uso:
    python desk/spec2viz/wrap_vega.py \
        desk/spec2viz/build/matrix.component-turn-lifecycle.vega.json \
        desk/spec2viz/build/matrix.component-turn-lifecycle.html
"""
from __future__ import annotations

import html as _html
import json
import sys
from pathlib import Path

_KIND_COLORS = {
    "core": "#F59E0B", "boundary": "#60A5FA", "engine": "#F59E0B",
    "decision_engine": "#EC4899", "actor": "#A78BFA", "service": "#94A3B8",
    "api": "#94A3B8", "ui": "#94A3B8", "database": "#10B981",
}


def _legend_from_spec(spec: dict) -> str:
    """Construye una leyenda HTML (vistas -> stages, y kinds -> color) desde el data del spec."""
    data = {d.get("name"): d for d in spec.get("data", [])}
    stages = data.get("stages", {}).get("values", [])
    spans = data.get("spans", {}).get("values", [])
    # vistas en orden de aparicion, con sus stages
    views: dict[str, list[str]] = {}
    for s in stages:
        views.setdefault(s.get("view", ""), []).append(s.get("label", s.get("id", "")))
    kinds = []
    for sp in spans:
        k = sp.get("kind")
        if k and k not in kinds:
            kinds.append(k)
    view_html = "".join(
        f'<div style="margin:2px 0"><b>{_html.escape(v)}</b>: '
        + " \u2192 ".join(_html.escape(x) for x in st) + "</div>"
        for v, st in views.items()
    )
    kind_html = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px">'
        f'<span style="width:11px;height:11px;border-radius:3px;background:{_KIND_COLORS.get(k, "#94A3B8")}"></span>'
        f'{_html.escape(k)}</span>'
        for k in kinds
    )
    return (
        '<div class="matrix-legend" style="font-size:12px;color:var(--bone-dim,#94a3b8);'
        'padding:10px 12px;line-height:1.5">'
        '<div style="opacity:.8;margin-bottom:6px"><b>Vistas &amp; stages:</b></div>'
        f'{view_html}'
        f'<div style="margin-top:8px"><b>Kinds:</b> {kind_html}</div>'
        '</div>'
    )

FRAGMENT = """<div class="board">
  <div id="{div_id}" class="vega-matrix" style="min-width:max-content;background:#f8fafc;border-radius:10px;padding:12px"></div>
{legend}
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <script>
    (function() {{
      var spec = {spec_json};
      function draw() {{
        if (typeof vegaEmbed === "undefined") {{ setTimeout(draw, 60); return; }}
        vegaEmbed("#{div_id}", spec, {{actions: false, renderer: "canvas"}})
          .catch(function(e) {{ console.error("vega-embed matrix:", e); }});
      }}
      draw();
    }})();
  </script>
</div>"""


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    src = Path(argv[1])
    out = Path(argv[2])
    spec = json.loads(src.read_text(encoding="utf-8"))
    div_id = "vega-" + out.stem.replace(".", "-")
    fragment = FRAGMENT.format(
        div_id=div_id, spec_json=json.dumps(spec), legend=_legend_from_spec(spec)
    )
    out.write_text(fragment, encoding="utf-8")
    print(f"Wrapped {src.name} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
