---
id: atom-trigger-sintetico-cron
title: Trigger Sintetico Cron
five_wh_one_plus: what
tags:
- domain:self.architecture.backend
- layer:runtime
- system:cron
- topic:proactivity
provenance: null
---

# Trigger Sintetico Cron

## Answer

Evento disparado artificialmente por un backend CRON para despertar al Router desde el estado 'idle', obligando al Conversador a iniciar un protocolo proactivo con el usuario.

Contrato del payload: el trigger inyecta `{scenario: str, user_id: int}`, donde `scenario` es un tag de dominio válido (ej. `pizza`) que se propaga al Compilador de Contexto como el escenario proactivo del turno, y `user_id` identifica al destinatario. Solo surte efecto cuando el Router está en `idle`; si el nodo actual no es `idle`, el trigger se descarta (drop silencioso con log).
