# Knowledge Base — Guía de modelación

## Taxonomía de modelos

Cada modelo SLDB corresponde a un tipo de conocimiento distinto.
No todos los átomos son iguales — la forma de sus campos determina el modelo.

### Modelos actuales

| Modelo | atom_type | Para qué | Campos clave |
|---|---|---|---|
| `DomainAtom` | domain | Hechos de negocio (carta, horarios, catálogo) | id, title, answer, tags, domain_ref |
| `RuleAtom` | rule | Reglas condicionales de comportamiento | id, title, answer, conditions, applies_to |
| `ToolAtom` | tool | Schema JSON de APIs externas | id, title, description, parameters |
| `TraitAtom` | trait | Descriptores de perfil de usuario (sin answer) | id, title, description, category |
| `ConversationStep` | step | Nodos del diagrama de conversación | instructions, required_slots, allowed_transitions, grounding_atoms |
| `SelfDeclaration` | self | Declaración de identidad (whoami) | id, title, statement |
| `StyleGuide` | style | Guía de estilo conversacional | tone, language_register, phrase_preferences, length_guidelines |
| `CapabilityBoundary` | boundary | Límites de capacidad y escalación | restriction, conditions, escalation |
| `StrategyRule` | strategy | Estrategia general de interacción | goal, approach, priorities |
| `FallbackRule` | fallback | Respuesta ante contexto vacío | fallback_message, conditions |

### Categorías self.* no son un modelo — son 3

| Tag self.* | Modelo real | Contenido |
|---|---|---|
| `self:whoami` | `SelfDeclaration` | Quién soy, para quién trabajo |
| `self:estilo` | `StyleGuide` | Tono, registro, fraseo, longitud |
| `self:limites` | `CapabilityBoundary` | Qué no puedo hacer, cómo escalar |

## Heurística de modelación

Crear modelo nuevo si se cumple **al menos una**:

1. **Forma de campo distinta** — el tipo tiene un campo que ningún otro modelo tiene
   - Ej: `ToolAtom.parameters` (JSON schema), `StyleGuide.language_register`, `CapabilityBoundary.escalation`
2. **Comportamiento de compilación distinto** — el Ontologizador trata este tipo de forma diferente
   - Ej: `ConversationStep` va al KGDB flow_node; `TraitAtom` se resuelve contra SQL por user_id
3. **Validación distinta** — requiere reglas que no aplican a otros
   - Ej: `ToolAtom.parameters` debe ser JSON válido; `DomainAtom.answer` no vacío

Usar variante de modelo existente (no crear nuevo) si es:

| Concepto | Modelo que lo cubre | Se distingue por |
|---|---|---|
| Clarificación | `RuleAtom` | tags: conversation:clarification |
| Confirmación | `RuleAtom` | tags: conversation:confirmation |
| Escalation | `CapabilityBoundary` | conditions + escalation |
| Error recovery | `RuleAtom` | tags: conversation:recovery |
| Proactividad | `RuleAtom` | conditions con trigger |
| Saludo / Cierre | `SelfDeclaration` + `StyleGuide` | statement + phrase_preferences |
| Chitchat | `CapabilityBoundary` | restriction sobre conversación casual |

## Ciclo de vida de un modelo

```
1. Identificar forma de campo única → crear clase StructuredNLDoc
2. Definir __semantics__ y __template__ con marcadores ⸢rev•⸥ / ⸢optrev•⸥
3. Agregar a kb_agent/models/knowledge/ y exportar en __init__.py
4. Validar: python -c "from kb_agent.models.knowledge import ..."
5. Registrar: sldb models add kb_agent.models.knowledge:<Model> --store knowledge/.sldb
6. Actualizar: sldb stores update --store knowledge/.sldb --pythonpath .
```

## Anti-patrones

- No usar `AtomDoc` de deskops para KB de dominio — es para workflow/arquitectura
- No mezclar dos formas de campo en un mismo modelo con un campo `type` enum
  - (Ej: lo que era SelfDeclaration con declaration_type cubriendo whoami + estilo + limites)
- No poner `atom_type` como tag en vez de campo — el Ontologizador filtra por modelo, no por tag
- No crear modelos para conceptos que son variantes de tags de modelos existentes