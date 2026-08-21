# KB Agent UI

## Levantar local

Desde esta carpeta:

```bash
cd /home/jp/proyectos/gemini_test/kb_agent_ui
python3 -m http.server 8080
```

Abrir:

```text
http://localhost:8080
```

## Archivos

- `index.html` — interfaz principal
- `atoms.json` — 90 átomos exportados desde `tutor_apoe/desk/atoms`

## Qué hace

- Renderiza markdown en el panel principal
- Muestra los átomos en sidebar derecho
- Permite buscar átomos por título, tag, id, path o contenido
- Click en átomo → abre el átomo renderizado en el panel principal
