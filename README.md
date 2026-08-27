# KB Agent Runtime

### Propuesta de Valor
Agente conversacional multi-dominio diseñado para operar en entornos de alta restricción. Su núcleo no depende de prompts hardcodeados, sino de la inyección dinámica de conocimiento estructurado (Átomos Semánticos), permitiendo cambiar de negocio (ej. de una clínica a una pizzería) simplemente cambiando la base de datos subyacente.

### Garantía Cero Alucinaciones
Regla arquitectónica estricta: el LLM tiene prohibido inventar información. Si el Ontologizador compila un contexto vacío (sin hechos ni reglas que sustenten la consulta del usuario), la máquina de estados fuerza una transición a un nodo de `BREAKPOINT_MISS`, obligando al agente a usar un mensaje de `fallback` determinista en lugar de alucinar una respuesta.

### Negocios Activos (KBs)
El sistema soporta múltiples negocios aislados. Actualmente conviven dos KBs principales: 'Antonia' (asistente clínico, producción) que vive en `knowledge/`, y 'Don Peppe' (pizzería, pruebas) que vive en `tests/knowledge/`. El archivo `project.config.yaml` actúa como el switch que define cuál está activo.


## Arquitectura y Componentes
> Ver [Documentación de Arquitectura](docs/ARCHITECTURE.md) y [Catálogo Visual](desk/spec2viz/build/architecture.html) para detalles técnicos.

## Glosario del Dominio
> Ver [Glosario de Conceptos](docs/GLOSSARY.md).

## Operaciones y Desarrollo
> Ver [Guía de Operaciones](docs/OPERATIONS.md).

## Configuración (KB vs YAML) y montar otro negocio
> Ver [Guía de Configuración](docs/CONFIGURATION.md).

## Ramas, CI y releases
> Capas de test, topología Modal y alembic en detalle: [Guía de Operaciones](docs/OPERATIONS.md). Secrets, imagen y volumen: [deploy/README.md](deploy/README.md).

### Ramas

| Rama | Rol | Cómo avanza |
|---|---|---|
| `dev` | Integración. Única rama donde se mergea. | `merge --no-ff` desde ramas de feature con la suite verde. |
| `main` | Estable. | Solo fast-forward desde `dev` cuando pasa la suite completa, incluida la capa LLM. |
| `production` | Lo que está desplegado en Modal. | La mueve únicamente `deploy/release.sh`, con tag `release-YYYYMMDD-<sha>`. |
| `vitali`, `apoe`, … | Features, como worktrees en `../_worktrees/<nombre>`. | Nacen de `dev`, se rebasean sobre `dev` mientras viven, vuelven con `--no-ff`; al mergear se borran worktree y rama. |

Reglas:
- Nada se commitea directo en `main` ni en `production`.
- `main` nunca se mergea hacia `dev`: todo nace en `dev`.
- Cero stashes: todo cambio probado se commitea (regla del repo).
- Lo legacy se borra, no se archiva: el archivo es el historial de git.

Ciclo completo de una feature:

```bash
git worktree add ../_worktrees/vitali -b vitali dev    # nace de dev
# ... commits en ../_worktrees/vitali ...
git -C ../_worktrees/vitali rebase dev                  # mientras vive, sobre dev
git checkout dev && git merge --no-ff vitali            # vuelve con suite verde
git worktree remove ../_worktrees/vitali && git branch -d vitali
git checkout main && git merge --ff-only dev            # solo ff, suite completa (incl. LLM) verde
git push origin dev main
```

### Capas de verificación

| Capa | Dónde | Qué corre | Comando |
|---|---|---|---|
| `static` | CI | Sin deps: `compileall`, `project.config.yaml` válido, sin hardcodes de negocio en `kb_agent/`. | job `static` de `.github/workflows/ci.yml` |
| `suite` | CI y local | Unit + integration sin LLM. En CI instala `sldb`/`kgdb`/`deskops` por git. | `SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration` |
| `ui` | Local | Playwright + Chromium contra la app in-process (`tests/ui`, marker `ui`). Se salta si no hay Playwright. | `python -m pytest tests/ui` |
| `llm` / `simulation` | Local con `.env` | Vertex ADC (`GOOGLE_GENAI_USE_VERTEXAI` + `GOOGLE_CLOUD_PROJECT`). `tests/e2e`: smoke + simulaciones agente-vs-usuario con juez LLM. | `set -a; source .env; set +a; python -m pytest tests/e2e` |
| release gate | Local | Preflight + suite offline + deploy + tag + `production`. Fuente de verdad de "qué hay arriba". | `deploy/release.sh` |

CI (`.github/workflows/ci.yml`) corre en push a `main`, `dev` y `production` y en cada PR. Los tests con marker `llm` se saltan solos sin credenciales o con `SKIP_LLM_TESTS=1` (`tests/conftest.py`). `known_gap` es un xfail estricto: documenta un defecto conocido del runtime y, al arreglarse, el test exige quitar la marca.

### Release y deploy

Desde `main` limpio (el script rechaza working tree sucio):

```bash
deploy/release.sh [tag]          # sin tag: release-YYYYMMDD-<sha>
SKIP_DEPLOY=1 deploy/release.sh  # solo gate + tag, no toca Modal
```

Secuencia: suite offline → `modal deploy deploy/modal_app.py` (app `kb-agent-runtime`, secret `kb-agent-runtime-gcp`, volumen `kb-agent-runtime-data` con el sqlite; las migraciones alembic corren al arrancar el contenedor) → `production` = SHA desplegado + tag. El script no hace push; lo imprime al final:

```bash
git push origin production && git push origin <tag>
```

Endpoint de desarrollo separado (app y volumen propios, mismo secret) para probar antes de producción:

```bash
MODAL_APP_NAME=kb-agent-runtime-dev modal deploy deploy/modal_app.py
```

Mantenimiento del sqlite del volumen:

```bash
modal run deploy/modal_app.py::inspect_db      # solo lectura
modal run deploy/modal_app.py::clean_and_seed  # borra conversaciones y resiembra usuarios demo
```

`DEMO_MODE=1` (modo demo sin LLM, datos de `frontends/chat/demo_data.py`) es opt-in y nunca se setea en producción.
