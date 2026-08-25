---
id: atom-tool-atom
title: Tool Atom (Átomo de Herramienta)
five_wh_one_plus: what
tags:
  - atom_type:tool
  - domain:ontology
---
## Answer

Es la representación semántica en SLDB de una API externa o script ejecutable. Documenta su esquema JSON, parámetros esperados y propósito. El Ontologizador extrae este átomo y lo convierte al vuelo en `function_declarations` para el LLM. Dicta "qué puede hacer" el bot de forma dinámica sin que las herramientas estén hardcodeadas en el código fuente.