---
id: atom-topologia-de-despliegue
title: "Topolog\xEDa de Despliegue (Modal)"
five_wh_one_plus: what
tags:
- layer:ops
- role:boundary
provenance: architecture-audit
---

# Topología de Despliegue (Modal)

## Answer

Despliegue serverless en Modal (`deploy/modal_app.py`). El runtime completo (ASGI de FastAPI sirviendo las 5 UIs y los endpoints webhooks) se empaqueta junto con la Base de Conocimiento activa y se expone a internet, escalando desde cero.
