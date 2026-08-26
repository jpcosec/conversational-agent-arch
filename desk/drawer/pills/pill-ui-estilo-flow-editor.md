---
id: pill-ui-estilo-flow-editor
title: Estilo visual — alinear con Flow Editor
status: active
tags:
- pill
- ui
- style
- frontend
---

## Doctrina

Toda la UI debe parecerse visualmente a `frontends/flow_editor/index.html`.
No hay excepciones por vista. La paleta compartida está en
`frontends/shared/theme.css` y se aplica a:

- **Fondo página**: `#0a0a0f`.
- **Paneles**: `#0d1526` o gradient `#12121a→#0a0a0f`.
- **Bordes**: `rgba(245,240,232,.08)` normal; `rgba(212,165,116,.18)` en
  cards y elementos con accent.
- **Texto**: `#f5f0e8`. Muted: `rgba(245,240,232,.45)`.
- **Accent**: `#d4a574` (ámbar).
- **Tipografía**: `'Inter', sans-serif` (cuerpo), `'JetBrains Mono', monospace`
  (código/metadatos). Mono 11px, contenido 13-15px.
- **Cards**: `border: 1px solid rgba(212,165,116,.18)`, `border-radius: 14px`,
  `padding: 16px`. Hover: `border-color: #d4a574` + `box-shadow`.
- **Tags/chips**: `font-size: 10px`, `px-1.5 py-0.5`, `border-radius: 8px`.
- **Botones/links**: `font-family: 'JetBrains Mono'`, `font-size: 11px`,
  `padding: 6px 12px`.
- **Scrollbar**: personalizada, oscura, delgada (misma que flow editor).
- **Transiciones**: `all .15s` o `transition: all .18s`.

## Prohibido

- **NO** Tailwind utility classes en markup nuevo (CSS plano, como flow).
- **NO** fondos blancos o gris claro.
- **NO** textos grises (#666, #999) — usar `var(--muted)` con opacidad.
- **NO** border-radius > 16px.
- **NO** sombras grandes o difusas (usar blur-2xl sutil como flow).

## Referencia

`frontends/flow_editor/index.html` líneas 1-80.
`frontends/shared/theme.css` (líneas 1-171).