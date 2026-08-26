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
- NO modificar el contenido interno de mindmap (árbol, layouts, search,
  toolbar — sección 4) — es task C.
- NO modificar el contenido interno de flow (subflows, edición, palette,
  tools — sección 3) — es task D.
- NO modificar el contenido de users (perfil, eventos, conversaciones —
  sección 5) — es task E.
- NO implementar subflows ni drag & drop ni tools list en flow.
- NO fusionar embeddings con mindmap como contenido (esa fusión es task C).
  Esta task solo crea la RUTA `/mindmap` y redirige `/viz` → `/mindmap`.

**SÍ se permite** en flow/mindmap/users:
- Añadir `<script src="/static/hotkeys.js">` y `<script
  src="/static/glossary.js">` al `<head>` del HTML.
- Reemplazar la topbar/header existente por la nueva topbar compartida.
- Añadir `data-testid` a la topbar.
- NO tocar el cuerpo, el canvas, el inspector, los nodos, ni la lógica JS
  de cada vista (excepto importar y llamar `initHotkeys()`).

## Implementation Path

### Convenciones compartidas

Los archivos en `frontends/shared/` se sirven bajo `/static/` gracias a
`app.py` línea ~131 (`app.mount("/static", StaticFiles(directory=SHARED_DIR))`).
En cada HTML usar:
```html
<script src="/static/hotkeys.js"></script>
<script src="/static/glossary.js"></script>
<script src="/static/tooltip.js"></script>
```

El brand y labels se obtienen con `fetch('/api/config')` client-side al
cargar la página y se reemplazan en el DOM (sin template engine).

Los `<title>` se editan DIRECTAMENTE en cada archivo `.html` (no server-side).

**hotkeys.js API (contrato entre shared/* y cada vista):**
```
function initHotkeys(options: {
  element: HTMLElement,
  onSearch: () => void,     onDelete: () => void,
  onAddChild: () => void,   onAddSibling: () => void,
  onLinkHorizontal: () => void, onCollapse: () => void,
  onFocus: () => void,      onLayout: (n: 1|2|3) => void,
  onHelp: () => void,       onCancel: () => void,
}): void
```
No capturar hotkeys si un input/textarea tiene el foco.
Overlay de ayuda con `data-testid="hotkey-overlay"`.

**glossary.js estructura:**
```
// window.__glossary: { [concept: string]: string }
// conceptos required: handout, interaccion_simple, obtencion_datos,
// llamado_tool, grounding_atoms, completion_condition, allowed_transitions,
// required_slots, system_turn, tool_call, fallback, breakpoint_miss,
// context_compilation, scenario
```

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

```
from starlette.responses import RedirectResponse

# En create_app(), tras las rutas existentes:
OLD_ROUTES = {
    "/conversation_flow_editor": "/flow",
    "/taxonomy_explorer": "/mindmap",
    "/profiling_viewer": "/users",
    "/viz": "/mindmap",
}
for old_path, new_path in OLD_ROUTES.items():
    @app.get(old_path)
    @app.get(old_path + "/")
    async def _redirect(request: Request, dest: str = new_path):
        return RedirectResponse(url=dest, status_code=301)
```

Fase 3 — Placeholder:
```
1. En project.config.yaml, bajo ui: agregar: input_placeholder: "Escribe tu mensaje..."
2. En kb_agent/project_config.py, en ProjectConfig:

@dataclass
class ProjectConfig:
    ...
    input_placeholder: str = "Escribe tu mensaje..."

   En to_public_dict() agregar: "input_placeholder": self.input_placeholder,
```

Fase 4 — Tests:
```
1. En tests/ui/test_ui_guide.py: envolver los tests de secciones 0, 1, 6, 7, 8
   con @pytest.mark.xfail(reason="UI no redisenada — se implementa en esta task").
   Los tests de secciones 2 (chat), 3 (flow), 4 (mindmap), 5 (users) NO se
   marcan xfail y FALLARAN — eso es esperado y aceptable para esta task.
   Done When NO exige que esos tests pasen; solo que los xfail reporten
   como xfail (ninguno pasa inesperadamente).

   Usar xfail individual por funcion (no pytestmark de modulo), para no marcar
   toda la suite.

2. Ejecutar: SKIP_LLM_TESTS=1 python -m pytest tests/ui/test_ui_guide.py -q
   — los xfail deben aparecer como "xfailed" (no "passed", no "failed").
   Los no-xfail de secciones 2-5 fallaran (reporte: X failed, X xfailed).
```

## Validation

Antes de cada fase:
```
SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration -q  # 141+ pasan
```

Después de cada fase (puerto aleatorio del fixture — NO se fija manualmente):
```bash
SKIP_LLM_TESTS=1 python -m pytest tests/ui/test_ui_guide.py -q --tb=short -k "test_config_ or test_nav or test_hotkey or test_api_tools or test_api_events"
# Los xfail de secciones 0/1/6/7/8 deben salir como "xfailed" (no "PASSED")
# Los no-xfallidos de las demas secciones (api_tools, api_events, ...) deben
# salir como pasados si el endpoint existe, o fallar si no — aceptable

# Verificar import de shared/ en HTML (sin servidor):
# grep -c "hotkeys.js" frontends/flow_editor/index.html  → 1
# grep -c "hotkeys.js" frontends/taxonomy/index.html     → 1 (mindmap)
# grep -c "hotkeys.js" frontends/viz/index.html          → 1 (redirige a mindmap)
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