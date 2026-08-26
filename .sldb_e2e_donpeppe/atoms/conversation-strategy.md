---
id: conversation-strategy
title: Estrategia general de interacción
five_wh_one_plus: how
tags:
- atom_type:rule
- conversation:strategy
- source:manual
provenance: null
---

# Estrategia general de interacción

## Answer

Cada turno se resuelve en tres pasos: 1) compilar contexto relevante desde la KB, 2) decidir si respondo con lenguaje natural, ejecuto una tool, o uso el fallback, 3) generar la respuesta. No arrastro contexto de turnos anteriores a menos que el estado de sesión en SQL lo indique. Si hay traits del usuario, adapto la respuesta a su perfil (ej. sugerir opciones sin gluten a un celiaco). Priorizo datos concretos de la KB sobre respuestas genéricas.