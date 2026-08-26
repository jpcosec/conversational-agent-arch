---
id: handoff-knowledge-org
title: Organización automática de átomos en la KB
status: open
tags:
- handoff
- knowledge
- sldb
---

## Problema

Hoy todos los átomos de la KB se escriben en un solo directorio plano:

```
knowledge/atoms/
├── atom-donpeppe-carta.md
├── self-whoami.md
├── step-onboarding.md
├── style-donpeppe.md
├── trait-vegetariano.md
└── ...
```

Sin organización por namespace, sin subdirectorios. Esto escala mal: 100+ átomos son inmanejables en un solo folder.

## Objetivo

Organizar automáticamente los átomos usando el árbol de tags semánticos como estructura de directorios.

## Regla de derivación de ruta

Cada átomo tiene tags semánticos namespaced (ej. `self:whoami`, `conversation:steps.onboarding`, `domain:catalogo`, `user:traits.vegetariano`).

La ruta del archivo se deriva del **primer tag semántico significativo** (excluyendo `type.*`, `workspace.*`, `source:*`).

```
tag                               → directorio
self:whoami                       → knowledge/self/whoami/
self:estilo                       → knowledge/self/estilo/
self:limites                      → knowledge/self/limites/
self:tools                        → knowledge/self/herramientas/
conversation:steps.onboarding     → knowledge/conversation/steps/onboarding/
conversation:steps.booking        → knowledge/conversation/steps/booking/
conversation:fallback             → knowledge/conversation/fallback/
conversation:strategy             → knowledge/conversation/strategy/
domain:catalogo                   → knowledge/domain/catalogo/
domain:horarios                   → knowledge/domain/horarios/
domain:reglas.reservas            → knowledge/domain/reglas/reservas/
user:traits.celiaco               → knowledge/user/traits/celiaco/
user:traits.vegetariano           → knowledge/user/traits/vegetariano/
```

**Transformación:** `:` → `/`, `.` → `/`

Si el átomo tiene múltiples tags, usar el primer tag cuyo namespace no sea `type`, `workspace` ni `source`.

## Árbol de tags original (del que se deriva)

```
self:*                    → Identidad y personalidad del agente
  self:whoami
  self:estilo
  self:herramientas       (originalmente self:tools)
  self:limites

conversation:*            → Flujo y reglas de interacción
  conversation:steps.*
    conversation:steps.onboarding
    conversation:steps.booking
  conversation:fallback
  conversation:strategy

domain:*                  → Conocimiento del negocio (único por KB)
  domain:catalogo
  domain:horarios
  domain:reglas.*

user:traits.*             → Catálogo de rasgos de usuario
  user:traits.celiaco
  user:traits.vegetariano

source:*                  → Procedencia (metadata, no genera directorio)
```

## Qué hay que implementar

### 1. `knowledge organize` (CLI)

Comando que reorganiza los átomos existentes:

```
knowledge organize --kb <path> [--dry-run]
```

Por cada átomo en `knowledge/atoms/`:
1. Leer el átomo (SLDB extract)
2. Derivar ruta destino desde el primer tag semántico significativo
3. Crear directorios si no existen
4. Mover el archivo .md
5. Re-trackear en SLDB: `sldb docs untrack <old>` + `sldb docs track <new>`
6. Opcional: `sldb stores update`

`--dry-run` solo muestra lo que haría sin mover nada.

### 2. `knowledge propose` (actualizar)

Cuando `knowledge propose` crea un átomo nuevo, debe escribirlo directamente en la ruta derivada, no en `atoms/` plano.

### 3. Regla de ruta como función

Implementar como función pura testable:

```python
def derive_path(kb_root: Path, atom_id: str, tags: list[str]) -> Path:
    """
    Dado un atom_id y sus tags, devuelve la ruta destino.
    
    Ej: derive_path("/kb", "step-onboarding", ["conversation:steps.onboarding"])
        → Path("/kb/conversation/steps/onboarding/step-onboarding.md")
    """
```

## Validación

- `tests/test_knowledge_cli.py` — test unitario de `derive_path()` con múltiples tags
- `knowledge organize --dry-run` contra `tests/knowledge/` y `tests/knowledge_antonia/`
- Verificar que SLDB re-track funciona: `sldb find <atom>` después de organizar

## Contexto técnico

- Los átomos usan modelos SLDB propios en `kb_agent.models.knowledge.*`
- Para extraer datos: `sldb.runtime.validation.extract_model_data(modelo, md_text)`
- Para trackear: `sldb docs track <path> --model <Model> --store <store> --pythonpath .`
- Para untrack: `sldb docs untrack <id> --store <store>`
- Tags excluidos de la ruta: `type.*`, `workspace.*`, `source:*`
- Tags de ejemplo en `tests/knowledge/` y `tests/knowledge_antonia/`
- CLI existente en `knowledge_base/` — agregar comando `organize`
