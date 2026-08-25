---
id: atom-perfiles-como-subgrafos-indexables
title: Perfiles de Usuario como Subgrafos Indexables
five_wh_one_plus: why
tags:
  - architecture:data
  - concept:profiling
---
## Answer

Para evitar los silos de datos que generan los documentos JSON monolíticos por usuario, el sistema modela los perfiles como un subgrafo derivado de la Base de Conocimiento universal. 

Las características de los usuarios (ej. "Cliente Frecuente" o "Prefiere Python") existen como átomos de características (`TraitAtoms`) independientes y transversales en SLDB. Un "perfil" es simplemente el subgrafo de átomos que resulta de resolver los punteros relacionales de un usuario específico. Esto permite enriquecer la KB, encontrar similitudes globales y mantener la información despersonalizada y reutilizable en múltiples dominios.