---
id: atom-cómo-se-resuelve-canal-y-persona-desde-el-remitente-de-twilio
title: Cómo se resuelve canal y persona desde el remitente de Twilio
five_wh_one_plus: how
tags:
- layer:runtime
- role:data
- topic:canales
- family:user
provenance: kb_agent/inbound.py
---

# Cómo se resuelve canal y persona desde el remitente de Twilio

## Answer

Twilio manda el remitente de dos formas: `From=whatsapp:+569...` para WhatsApp y `From=+569...` pelado para SMS. `normalize_sender` (`kb_agent/inbound.py`) produce siempre un `external_id` con prefijo de canal — `whatsapp:+56912345678`, `sms:+56912345678` — y el canal (`whatsapp`, `sms`; otros prefijos como `messenger:` se respetan tal cual). Antes el webhook pasaba el `From` crudo y `channel_from_external_id` del orquestador no reconocía el SMS pelado: el usuario quedaba con canal `unknown` y sin teléfono. La parte de teléfono se canoniza con `canonical_phone` (`kb_agent/orchestrator.py`): quita espacios, guiones y paréntesis y exige formato E.164 (`+` opcional y 7 a 15 dígitos); si el id no parece un teléfono devuelve None. Esa exigencia corrige un bug real: la versión anterior extraía los dígitos que hubiera, así que `ui:devsession-1` daba `+1`, y con `identity_key='phone'` dos sesiones de UI distintas terminadas en 1 se habrían unificado como la misma persona. La misma regla se usa en `Orchestrator._canonical_phone` (unificación en `ensure_user`), en `InboundMessage.phone` y en el backfill de la migración `d4e5f6a7b8c9`. Antonia usa `identity_key: phone` en `project.config.yaml` (decisión de negocio: la paciente puede escribir por WhatsApp o SMS y es una sola persona), así que `sms:+569X` y `whatsapp:+569X` comparten un `Users` y el segundo `external_id` queda como alias. Como los usuarios creados antes del cambio tenían `Users.phone` NULL y no se unificaban, la migración rellena `phone` desde el `external_id` en las filas con prefijo de canal y teléfono E.164; los ids sin prefijo o sin teléfono (`ui:`, `web-anon-*`) quedan NULL. Lo que la migración no hace es fusionar dos `Users` que ya existían separados para el mismo teléfono: `ensure_user` busca primero por `external_id` exacto, así que esas parejas históricas siguen siendo dos filas.
