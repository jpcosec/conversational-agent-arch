# knowledge_vitali — KB del negocio (fuente de verdad del runtime)

Esta carpeta ES la KB que consume el `kb_agent` en runtime. Una KB = un negocio.

## Doctrina de interacción con la KB

- **La interacción con la KB se hace SIEMPRE desde `knowledge/` (esta capa, `knowledge_vitali/`), no desde `desk/atoms/`.**
  - `desk/atoms/` es conocimiento del repo/proyecto (arquitectura, gobernanza) y alimenta docs (`README`, `docs/*`). NO es la KB del agente.
  - `knowledge_vitali/atoms/` son los KB-atoms runtime (modelos SLDB: SelfDeclaration, DomainAtom, RuleAtom, ConversationStep, StyleGuide, Boundary, Gate, Strategy, Fallback, AgentFraming, Tool, Trait) que el agente recupera por embeddings.
- **No hay generador intermedio.** Se eliminó `scripts/build_vitali_kb.py`. La KB no se "compila" desde un script ni desde `source/systemprompt.md`.
- **Para crear/editar/consultar KB-atoms usar los comandos SLDB directamente sobre este store** (`knowledge_vitali/.sldb`):

```bash
sldb docs create --model DomainAtom -o atoms/<id>.md <payload.yaml> --store knowledge_vitali/.sldb --pythonpath .
sldb docs update <doc> <payload> --store knowledge_vitali/.sldb --pythonpath .
sldb fields query <field> --store knowledge_vitali/.sldb --pythonpath .
sldb find <term> --in semantic --store knowledge_vitali/.sldb --pythonpath .
sldb stores check --store knowledge_vitali/.sldb
```

- `source/` guarda material fuente crudo (system prompt, crawl del sitio) usado como insumo humano para redactar atoms. No es leído por el runtime.

## Switch de negocio

- Este negocio se sirve con `PROJECT_CONFIG=project.vitali.yaml`.
- El multi-negocio es por branch/worktree; la arquitectura sólo reacciona a un negocio activo.
