---
id: task-ui-foundations
title: UI foundations — navegación unificada, estilo flow-editor, hotkeys globales
status: draft
tags:
- ui
- foundation
- navigation
- hotkeys
---

## Rationale

El seed UI (desk/drawer/tasks/seed-ui-correcciones-y-vistas.md) define 10 áreas
de reorganización. Esta task implementa las bases compartidas que TODAS las
vistas necesitan antes de que ninguna pueda cambiar: sistema de diseño único,
navegación unificada, hotkeys globales, renombres de rutas, y el deshardcodeo
del placeholder. Sin esto, las tasks B/C/D/E operan sobre supuestos
contradictorios.

Fuentes:
- desk/drawer/tasks/seed-ui-correcciones-y-vistas.md (§0, §1, §4, §5.6, §5.7, §6.8, §8)
- frontends/UI-GUIDE.md (§0, §1, §6, §7, §8)
- frontends/flow_editor/index.html (estilo de referencia)

## Goal

Una sola topbar de navegación con nombres nuevos, paleta flow-editor aplicada
a todas las UIs, hotkeys compartidas funcionando en flow y mindmap, rutas
renombradas con redirects, placeholder del input desde config,
y el mapa léxico de tooltips listo para usar.

## Scope IN

1. **Sistema de diseño compartido** (`frontends/shared/`):
   - `theme.css` actualizado con todos los tokens de la UI-GUIDE §0.
   - `hotkeys.js` — implementación compartida de la tabla de hotkeys (§6.8).
   - `glossary.js` — mapa léxico `{kind → descripción 1-2 líneas}` para
     tooltips (handout, interaccion_simple, grounding atoms, etc.).
   - `tooltip.js` — utilidad de tooltip (hover 300ms, overlay, sin modal).

2. **Navegación global** (`frontends/chat/index.html` y todas las UIs):
   - Una sola topbar (`data-testid="nav-topbar"`) con links:
     Chat, Flow, Mindmap, Users.
   - Eliminar la sidebar de navegación duplicada del chat.
   - Brand y labels desde `/api/config` (cero hardcode).
   - Link activo resaltado.

3. **Renombres de rutas** (`frontends/chat/app.py`):
   - Nuevas rutas: `/flow`, `/mindmap`, `/users`.
   - Redirects 301 desde las viejas (`/conversation_flow_editor`,
     `/taxonomy_explorer`, `/profiling_viewer`, `/viz`).
   - `<title>` HTML actualizado en cada vista.

4. **Placeholder del input** (`kb_agent/project_config.py`):
   - Agregar `input_placeholder` a la sección `ui:` de project.config.yaml.
   - Exponer en `ProjectConfig.to_public_dict()`.
   - La UI lo lee y setea (neutral: "Escribe tu mensaje...").

5. **Tests** (`tests/ui/test_ui_guide.py`):
   - Marcar como `xfail` los tests de secciones 0, 1, 6, 7, 8 que validan
     las bases (config, nav, hotkeys, tooltips, endpoints).
   - Verificar que el `base_url` fixture funciona con las rutas nuevas.

## Scope OUT

- NO modificar el contenido del chat inspector (sección 2) — es task B.
- NO modificar el contenido de mindmap (sección 4) — es task C.
- NO modificar flow (sección 3) ni users (sección 5).
- NO implementar subflows ni drag & drop ni tools list en flow.
- NO fusionar embeddings con mindmap (solo crear rutas).

## Implementation Path

Fase 1 — Sistema de diseño + hotkeys + glossary:
```
1. git checkout -b task/ui-foundations  # desde dev limpio
2. Editar frontends/shared/theme.css: todos los tokens UI-GUIDE §0.
3. Crear frontends/shared/hotkeys.js.
4. Crear frontends/shared/glossary.js + frontends/shared/tooltip.js.
```

Fase 2 — Navegación + renombres:
```
1. Editar frontends/chat/index.html: reemplazar header+sidebar por una
   solo topbar (data-testid="nav-topbar"). Brand y labels de /api/config.
2. Editar frontends/chat/app.py: agregar rutas /flow /mindmap /users,
   redirects 301 de las viejas.
3. Editar frontends/flow_editor/index.html: import shared/*, topbar nueva.
4. Editar frontends/taxonomy/index.html: topbar nueva.
5. Editar frontends/profiling/index.html: topbar nueva.
6. Editar frontends/viz/index.html: topbar nueva (aunque se fusione luego).
```

Fase 3 — Placeholder:
```
1. Agregar ui.input_placeholder a project.config.yaml (default "Escribe tu
   mensaje...").
2. Agregar a ProjectConfig.to_public_dict() en kb_agent/project_config.py.
3. Editar frontends/chat/index.html: leer de /api/config y setear placeholder.
```

Fase 4 — Tests:
```
1. En tests/ui/test_ui_guide.py: xfail en tests de secciones 0, 1, 6, 7, 8.
2. SKIP_LLM_TESTS=1 pytest tests/ui/test_ui_guide.py -q — deben fallar
   (xfail) o pasar si la UI ya está implementada parcialmente.
```

## Validation

Antes de cada fase:
```
SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration -q  # 141+ pasan
```

Después de cada fase:
```bash
SKIP_LLM_TESTS=1 python -m pytest tests/ui/test_ui_guide.py -q --tb=short -x -k "seccion_0 or seccion_1 or test_config_"
# Deben fallar con xfail (la UI no está implementada)
# Si pasan inesperadamente, la task está hecha

# Verificar redirects:
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:<port>/conversation_flow_editor  # 301
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:<port>/flow                      # 200

# Verificar placeholder:
curl -s http://127.0.0.1:<port>/api/config | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'input_placeholder' in d, 'falta placeholder en config'"

# Verificar hotkeys global:
curl -s http://127.0.0.1:<port>/flow  | grep -c "hotkeys.js"  # 1
curl -s http://127.0.0.1:<port>/mindmap | grep -c "hotkeys.js"  # 1
```

## Done When

- [ ] `frontends/shared/hotkeys.js` existe y se importa en flow y mindmap.
- [ ] `frontends/shared/glossary.js` existe, contiene entradas para handout,
      interaccion_simple, obtencion_datos, llamado_tool, grounding_atoms,
      completion_condition, allowed_transitions, required_slots, system_turn.
- [ ] `frontends/shared/tooltip.js` existe y tooltips aparecen en flow.
- [ ] Una sola topbar con `data-testid="nav-topbar"` visible en /, /flow,
      /mindmap, /users. Sin sidebar de navegación duplicada.
- [ ] Link activo resaltado (data-active="true" o clase active).
- [ ] Brand y labels de /api.config, no hardcodeados.
- [ ] `/flow` sirve el flow editor, `/conversation_flow_editor` redirige 301.
- [ ] `/mindmap` sirve el taxonomy explorer, `/taxonomy_explorer` y `/viz`
      redirigen 301.
- [ ] `/users` sirve el profiling viewer, `/profiling_viewer` redirige 301.
- [ ] `<title>` de cada html actualizado (Chat · Flow · Mindmap · Users).
- [ ] Placeholder del input no contiene "pizza", viene de /api/config.
- [ ] `project_config.py` expone `input_placeholder` en `to_public_dict()`.
- [ ] Los tests xfail en test_ui_guide.py reportan el número esperado de
      xfails (ninguno inesperadamente passed).

## files:

- M: frontends/shared/theme.css
- A: frontends/shared/hotkeys.js
- A: frontends/shared/glossary.js
- A: frontends/shared/tooltip.js
- M: frontends/chat/index.html
- M: frontends/chat/app.py
- M: frontends/flow_editor/index.html
- M: frontends/taxonomy/index.html
- M: frontends/profiling/index.html
- M: frontends/viz/index.html
- M: kb_agent/project_config.py
- M: project.config.yaml
- A: tests/ui/test_ui_guide.py