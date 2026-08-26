---
id: pill-ui-no-build-cdn
title: Sin build step — CDN only
status: active
tags:
- pill
- ui
- build
- constraints
---

## Doctrina

Ninguna UI del runtime requiere build step. Todo se sirve como HTML/JS/CSS
estático desde CDN.

- **React**: via `esm.sh` (@xyflow/react, htm, dagre, React 18).
- **Tailwind**: via CDN plugin (`cdn.tailwindcss.com`). Prohibido en markup
  nuevo (usar CSS plano), pero el existente puede mantenerse mientras no se
  toque.
- **Fuentes**: Google Fonts CDN (Inter, JetBrains Mono, Material Symbols).
- **Tema**: `frontends/shared/theme.css` compartido (no CDN).

## Consecuencias

- Los tests UI necesitan internet (documentado en test_playwright_smoke.py).
- Sin npm, sin webpack, sin vite, sin build script.
- El fixture de test levanta uvicorn in-process (no build step que verificar).
- Para probar cambios: recargar el navegador (hot reload manual).