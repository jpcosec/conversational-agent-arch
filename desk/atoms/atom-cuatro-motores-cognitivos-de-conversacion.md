---
id: atom-cuatro-motores-cognitivos-de-conversacion
title: Los Cuatro Motores Cognitivos de Conversación
five_wh_one_plus: what
tags:
  - architecture:engines
  - system:conversation
---
## Answer

El ecosistema cognitivo se divide en cuatro motores con responsabilidades ortogonales:

1. **Conversador**: Actúa como State Router y redactor. No piensa ni busca, solo ejecuta las transiciones de la Máquina de Estados y genera lenguaje natural o llamadas a APIs estrictamente basado en el contexto recibido.
2. **Ontologizador**: El compilador de contexto. Su único rol es resolver la función matemática `p(Escenario, Pregunta, Perfil_Usuario)` extrayendo el subgrafo exacto de SLDB.
3. **Perfilador**: Agente asíncrono que escucha pasivamente los turnos del usuario para extraer "características" (traits) y guardarlas como enlaces en SQL.
4. **Reflector**: Un trabajo por lotes (batch) que engrosa la base de conocimiento leyendo historiales para consolidar nuevas reglas y dominios como átomos reutilizables en SLDB.