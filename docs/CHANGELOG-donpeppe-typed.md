# Changelog — Don Peppe migrado a modelos tipados

Migración de `tests/knowledge/` (KB de prueba Don Peppe) de `AtomDoc` genérico
a los 10 modelos `StructuredNLDoc` tipados de `kb_agent/models/knowledge/`.

## Antes → Después

- **Antes**: 7 átomos `AtomDoc`, con `atom_type` como **tag**, sin átomos de
  configuración del agente (self/style/boundary/strategy/fallback/steps).
- **Después**: 15 átomos tipados, `atom_type` como **campo** del modelo,
  seleccionables por `type.knowledge.<tipo>`.

## Átomos resultantes (15)

| Átomo | Modelo | atom_type |
|---|---|---|
| atom-donpeppe-carta | DomainAtom | domain |
| atom-donpeppe-horarios | DomainAtom | domain |
| atom-donpeppe-ubicacion | DomainAtom | domain |
| atom-donpeppe-promos | DomainAtom | domain |
| atom-donpeppe-regla-reservas | RuleAtom | rule |
| atom-donpeppe-tool-reserva | ToolAtom | tool |
| atom-trait-sin-gluten | TraitAtom | trait |
| atom-trait-vegetariano | TraitAtom | trait |
| self-donpeppe | SelfDeclaration | self |
| style-donpeppe | StyleGuide | style |
| boundary-donpeppe | CapabilityBoundary | boundary |
| strategy-donpeppe | StrategyRule | strategy |
| fallback-donpeppe | FallbackRule | fallback |
| step-donpeppe-onboarding | ConversationStep | step |
| step-donpeppe-booking | ConversationStep | step |

## Cambios concretos

- `atom_type` movido de tag → campo del modelo (por átomo).
- Eliminado `atom-heladeria-carta` (otro negocio — una KB = un negocio).
- Añadidos átomos de configuración del agente copiando estructura de antonia:
  self, style, boundary, strategy, fallback, 2 steps.
- Convención de tags: `system:donpeppe` + tags semánticos por dominio.
- Steps con campos tipados: `allowed_transitions`, `grounding_atoms`,
  `required_slots`, `completion_condition`.

## ⚠️ Alcance a confirmar

El usuario indicó que **inventé contenido nuevo** (ubicación, promos, y los
átomos de config completos) en vez de solo migrar la *forma* de los 7 átomos
existentes. Pendiente confirmar si se mantiene la KB expandida o se revierte a
solo los 7 originales migrados. Ver `docs/HANDOFF-kb-typed-models.md` §3.2.

## Verificación

```
sldb stores check --store .sldb   → PASS: store integrity (15 átomos, 0 missing)
```

Selección por tipo verificada:
```
type.knowledge.domain   → 4 átomos
type.knowledge.rule     → 1
type.knowledge.tool     → 1
type.knowledge.trait    → 2
type.knowledge.step     → 2
type.knowledge.self/style/boundary/strategy/fallback → 1 c/u
```

Campos tipados accesibles (ej. `self-donpeppe.statement`,
`step-donpeppe-booking.allowed_transitions` / `.grounding_atoms`).
