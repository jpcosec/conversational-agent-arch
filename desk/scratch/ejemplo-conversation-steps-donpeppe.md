# Ejemplo: átomos `conversation:steps.*` para Don Peppe

---

## Átomo 1 — Saludo / Onboarding

```markdown
---
id: conversation-step-saludo
title: Paso conversacional · Saludo inicial
five_wh_one_plus: how
tags:
  - conversation:steps.saludo
  - domain:pizzeria
provenance: null
---

# Paso conversacional · Saludo inicial

## Answer

**Rol:** Paso inicial de la conversación.  
**Próximos pasos:** consulta_carta, reserva_inicio, fallback.  
**Groundea:** atom-donpeppe-horarios, atom-donpeppe-carta.  
**Comportamiento:** El agente saluda, ofrece las opciones principales (carta/reserva), y pregunta qué necesita el cliente.  
**Tools:** ninguna.  
**Slots requeridos:** ninguno.  
**Traits activos:** ninguno.
```

---

## Átomo 2 — Pedir fecha de reserva

```markdown
---
id: conversation-step-reserva-pedir-fecha
title: Paso conversacional · Pedir fecha de reserva
five_wh_one_plus: how
tags:
  - conversation:steps.reserva_pedir_fecha
  - domain:pizzeria
provenance: null
---

# Paso conversacional · Pedir fecha de reserva

## Answer

**Rol:** Paso intermedio de reserva. Solicitar la fecha al cliente.  
**Próximos pasos:** reserva_pedir_personas, reserva_confirmar.  
**Groundea:** atom-donpeppe-horarios (para validar día hábil), atom-donpeppe-regla-reservas (no mismo día).  
**Comportamiento:** El agente pregunta qué día quiere reservar. Valida que no sea lunes (cerrado) y que no sea el mismo día (regla).  
**Tools:** ninguna.  
**Slots requeridos:** fecha (string, formato YYYY-MM-DD).  
**Traits activos:** ninguno.
```

---

## Átomo 3 — Ejecutar tool de reserva

```markdown
---
id: conversation-step-reserva-ejecutar
title: Paso conversacional · Ejecutar tool de reserva
five_wh_one_plus: how
tags:
  - conversation:steps.reserva_ejecutar
  - domain:pizzeria
provenance: null
---

# Paso conversacional · Ejecutar tool de reserva

## Answer

**Rol:** Paso terminal de reserva. Ejecuta la tool y confirma.  
**Próximos pasos:** reserva_fin, reserva_inicio (si falla).  
**Groundea:** atom-donpeppe-regla-reservas.  
**Comportamiento:** El agente ejecuta crear_reserva(fecha, hora, personas, nombre). Si falla, vuelve a reserva_inicio con el error.  
**Tools:** crear_reserva.  
**Slots requeridos:** fecha, hora, personas, nombre.  
**Traits activos:** trait-vegetariano, trait-sin-gluten (el agente los advierte al confirmar).
```

---

## Átomo 4 — Fallback

```markdown
---
id: conversation-step-fallback
title: Paso conversacional · Fallback (fuera de dominio)
five_wh_one_plus: how
tags:
  - conversation:steps.fallback
  - domain:pizzeria
provenance: null
---

# Paso conversacional · Fallback (fuera de dominio)

## Answer

**Rol:** Paso terminal cuando el usuario pregunta algo fuera del dominio.  
**Próximos pasos:** saludo.  
**Groundea:** ninguno.  
**Comportamiento:** El agente admite no saber y redirige a saludo. Usa el texto de conversación:fallback.  
**Tools:** ninguna.  
**Slots requeridos:** ninguno.  
**Traits activos:** ninguno.
```

---

## Cómo se vería en KGDB (grafo)

```
conversation:steps.saludo
  ┣━ flows_to ━━━> conversation:steps.consulta_carta
  ┣━ flows_to ━━━> conversation:steps.reserva_inicio
  ┗━ flows_to ━━━> conversation:steps.fallback

conversation:steps.reserva_inicio
  ┣━ flows_to ━━━━━━━━━━> conversation:steps.reserva_pedir_fecha
  ┣━ grounded_by ━━━━━━━> atom-donpeppe-regla-reservas
  ┗━ uses_tool ━━━━━━━━━> crear_reserva

conversation:steps.reserva_pedir_fecha
  ┣━ flows_to ━━━━━━━━━━> conversation:steps.reserva_pedir_personas
  ┣━ flows_to ━━━━━━━━━━> conversation:steps.reserva_confirmar
  ┣━ grounded_by ━━━━━━━> atom-donpeppe-horarios
  ┣━ grounded_by ━━━━━━━> atom-donpeppe-regla-reservas
  ┗━ requires_slot ━━━━━> slot:fecha

conversation:steps.reserva_ejecutar
  ┣━ flows_to ━━━━━━━━━━> conversation:steps.reserva_fin
  ┣━ falls_back_to ━━━━━> conversation:steps.reserva_inicio
  ┣━ grounded_by ━━━━━━━> atom-donpeppe-regla-reservas
  ┣━ uses_tool ━━━━━━━━━> crear_reserva
  ┣━ adapts_to_trait ━━━> trait-vegetariano
  ┗━ adapts_to_trait ━━━> trait-sin-gluten
```

---

## Qué permite esto en runtime

| Turno | `SessionState.flow_node` | Compilador trae |
|--------|--------------------------|----------------|
| "Hola" | `saludo` | Horarios + carta |
| "Quiero reserva" | `reserva_inicio` | Regla + tool |
| "El viernes" | `reserva_pedir_fecha` | Horarios + regla, valida día |
| "3 personas, Juan" | `reserva_ejecutar` | Regla + tool, ejecuta |