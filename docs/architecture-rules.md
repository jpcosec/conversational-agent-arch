# Architecture Rules

Reglas firmes de diseño para el agente conversacional. No cambiar sin revisión explícita.

---

## R1. Conversador solo redacta

- No decide el tipo de turno (tool/fallback/NL).
- No conoce tools.
- No navega la KB.
- Entra: `CompiledDocument` sin tools → Sale: texto NL.
- Si `is_empty` → emite el texto de `conversation:fallback` que llegó en el contexto.

## R2. Orquestador decide tipo de turno

- Recibe `CompiledDocument` del compilador.
- Decide:
  - `is_empty` → responde con texto de `conversation:fallback` (sin pasar por conversador).
  - tool disponible + intención → ejecuta tool, reinyecta System Turn, luego llama al conversador para redactar.
  - NL → llama a `conversador.draft_nl(context)`.
- Orquestador no lee SLDB directo. Todo le llega del compilador.

## R3. Compilador decide step conversacional

- Lee `flow_node` del `SessionState` (vía orquestador).
- Consulta KGDB: `conversation:steps.*`, transiciones, grounding.
- Deriva el step actual y lo expone en `CompiledDocument`.
- El compilador produce un `CompiledDocument` **cerrado**: atoms completos (id, title, tags, body, role) sin necesidad de re-lectura del store.

## R4. Comportamiento del agente viene de la KB, no del código

| Comportamiento | Fuente en la KB |
|---------------|----------------|
| Identidad del agente | `self:whoami` |
| Estilo de comunicación | `self:estilo` |
| Límites | `self:limites` |
| Texto de fallback | `conversation:fallback` |
| Tools disponibles | `self:tools` (agrupa `atom_type:tool`) |
| Pasos conversacionales | `conversation:steps.*` (vía KGDB) |

Nada de esto está hardcodeado en Python. El orquestador y el conversador se configuran desde estos átomos.

## R5. Tools se descubren, no se hardcodean

- Las tools viven como `atom_type:tool` con tag `self:tools`.
- El compilador las incluye en `CompiledDocument.tools`.
- El orquestador las ejecuta por su schema, no por `if name == "..."`.

## R6. Nadie re-escribe la KB desde el runtime

- Leer SLDB ya modifica índices runtime (semantic_index, sections).
- Si hay que modificar la KB: directo sobre el Markdown, vía `sldb docs update`, o vía Reflector (batch).
- El orquestador no escribe el store.

## R7. Capas de datos — quién lee qué

| Agente | Lee SLDB | Lee SQL | Lee KGDB |
|--------|----------|---------|----------|
| Compilador | ✅ | ✅ traits | ✅ flow |
| Orquestador | ❌ | ✅ sesión, historial | ❌ |
| Conversador | ❌ | ❌ | ❌ |
| Perfilador | ✅ solo `user:traits.*` | ✅ UserTraits | ❌ |
| Reflector | ✅ solo `domain:*` + `rule` | ✅ ChatHistory | ❌ |

## R8. Selección por tag, no por lectura de contenido

- El compilador selecciona átomos por su tag semántico y `atom_type`.
- El contenido (`answer`) se consume solo después de seleccionado.
- Una KB = un negocio. No se filtra por scenario. Todos los `atom_type:domain` y `atom_type:rule` se traen.

## R9. Árbol de tags canónico

```
self:*                  → identidad y personalidad del agente
conversation:*          → flujo y reglas de interacción
domain:*                → conocimiento del negocio
user:traits.*           → catálogo de rasgos de usuario
source:*                → procedencia (metadata)
```

El reflector escribe `source:reflect`. El perfilador filtra por `user:traits.*`. El compilador trae todo lo demás por `atom_type`.

## R10. Dos dimensiones de selección por átomo

| Eje | Ejemplo | Propósito |
|-----|---------|-----------|
| `atom_type` | domain, rule, tool, trait | Tipo de contenido (cómo se usa) |
| Tag semántico | `domain:catalogo`, `self:whoami` | Propósito (cuándo se selecciona) |