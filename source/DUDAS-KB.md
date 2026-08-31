# Dudas para reconstruir la KB de Vitali — 2026-08-31

Documento de preguntas abiertas. Todo lo que NO tiene respaldo en el crawl del
sitio (`source/crawl/`) ni en `source/systemprompt.md` queda aquí, sin inventar.

## Ya actualizado en esta pasada (con respaldo del crawl)
- `dom-projects-overview`: ahora nombra los 6 proyectos con ciudad, estado y año.
  Los dos de Chile (Chicureo y Mantagua) quedan explícitos → arregla el bug de
  "ubicación" que solo devolvía Mantagua.
- Embeddings de la KB re-indexados (48 atoms). Store valida (PASS).

## Bugs reportados por Gian — estado
1. **"Ubicación" solo daba Mantagua** → CORREGIDO (overview ahora nombra ambos).
2. **Chicureo solo dice "precordillera de Santiago"** → el sitio NO publica más
   detalle. El atom ya refleja todo lo público. DUDA abajo (P1).
3. **Precios ("desde 2376 UF") y tipologías/dimensiones** → NO hay fuente. Sin
   tocar. DUDAS abajo (P2, P3).

## Preguntas abiertas

### P1 — Ubicación exacta de los proyectos chilenos
- El sitio solo dice "precordillera de Santiago" (Chicureo) y "zona de alto
  standing / costera" (Mantagua). Sin comuna ni dirección de proyecto.
- ¿Comuna/dirección real de Chicureo? (¿Colina? ¿sector puntual?)
- ¿Ubicación real de Mantagua? (¿región de Valparaíso / Quintero?)
- ¿Se pueden dar públicamente o son reservados hasta la visita?

### P2 — Precios
- ¿Se dará algún precio en la conversación, o se mantiene "lo ve un asesor en la
  visita"? Hoy `rule-faq-pricing` manda a asesor y prohíbe cifras (sin cambios).
- Si se da: ¿"desde X UF" por proyecto? ¿UF o USD? ¿varía por tipología?
- El sitio NO publica precios; necesito fuente interna oficial.

### P3 — Tipologías y dimensiones de suites
- ¿Qué tipos de suite existen (studio, 1D, 2D…)? ¿m² de cada una?
- El sitio solo lista features cualitativas (terrazas, domótica), sin m².
- Necesito tabla oficial: tipo de suite → dimensiones → (precio si aplica).

### P4 — Catálogo de citas / tipos de reunión
- El systemprompt define un solo tipo: "Reu Vitali" (30 min).
- ¿Hay más tipos de reunión (visita presencial vs videollamada, comercial vs
  franquicia)? ¿Duraciones y modalidad por tipo?

### P5 — Tool única: flujo n8n (pendiente de entrega)
- FRONTERA CONFIRMADA: la única tool expuesta será un flujo n8n aún no entregado.
- Las tools de Google Calendar / Gmail del systemprompt NO son responsabilidad
  nuestra (son del motor externo). No se modelan en la KB.
- La notificación interna a `vitalisuites@gmail.com` queda FUERA DE ALCANCE
  (la maneja el n8n / el motor externo), no la KB.
- La KB describe el agendamiento como INTENCIÓN (qué datos juntar, cómo presentar
  horarios). El binding real de la tool se hará cuando llegue el n8n.
- Pendiente del proveedor n8n: contrato de la tool (nombre, inputs/outputs,
  operaciones: disponibilidad, crear cita). Sin eso, los steps `kind:
  llamado_tool` quedan con `## Tool` vacío a propósito.

### P5b — Residuo de Google Calendar a limpiar en la KB
- `rule-timezone-routing` menciona "calendario 'primary' y zona America/Santiago"
  → es residuo del systemprompt de Google Calendar; asume una tool que no es
  nuestra. Debe reescribirse en términos de negocio (zona horaria del lead +
  oficina), sin nombrar mecanismos de calendario.
- `rule-visit-modality` dice "al crear el evento, SIEMPRE fijar una ubicacion" →
  mismo residuo; reformular como dato de la cita, no como parámetro de tool.

### P6 — Zona horaria y multi-país
- El systemprompt fija `America/Santiago`. Con proyectos en MX/CO/BO, ¿la cita
  se agenda en la TZ del proyecto o siempre Chile? Hay `rule-timezone-routing`
  pero conviene confirmar la regla de negocio.

### P7 — Segmentación de leads
- El form del sitio segmenta en Suite / Broker / Franquicia. La KB ya lo refleja
  (`agent-vitali-router`). ¿El agente conversacional maneja los 3 segmentos o
  solo "Suite" (residente/familiar/inversión)?
