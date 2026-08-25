---
id: pill-conversador-jamas-alucina-sin-contexto
title: El Conversador jamás alucina sin contexto
type: pill
tags:
  - rule:execution
---
# Context

- **Fallo Silencioso Prohibido**: Si el Ontologizador retorna un contexto vacío (miss), fuera de dominio, o insuficiente, el Conversador tiene estrictamente prohibido intentar adivinar o inventar datos basados en su entrenamiento paramétrico.
- **Punto de Quiebre**: La falta de contexto debe gatillar un cambio de estado hacia el nodo `breakpoint_miss`. 
- **Respuesta Estándar (frase canónica exacta)**: En `breakpoint_miss` el Conversador debe emitir textualmente: "No tengo esa información a mano, la averiguaré." (string exacto, para permitir aserciones deterministas en tests).