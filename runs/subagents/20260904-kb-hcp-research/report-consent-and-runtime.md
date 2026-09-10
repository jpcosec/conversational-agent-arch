# Informe: Consentimiento y Runtime — antonIA V4.2

Fecha: 2026-09-04
Subagente: 20260904-kb-hcp-research
Fuentes: 7 atoms del desk de `projects/teva/Chatbot/`

---

## 1. Ciclo de vida de consentimiento (opt-in / opt-out)

**Fuente:** `desk/atoms/atom-consent-lifecycle-states.md` (provenance: `antonIA_Arquitectura_V4.2_Vistas_UML.html`, Vista 06 · Diagrama de estados)

### Estados exactos definidos

1. **No contact** (sin contacto)
2. **Opt-in**
3. **Active contact** (contacto activo)
4. **Campaign opt-out** (baja de campaña)
5. **Channel opt-out** (baja de canal)
6. **DSR-driven erasure** (borrado impulsado por solicitud DSR)

### Transiciones y semántica

- El consentimiento avanza por un ciclo definido: no contact → opt-in → active contact, con salidas hacia campaign opt-out, channel opt-out o borrado por DSR.
- **Campaign opt-out**: preserva la elegibilidad futura del HCP (puede volver a ser contactado en otras campañas).
- **Channel opt-out**: bloquea WhatsApp por completo hasta que ocurra un **re-opt-in explícito**.
- **DSR-driven erasure**: estado terminal por borrado de datos vía Data Subject Request.

Distinción clave: opt-out de campaña ≠ opt-out de canal; solo el segundo corta el canal WhatsApp y exige re-consentimiento explícito.

---

## 2. Safety net de eventos adversos (AE): timing e interceptación

**Fuente:** `desk/atoms/atom-ae-safety-net-interception-timing.md` (provenance: diagramas de actividad y aislado v4.2; Vistas 03 y 04 · Diagramas de secuencia)

- **Momento exacto de interceptación:** después de que el LLM propone una respuesta y **antes** de que cualquier respuesta automática sea devuelta al HCP (paso post-guardrails, según tag `pipeline_step:post-guardrails`).
- Ese timing permite **detener la ruta normal de respuesta vía ManyChat**.
- La conversación se **desvía al workflow de safety-net** en lugar de responderse automáticamente.
- Componente implicado en la ruta interceptada: ManyChat (tag `component:manychat`).

---

## 3. Ruteo de respuestas del pipeline

**Fuente:** `desk/atoms/ai-core/atom-pipeline-reply-routing.md` (provenance: diagrama de actividad v4.2; Vista 03 · Diagrama de secuencia)

- **Ruta normal (respuesta aprobada):** la respuesta retorna vía **ManyChat → Meta → HCP**.
- **Rutas de interrupción:** dos condiciones cortan la ruta normal:
  - **Baja confianza** (low-confidence)
  - **Sospecha de AE** (suspected-AE)
- En ambos casos la conversación se **escala** en vez de responderse automáticamente.
- Relación declarada: el ruteo dispara (`triggers`) el atom `atom-suspected-ae-processing-flow` para el flujo AE.

Coherencia con el punto 2: el safety net AE es precisamente una de las interrupciones del ruteo, ubicada post-LLM / pre-respuesta.

---

## 4. Alcance de PII del HCP y almacenamiento en PostgreSQL

### 4.1 Alcance de PII profesional

**Fuente:** `desk/atoms/data/atom-hcp-professional-pii-scope.md` (provenance: `hoja_estudio_martes_28.md`; Vista 05 · Diagrama de clases)

- El alcance previsto es **solo PII profesional del HCP**:
  - Nombre
  - Número de teléfono
  - Especialidad
  - Estado de consentimiento
- El servicio se enmarca explícitamente como **sin datos de pacientes y sin PHI**.

### 4.2 Qué se guarda en PostgreSQL

**Fuente:** `desk/atoms/data/atom-postgresql-state-store.md` (provenance: diagrama aislado v4.2; `docs/plan_implementacion_v2.md`; Vistas 01 y 05)

- PostgreSQL es el **system-of-record borrable** (erasable) del estado operacional.
- Almacena:
  - Estado de conversación
  - Registros de consentimiento
  - Datos de HCP
  - Estado de campañas y opt-out
  - Estructuras de knowledge base usadas por RAG, incluido **soporte de búsqueda vectorial para embeddings**

### 4.3 Cómo llega el conocimiento a PostgreSQL

**Fuente:** `desk/atoms/atom-secure-knowledge-ingestion.md` (provenance: diagrama aislado v4.2; `plan_implementacion_v2.md`; `hoja_estudio_martes_28.md`; Vista 01)

- Ingesta de conocimiento **out-of-band y manual**.
- Bases de HCP provistas por Teva y contenido **aprobado por MLR** se entregan vía **Kiteworks/SFTP**.
- antonIA procesa esos archivos para actualizar PostgreSQL y la knowledge base accesible por RAG.
- Diseño explícito: **sin integración directa Teva ↔ backend**.

---

## 5. Identidad de servicio de antonIA V4.2

**Fuente:** `desk/atoms/atom-antonia-v4.2-service-identity.md` (provenance: `README.md`; diagrama aislado v4.2; UML header y Vista 07 · Casos de uso)

- antonIA V4.2 es un **servicio de IA conversacional aislado para HCP, de Teva Chile**.
- Alcance operativo (exhaustivo según el atom):
  1. Conversaciones con HCP
  2. Recuperación de conocimiento médico aprobado
  3. Manejo de campañas
  4. Human takeover (toma de control humana)
  5. Escalamiento al canal de AE
  6. Reporting de solo lectura
- Conceptos identitarios: aislamiento (`concept:isolation`) y alcance de servicio acotado (`model:service-scope`).

---

## Síntesis cruzada

- El diseño es coherente end-to-end: servicio aislado (atom-antonia-v4.2-service-identity) + datos mínimos profesionales sin PHI (atom-hcp-professional-pii-scope) + estado borrable en PostgreSQL con soporte DSR (atom-postgresql-state-store, atom-consent-lifecycle-states).
- El pipeline garantiza que ninguna respuesta llegue al HCP sin pasar el filtro AE post-LLM (atom-ae-safety-net-interception-timing, atom-pipeline-reply-routing).
- La ingesta manual vía Kiteworks/SFTP evita acoplamiento directo con Teva, reforzando el aislamiento del servicio (atom-secure-knowledge-ingestion).

## Tabla de trazabilidad

| Hallazgo | Archivo fuente |
|---|---|
| 6 estados de consentimiento y transiciones | `desk/atoms/atom-consent-lifecycle-states.md` |
| Interceptación AE post-LLM / pre-respuesta | `desk/atoms/atom-ae-safety-net-interception-timing.md` |
| Ruteo ManyChat→Meta→HCP y escalamiento | `desk/atoms/ai-core/atom-pipeline-reply-routing.md` |
| PII: nombre, teléfono, especialidad, consentimiento; sin PHI | `desk/atoms/data/atom-hcp-professional-pii-scope.md` |
| PostgreSQL como system-of-record borrable | `desk/atoms/data/atom-postgresql-state-store.md` |
| Ingesta Kiteworks/SFTP manual, sin integración directa | `desk/atoms/atom-secure-knowledge-ingestion.md` |
| Identidad y alcance operativo v4.2 | `desk/atoms/atom-antonia-v4.2-service-identity.md` |
