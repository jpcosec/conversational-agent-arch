# desk/materializations

Las proyecciones de alto nivel viven como documentos SLDB trackeados por `CompositionDoc`.
Cada `composition-*.md` declara su `target_path` y contiene el Markdown fuente con
transclusiones `![[...]]` hacia atoms.

```bash
python desk/materializations/materialize.py          # regenera los docs proyectados
python desk/materializations/materialize.py --check  # drift guard (CI): exit 1 si un doc difiere
```

Reglas:
- Los docs finales son generados. Nunca se editan a mano.
- La composición se corrige editando `desk/materializations/composition-*.md`.
- El contenido durable se corrige editando `desk/atoms/*.md`.
- Tanto las composiciones como los atoms deben estar trackeados en `.sldb`.
