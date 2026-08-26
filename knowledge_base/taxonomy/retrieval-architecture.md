# Knowledge Base — Arquitectura de recuperación y planos de ejecución

## 1. Los dos planos de ejecución

La KB opera en **dos planos que nunca se cruzan en runtime**.

### Plano de runtime (agentes conversacionales) — read-only

- Actores: Conversador, Compilador, Perfilador.
- Consumen la KB **ya enriquecida** vía `knowledge explore/self/step/traits/show`.
- **Nunca** calculan embeddings, reordenan jerarquías, ni escriben proxies.
- Latencia baja, determinista, sin side-effects sobre la KB.
- Asumen que el frontmatter ya tiene embeddings/proxies calculados.

### Plano de fortalecimiento (offline) — read-write, paralelo

- Actor: `knowledge` CLI en modo batch. Ningún agente conversacional.
- Corre **entre** conversaciones, nunca durante un turno.
- Enriquece, indexa y promueve la KB.
- Incluye al **Reflector**, que corre sobre historial de conversaciones guardado (SQL `ChatHistory`).

### La frontera

| | Runtime | Offline |
|---|---|---|
| Quién | agentes conversacionales | `knowledge` CLI (batch) |
| Modo | read-only | read-write |
| Sobre la query | embed in-situ, filtrar, rankear | — |
| Sobre la KB | nada | enriquece, indexa, promueve |
| Timing | por turno | paralelo, asíncrono |

### Ciclo completo

```
runtime:   conversación → ChatHistory (SQL)
                              │
offline:   Reflector lee ChatHistory ──> propone atoms (status:proposed)
           humano/pipeline promueve ───> atoms activos
           index embeddings/hierarchy/proxies ──> KB enriquecida
                              │
runtime:   siguiente conversación consume KB mejorada
```

La KB se fortalece **entre** conversaciones, nunca **durante**.

---

## 2. Los cinco ejes de activación

Cada namespace de tag tiene un **eje de activación distinto** — una lógica de
recuperación diferente. El Compilador no puede tratar todo con una sola estrategia.

| Namespace | Se activa por | Estrategia de recuperación | Comando |
|---|---|---|---|
| `self:*` | siempre (constante) | cargar todo, siempre | `knowledge self` |
| `conversation:*` | estado de sesión | navegar desde flow_node | `knowledge step next` |
| `domain:*` | relevancia a la pregunta | búsqueda por relevancia | `knowledge explore` |
| `user:traits.*` | identidad del usuario | resolver por FK desde SQL | `knowledge traits` |
| `source:*` | nunca (metadata) | no se recupera (trazabilidad) | N/A |

### Detalle funcional

- **`self:*`** — declaraciones sobre el agente. Constantes del contexto: identidad
  (`whoami`), estilo, límites, tools. No dependen del input del usuario.
- **`conversation:*`** — máquina de flujo. Opera sobre el estado (flow_node en SQL).
  `conversation:steps.*` es jerarquía navegable (KGDB `semantic_parent`).
  `fallback`/`strategy` se activan condicionalmente.
- **`domain:*`** — conocimiento factual recuperable. Único namespace que se filtra
  por la consulta del usuario. `domain:reglas.*` acota lo permitido.
- **`user:traits.*`** — catálogo referenciado desde SQL (`UserTraits.trait_id →
  TraitAtom`). Multi-usuario: un trait aplica a muchos usuarios.
- **`source:*`** — metadata pura. No participa en la compilación. Trazabilidad para
  el Reflector (marcar propuestas, filtrar lo no-promovido).

---

## 3. `explore` como caja de herramientas del Compilador

`explore` no es solo navegación de grafo. Es **la caja de herramientas completa de
recuperación** que tiene el Compilador para encontrar info relevante — y para decidir
**cuándo NO hay info relevante** (anti-alucinación).

### Capas de recuperación

| Capa | Fuente | Cuándo |
|---|---|---|
| Navegación KGDB | grafo de referencias transversales | relaciones semánticas entre atoms |
| Jerarquía enciclopédica | domain atoms ordenados en árbol | drill-down temático |
| Fuzzy search | nombres/tags/títulos | match aproximado rápido |
| Embeddings | vector offline (frontmatter) vs vector in-situ (query) | similitud semántica real |
| Proxies de frontmatter | metadata indexable | filtrar sin leer el body |

### Principio central: frontmatter como proxy de indexación

El Compilador **no lee la KB completa**. Cada atom lleva en su frontmatter señales
suficientes para decidir relevancia **sin abrir el `answer`**:

```yaml
---
id: atom-donpeppe-carta
title: Carta Don Peppe
summary: "Catálogo de pizzas con precios"       # proxy textual
embedding: [0.021, -0.13, ...]                   # vector offline precalculado
parent: domain:catalogo                          # posición jerárquica
semantic_anchors: [pizza, precio, menu, comida]  # proxies de match
tags: [...]
---
```

### Flujo de `explore` para una consulta

```
1. Embed la query in-situ
2. Filtrar candidatos por proxies de frontmatter (embedding sim + fuzzy + tags)
3. Navegar KGDB para expandir referencias transversales de los candidatos
4. Rankear
5. Si el top score < umbral → "no hay info relevante" (anti-alucinación)
```

---

## 4. Comandos por plano

### Runtime (agentes conversacionales, read-only)

```
knowledge explore <query>       # caja de herramientas de recuperación (domain:*)
knowledge self                  # identidad + estilo + límites (self:*)
knowledge step next --user <id> # navegación por estado (conversation:*)
knowledge traits --user <id>    # resolución por identidad (user:traits.*)
knowledge show <atom_id>        # atom completo por id
knowledge context --user <id>   # todo-en-uno del estado de sesión
```

### Offline (knowledge CLI, batch — nunca un agente conversacional)

```
knowledge index embeddings      # calcula y escribe embeddings al frontmatter
knowledge index hierarchy       # construye jerarquía enciclopédica en KGDB
knowledge index proxies         # genera summary + semantic_anchors
knowledge reflect --db <sql>    # Reflector: propone atoms desde ChatHistory
knowledge promote <atom_id>     # promueve propuesta del Reflector a activo
```

---

## 5. Estado actual y pendientes

### Hecho

- 10 modelos SLDB propios (`kb_agent/models/knowledge/`).
- KB reubicada: `knowledge/` (reusable) + `tests/knowledge*` (casos de prueba).
- CLI runtime: `explore` (navegación KGDB), `self`, `step next`, `traits`, `show`,
  `context`, `propose`.
- Navegación tag-céntrica en KGDBReader (root_tags, child_tags, docs_for_tag, etc.).
- 18 unit tests del CLI.

### Pendiente (plano offline)

1. **Campos de frontmatter de indexación** en los modelos: `summary`, `embedding`,
   `parent`, `semantic_anchors`. (Prerequisito de todo el indexado.)
2. **Pipeline offline de embeddings**: `knowledge index embeddings`.
3. **Jerarquía enciclopédica en KGDB**: domain atoms con `semantic_parent` real.
4. **`explore` multi-estrategia**: combinar las 5 capas + umbral de corte
   (anti-alucinación).
5. **Embedder in-situ** para la query.
6. **Cablear Reflector a `knowledge`**: `knowledge reflect` sobre `ChatHistory`.
7. **`knowledge promote`**: promoción de propuestas.
