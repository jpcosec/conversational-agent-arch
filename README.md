<!-- generado desde desk/bundles/bundle-readme.md — no editar a mano; python desk/bundles/materialize.py -->
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

### Modelo de ramas
Cuatro tipos de rama (README.md, sección "Ramas, CI y releases"). `dev` es integración y la única rama donde se mergea — recibe `merge --no-ff` desde ramas de feature con la suite verde. `main` es estable — avanza sólo por fast-forward desde `dev` cuando pasa la suite completa, incluida la capa LLM. `production` es lo desplegado en Modal — la mueve únicamente `deploy/release.sh`, con tag `release-YYYYMMDD-<sha>`. Las features (`vitali`, `apoe`, …) viven como worktrees en `../_worktrees/<nombre>` — nacen de `dev`, se rebasean sobre `dev` mientras viven, vuelven con `--no-ff`, y al mergear se borran worktree y rama. Reglas — nada se commitea directo en `main` ni `production`; `main` nunca se mergea hacia `dev` (todo nace en `dev`); cero stashes (todo cambio probado se commitea); lo legacy se borra, no se archiva (el archivo es el historial de git). Ciclo completo de una feature — `git worktree add ../_worktrees/vitali -b vitali dev`; commits en el worktree; `git -C ../_worktrees/vitali rebase dev`; `git checkout dev && git merge --no-ff vitali`; `git worktree remove ../_worktrees/vitali && git branch -d vitali`; `git checkout main && git merge --ff-only dev`; `git push origin dev main`.

### Capas de verificación y release
Cinco capas de verificación con su comando (README.md, sección "Ramas, CI y releases"). `static` (CI, job `static` de .github/workflows/ci.yml, sin deps) — `compileall`, `project.config.yaml` válido con negocio activo, sin hardcodes de negocio en string-literals vivos de `kb_agent/`, y los docs proyectados sin drift (`python desk/bundles/materialize.py --check`). `suite` (CI y local) — unit + integration sin LLM, `SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration`; en CI instala `sldb`/`kgdb`/`deskops` por git. `ui` (local) — Playwright + Chromium contra la app in-process, `python -m pytest tests/ui` (marker `ui`, se salta sin Playwright). `llm` / `simulation` (local con `.env`, Vertex ADC vía `GOOGLE_GENAI_USE_VERTEXAI` + `GOOGLE_CLOUD_PROJECT`) — `set -a; source .env; set +a; python -m pytest tests/e2e`, smoke + simulaciones agente-vs-usuario con juez LLM. Release gate (local) — `deploy/release.sh`, preflight + suite offline + deploy + tag + `production`, fuente de verdad de qué hay arriba. CI corre en push a `main`, `dev` y `production` y en cada PR; los tests con marker `llm` se saltan solos sin credenciales o con `SKIP_LLM_TESTS=1` (tests/conftest.py). `known_gap` es un xfail estricto que documenta un defecto conocido del runtime y exige quitar la marca al arreglarse. Release — desde `main` limpio (el script rechaza working tree sucio), `deploy/release.sh [tag]` (sin tag, `release-YYYYMMDD-<sha>`; `SKIP_DEPLOY=1` sólo gate + tag). Secuencia — suite offline => `modal deploy deploy/modal_app.py` (app `kb-agent-runtime`, secret `kb-agent-runtime-gcp`, volumen `kb-agent-runtime-data`; alembic migra al arrancar el contenedor) => `production` = SHA desplegado + tag; no hace push, lo imprime — `git push origin production && git push origin <tag>`. Antes de producción se prueba en el endpoint dev (app y volumen propios, mismo secret) — `MODAL_APP_NAME=kb-agent-runtime-dev modal deploy deploy/modal_app.py`. Mantenimiento del sqlite del volumen — `modal run deploy/modal_app.py::inspect_db` (sólo lectura) y `modal run deploy/modal_app.py::clean_and_seed` (borra conversaciones y resiembra usuarios demo). `DEMO_MODE=1` (modo demo sin LLM, datos de `frontends/chat/demo_data.py`) es opt-in y nunca se setea en producción.
