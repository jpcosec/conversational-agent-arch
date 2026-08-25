---
id: atom-perfilador-asincrono
title: Perfilador (Feature Extractor)
five_wh_one_plus: what
tags:
  - component:perfilador
  - layer:background
---
## Answer

Es un agente que opera de forma asíncrona en segundo plano, escuchando la conversación sin añadir latencia al chat. Su propósito es inferir comportamientos o características del usuario (ej. preferencias, nivel de expertise) explícitas en el texto y convertirlas en punteros (edges relacionales) hacia `TraitAtoms` en SLDB, guardando esta asociación en la capa SQL.