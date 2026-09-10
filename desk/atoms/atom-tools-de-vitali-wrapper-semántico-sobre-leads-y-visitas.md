---
id: atom-tools-de-vitali-wrapper-semántico-sobre-leads-y-visitas
title: 'Tools de Vitali: wrapper semántico sobre leads y visitas'
five_wh_one_plus: how
tags:
- layer:runtime
- role:boundary
provenance: kb_agent/tools/leads.py
---

# Tools de Vitali: wrapper semántico sobre leads y visitas

## Answer

"Dos tablas SQL planas sin semántica de negocio (`kb_agent/models_sql/leads.py`, migración `f6a7b8c9d0e2`): `leads` (una fila por `users.id`: nombre, email, teléfono, segmento, para quién, rango de edad, ciudad, país, propósito, notas) y `visitas` (modalidad, preferencia de día y bloque tal como la dijo la persona, título, duración 30 min, estado `solicitada`/`confirmada`/`cancelada`). Encima, dos tools que son wrappers semánticos: `registrar_lead` (`kb_agent/tools/leads.py`) hace upsert parcial (sólo pisa los campos informados) y devuelve qué se conoce y qué falta para agendar; `crear_visita` (`kb_agent/tools/visitas.py`) registra el contacto en `leads`, crea la visita en estado `solicitada` (el agente no ve la agenda, el equipo confirma la hora) y es idempotente ante la misma modalidad y preferencia; si faltan modalidad, preferencia, email o teléfono no crea nada y devuelve `status: faltan_datos` con la lista. Ambos handlers completan los argumentos que el modelo no pasó con los slots que el orquestador capturó del mensaje crudo (`session_state.flow_slots.collected`, ver `kb_agent/lead_slots.py`); para eso el orquestador calcula esos slots ANTES de compilar el contexto y los expone al `OrchestratorAgent` como `datos_capturados`. El schema que ve el LLM vive en la KB (`tool-vitali-registrar-lead`, `tool-vitali-crear-visita`) y los steps `calificacion` y `datos_contacto` los referencian en `tool_ref`; `project.vitali.yaml` mapea el nombre al handler. La bandeja `/api/leads` y la ficha `/api/lead` exponen la fila `leads` y las `visitas` del usuario."
