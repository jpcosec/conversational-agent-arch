---
id: atom-ontologizador-context-compiler
title: Ontologizador (Context Compiler)
five_wh_one_plus: what
tags:
  - component:ontologizador
  - layer:engine
---
## Answer

Es el compilador de contexto determinista. Resuelve la ecuación `Contexto = p(Escenario, Pregunta, Perfil)`. Toma los `trait_ids` del usuario desde SQL y la intención de la pregunta, y extrae de SLDB el subgrafo exacto de conocimiento (reglas, herramientas y dominios relevantes). Entrega un paquete cerrado de información al Conversador.