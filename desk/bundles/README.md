# desk/bundles

Los bundles son la fuente de los docs de alto nivel. Cada `bundle-*.md` es Markdown plano que
transcluye atoms con `![[atom-id]]`; `materialize.py` expande cada transclusion como
`### <title>` + `<answer>` del atom y escribe el doc generado:

| Bundle | Doc generado |
|---|---|
| `bundle-readme.md` | `README.md` |
| `bundle-arquitectura.md` | `docs/ARCHITECTURE.md` |
| `bundle-glosario.md` | `docs/GLOSSARY.md` |
| `bundle-operaciones.md` | `docs/OPERATIONS.md` |

```bash
python desk/bundles/materialize.py          # regenera los 4 docs
python desk/bundles/materialize.py --check  # drift guard (CI, job static): exit 1 si un doc difiere
```

Reglas:
- Los 4 docs son generados y llevan un comentario HTML de cabecera que lo dice. Nunca se parchan a mano:
  si algo esta mal, se corrige el atom (`deskops edit atom <id> answer "<texto>" --root .`, luego
  `sldb stores update --store .sldb`) o el orden/intro del bundle, y se vuelve a correr el script.
- Todo atom transcluido tiene que estar trackeado en `.sldb` (el script falla listando los que no).
- El script lee los atoms con stdlib (sin `sldb`) para que el gate `static` de CI corra sin deps;
  el store sigue siendo la autoridad.
