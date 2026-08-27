# Arquitectura del Sistema

Esta documentación está ensamblada a partir de los Átomos Semánticos del proyecto, garantizando que el diseño arquitectónico mantenga cero-drift con el código real.

> **Catálogo Visual Spec2Viz**: `desk/spec2viz/build/architecture.html`

## El Motor Conversacional Síncrono (Runtime)
![[atom-canales-de-entrada]]
![[atom-orquestador-hub]]
![[atom-pii-scrubber]]
![[atom-router-state-machine]]
![[atom-ontologizador-context-compiler]]
![[atom-ruteador-de-contexto-como-agente]]
![[atom-policy-decide-turn]]
![[atom-tool-handlers-registry]]
![[atom-agente-conversador]]
![[atom-policy-gate-como-agente-separado-con-rama-kb-propia]]
![[atom-encuadre-de-agentes-desde-la-kb-agentframing]]

## Procesos Offline y Asíncronos
![[atom-in-process-event-bus]]
![[atom-perfilador-asincrono]]
![[atom-reflector-batch]]

## Capas de Datos y Conocimiento
![[atom-project-config]]
![[atom-persistencia-sql]]
![[atom-sldb-knowledge-base]]
![[atom-kgdb-grafo-de-flujo]]

## Frontends
![[atom-dashboard]]
![[atom-modo-demo]]
