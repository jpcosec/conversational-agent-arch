# KB Doctrine

## Principios

### 1. Una KB = un negocio

Cada knowledge base responde a un solo negocio/escenario. No se mezclan dominios de negocio distintos en una misma KB.

### 2. KB es conocimiento, no estado

El sistema es **stateless**. El estado vivo (sesión, historial, slots capturados, contexto de turnos anteriores) vive en SQL, no en la KB. La KB solo contiene conocimiento semántico reutilizable.

### 3. Multi-usuario, traits categorizados

Los traits de usuario no son fichas por usuario. Son un **catálogo de rasgos** (`user:traits.*`) que aplican a múltiples usuarios. SQL relaciona usuarios concretos con traits del catálogo.

### 4. Selección por tag, no por lectura de contenido

El compilador selecciona átomos por su **árbol semántico de tags**, sin necesidad de leer el `answer`. El contenido se consume solo cuando el átomo ya fue seleccionado.

### 5. Tools son un tipo, no un dominio

`atom_type:tool` identifica tools (tienen schema JSON). El tag semántico `self:tools` las agrupa, pero la selección las trata como tools, no como facts inline.

---

## Árbol de tags semánticos

```
self:*                       → Identidad y personalidad del agente
  self:whoami                → Quién soy, qué soy
  self:estilo                → Tono, personalidad, registro
  self:tools                 → Tools disponibles (atom_type:tool)
  self:limites               → Qué no puedo hacer

conversation:*               → Flujo y reglas de interacción
  conversation:steps.*       → Pasos del escenario (onboarding, booking, etc.)
  conversation:fallback      → Qué hacer cuando no hay contexto suficiente
  conversation:strategy      → Estrategia de interacción

domain:*                     → Conocimiento del negocio (único por KB)
  domain:catalogo            → Catálogo de productos/servicios
  domain:horarios            → Horarios de atención
  domain:reglas.*            → Reglas de negocio

user:traits.*                → Catálogo de rasgos de usuario (multi-usuario)
  user:traits.celiaco        → Cliente sin gluten
  user:traits.vegetariano    → Cliente vegetariano

source:*                     → Procedencia y metadata
  source:e2e                 → Creado en test E2E
  source:manual              → Escrito a mano
  source:reflect             → Generado por reflector
```

---

## Dimensiones de selección

Cada átomo tiene **dos ejes**:

| Eje | Ejemplo | Propósito |
|---|---|---|
| `atom_type` | domain, rule, tool, trait | Tipo de contenido (cómo se usa) |
| Tag semántico | `domain:catalogo`, `self:whoami` | Propósito (cuándo se selecciona) |

El compilador filtra por tag semántico para saber **qué** necesita, y usa `atom_type` para saber **cómo** tratarlo.

---

## Lo que NO va en la KB

| Concepto | Dónde vive | Razón |
|---|---|---|
| Sesión activa | SQL (`SessionState`) | Estado vivo, no conocimiento |
| Historial por usuario | SQL (`ChatHistory`) | Por usuario, anonimizado |
| Contexto de turno | SQL o SLDB doc por turno | Compilación, no fuente |
| Ficha de usuario | SQL (`Users`, `UserTraits`) | Relacional, no semántico |

---

## Relación KGDB ↔ SLDB

| Capa | Rol | Contenido |
|---|---|---|
| **KGDB** | Esqueleto | Nodos de flujo, transiciones (`flows_to`), relaciones (`grounded_by`, `uses_tool`) |
| **SLDB** | Contenido | `answer` de cada paso, reglas, facts, tools |

- KGDB dice qué paso va después de cuál.
- SLDB tiene el texto y semántica de cada paso (`conversation:steps.*`).
- El compilador resuelve los IDs de `grounded_by` contra SLDB para traer `title` + `answer` + `tags`.

---

## Ciclo de vida de un átomo

1. **Creación**: manual, por reflector, o por ingesta
2. **Indexación**: SLDB lo registra y lo hace buscable por tags
3. **Selección**: el compilador lo encuentra por tag semántico
4. **Consumo**: el conversador usa su `answer` como grounding
5. **Actualización**: se edita el Markdown, SLDB re-indexa