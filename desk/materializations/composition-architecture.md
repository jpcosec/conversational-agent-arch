---
id: composition-architecture
title: Arquitectura del Sistema
target_path: docs/ARCHITECTURE.md
tags:
- workspace:docs
- type:composition
- target:architecture
provenance: desk/materializations/composition-architecture.md
---

# Arquitectura del Sistema

Esta documentación está ensamblada a partir de los Átomos Semánticos del proyecto, garantizando que el diseño arquitectónico mantenga cero-drift con el código real.

> **Catálogo Visual Spec2Viz**: `desk/spec2viz/build/architecture.html`

## El Motor Conversacional Síncrono (Runtime)
![[desk/atoms/atom-canales-de-entrada.md]]
![[desk/atoms/atom-mensajes-entrantes-inboundservice-e-inbound-messages.md]]
![[desk/atoms/atom-por-qué-la-respuesta-a-twilio-sale-por-rest-y-no-en-el-twiml.md]]
![[desk/atoms/atom-cómo-se-resuelve-canal-y-persona-desde-el-remitente-de-twilio.md]]
![[desk/atoms/atom-orquestador-hub.md]]
![[desk/atoms/atom-pii-scrubber.md]]
![[desk/atoms/atom-router-state-machine.md]]
![[desk/atoms/atom-context-compiler-knowledge.md]]
![[desk/atoms/atom-ruteador-de-contexto-como-agente.md]]
![[desk/atoms/atom-policy-decide-turn.md]]
![[desk/atoms/atom-tool-handlers-registry.md]]
![[desk/atoms/atom-tools-de-vitali-wrapper-semántico-sobre-leads-y-visitas.md]]
![[desk/atoms/atom-agente-conversador.md]]
![[desk/atoms/atom-policy-gate-como-agente-separado-con-rama-kb-propia.md]]
![[desk/atoms/atom-encuadre-de-agentes-desde-la-kb-agentframing.md]]

## Procesos Offline y Asíncronos
![[desk/atoms/atom-in-process-event-bus.md]]
![[desk/atoms/atom-perfilador-asincrono.md]]
![[desk/atoms/atom-reflector-batch.md]]

## Capas de Datos y Conocimiento
![[desk/atoms/atom-project-config.md]]
![[desk/atoms/atom-persistencia-sql.md]]
![[desk/atoms/atom-sldb-knowledge-base.md]]
![[desk/atoms/atom-kgdb-grafo-de-flujo.md]]

## Frontends
![[desk/atoms/atom-dashboard.md]]
![[desk/atoms/atom-modo-demo.md]]
