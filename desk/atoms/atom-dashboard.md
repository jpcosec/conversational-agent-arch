---
id: atom-dashboard
title: Dashboard
five_wh_one_plus: what
tags:
- layer:frontend
- role:boundary
- topic:dashboard
provenance: frontends/dashboard/index.html
---

# Dashboard

## Answer

Vista `/dashboard` servida por `create_app` (frontends/chat/app.py) desde `frontends/dashboard/index.html`. Es un mock estático transcrito del diseño de referencia `docs/dashboard-reference.png` — KPIs, series y listas son sintéticos y la página lo declara con el chip "Datos de ejemplo" (`data-testid="dashboard-mock-chip"`). Está enlazada en la topbar de todas las vistas (`nav-dashboard`, etiqueta `nav_labels.dashboard`) y sólo consulta `/api/config` (marca, kb_label, labels de nav) y `/api/health` (estado); no lee métricas del runtime.
