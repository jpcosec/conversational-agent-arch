---
id: composition-readme
title: README
target_path: README.md
tags:
- workspace:docs
- type:composition
- target:readme
provenance: desk/materializations/composition-readme.md
---

# KB Agent Runtime

![[desk/atoms/atom-propuesta-de-valor.md]]
![[desk/atoms/atom-garantia-cero-alucinaciones.md]]
![[desk/atoms/atom-un-negocio-por-rama.md]]

## Arquitectura y Componentes
> Ver [Documentación de Arquitectura](docs/ARCHITECTURE.md) y [Catálogo Visual](desk/spec2viz/build/architecture.html) para detalles técnicos.

## Glosario del Dominio
> Ver [Glosario de Conceptos](docs/GLOSSARY.md).

## Operaciones y Desarrollo
> Ver [Guía de Operaciones](docs/OPERATIONS.md).

## Configuración (KB vs YAML) y montar otro negocio
> Ver [Guía de Configuración](docs/CONFIGURATION.md).

## Local Setup Quickstart

To run the **Antonia** knowledge base agent locally:

1. **Clone the repository** and navigate to the root.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   This installs all runtime dependencies (FastAPI, Uvicorn, SQLAlchemy, etc.).
3. **Set up environment variables** (optional):
   ```bash
   export GOOGLE_GENAI_USE_VERTEXAI=1
   export GOOGLE_CLOUD_PROJECT=your-project-id
   ```
4. **Start the API server**:
   ```bash
   uvicorn kb_agent.main:app --host 127.0.0.1 --port 8000
   ```
   The service will listen on `http://127.0.0.1:8000`.
5. **Run tests** (unit + integration):
   ```bash
   pytest tests/unit tests/integration -q
   ```
6. **Interact with the UI** (if Playwright is installed):
   ```bash
   playwright install chromium
   playwright test tests/ui
   ```

## Ramas, CI y releases
> Capas de test, topología Modal y alembic en detalle: [Guía de Operaciones](docs/OPERATIONS.md). Secrets, imagen y volumen: [deploy/README.md](deploy/README.md).

![[desk/atoms/atom-modelo-de-ramas.md]]
![[desk/atoms/atom-capas-de-verificación-y-release.md]]
