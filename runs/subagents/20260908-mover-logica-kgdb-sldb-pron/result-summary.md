# task-mover-logica-reimplementada-a-kgdb-sldb-pron — evidencia de cierre (2026-09-08)

## Tests
- `python -m pytest tests/unit tests/integration -q` → 310 passed, 5 skipped (Vitali ausente).
- `python -m pytest tests/ui -q` → 96 passed, 3 xfailed, 1 failed (expectativa vieja de Don Peppe), corregido en 19c63e1 (smoke: 5 passed).
- pron: 68 passed (`legos/pron`, commits 230a99f, eb6cce1, bbecea5, d7f9002). kgdb: 41 passed (sin cambios).

## Commits (gemini_test, dev)
5dd9cb2 ee1dc1c e400b6b a5d2622 10e75d0 c82c24c 7e1ff3a 72d6a58 63c8e93 4d23dc0 9649d88 19c63e1

## Qué quedó
Ver `report-overimplementation-vs-sldb-v2.md` § "Estado al cierre".
