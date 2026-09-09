# Misión — Construcción de la KB HCP (Override de `knowledge/`)

## 1. Qué estamos haciendo

Estamos construyendo una Knowledge Base tipada (`knowledge_hcp/`) que reemplaza a la KB
productiva actual (`knowledge/`, PSP de pacientes) para operar el **piloto HCP WhatsApp
MX+CL de Teva**: una plataforma de campañas dirigidas a médicos (Health Care
Professionals).

El bot sigue siendo **Antonia** (misma identidad, mismo runtime `kb_agent`), pero su
comportamiento completo se redefine desde la KB, aprovechando que el motor es
multi-dominio: cambiar `kb_root` en `project.config.yaml` cambia el negocio.

### Objetivo de negocio del piloto

- Hacer **campañas de medicamentos** a médicos con opt-in: ofertas, variantes nuevas,
  novedades de portafolio.
- El bot contacta al médico, entrega detalles del medicamento que el doctor pida y
  **filtra el contenido según especialidad** (psiquiatra ve un perfil de medicamentos,
  traumatólogo ve otro).
- **El consentimiento es sagrado**: en cualquier punto el médico puede bajarse de una
  campaña o de la app completa, y el bot debe ejecutar esa baja sin fricción, sin
  retención y actualizando el estado persistente.
- El bot debe soportar **"escríbeme más tarde"**: capturar la preferencia y programar
  un recontacto.
- Debe existir un **handout a especialista humano** cuando la consulta excede el corpus
  aprobado o el médico lo pide.

### Arquitectura de datos (3 stores)

| Store | Tecnología | Contenido |
|---|---|---|
| usuario-datos-personales | SQL | PII del médico (nombre, teléfono, opt-in/opt-out, canal) |
| usuario-perfil | SQL | Especialidad, traits, preferencias de contacto, historial de campaña |
| KB general | SLDB (`knowledge_hcp/`) | Info de "bajo riesgo": medicamentos, campañas, reglas, flujo |

El Context Compiler cruza el perfil SQL (`specialty=psiquiatria`) contra los tags de la
KB (`user:specialty.psiquiatria`) para inyectar solo los átomos pertinentes.

## 2. Restricciones no negociables

1. **Cero alucinación**: solo contenido MLR aprobado; contexto vacío ⇒ `BREAKPOINT_MISS`
   ⇒ fallback determinista.
2. **Consentimiento**: opt-out de campaña ≠ opt-out de app; ambos flujos deben existir,
   ser inmediatos y persistir en SQL. Prohibido retener o argumentar.
3. **Farmacovigilancia**: mención de evento adverso ⇒ detener flujo ⇒ derivar al
   contacto oficial de farmacovigilancia (MX o CL). Sin preguntas exploratorias.
4. **Límites clínicos**: no dosis fuera de ficha aprobada, no diagnóstico, no promesas,
   no extrapolar entre productos ni entre especialidades.
5. **Aislamiento V2.0**: cero integración con sistemas Teva; contenido llega vía
   Kiteworks/SFTP; el bot nunca promete acceso a sistemas del cliente.

## 3. Modelación (obligatoria, ver `knowledge_base/taxonomy/modelation-guide.md`)

Cada átomo DEBE ser instancia de un modelo tipado; `AtomDoc` genérico está prohibido
para dominio:

| Contenido | Modelo | Campos clave |
|---|---|---|
| Ficha/oferta de medicamento por especialidad | `DomainAtom` | answer, tags (`domain:medicamentos.*`, `user:specialty.*`) |
| Reglas condicionales (filtrado, recontacto, clarificación) | `RuleAtom` | answer, conditions, applies_to |
| Opt-out, farmacovigilancia, límites clínicos | `CapabilityBoundary` | restriction, conditions, escalation |
| Nodos del flujo (contactar, detallar, handout, baja, recontacto) | `ConversationStep` | instructions, required_slots, allowed_transitions, grounding_atoms |
| Identidad Antonia-para-HCP | `SelfDeclaration` | statement |
| Tono médico/científico | `StyleGuide` | tone, language_register |
| Traits del médico (especialidad, opt-in, preferencias) | `TraitAtom` | description, category |
| Respuesta ante contexto vacío | `FallbackRule` | fallback_message, conditions |
| Programar recontacto / actualizar opt-out (APIs) | `ToolAtom` | parameters (JSON schema) |
| Estrategia de campaña | `StrategyRule` | goal, approach, priorities |

### Flujo conversacional mínimo a modelar (`ConversationStep`)

```
contacto_inicial → presentar_campania → detalle_medicamento ⇄ responder_dudas
                                   ↘ handout_especialista
                                   ↘ agendar_recontacto ("escríbeme más tarde")
                                   ↘ optout_campania / optout_app → confirmar_baja
```

## 4. Dónde buscar información (fuentes)

### Fuentes primarias (source_docs — investigar con subagentes)

- `/home/jp/AntonIA/source_docs/projects/teva/Propuesta actualizada · antonIA HCP Conversational Platform · MX + CL v2.pdf`
  → alcance del piloto, comercial, arquitectura V2.0, farmacovigilancia, timeline.
- `/home/jp/AntonIA/source_docs/projects/teva/Chatbot/antonIA_Reference_Architecture_V4.2_Teva_Chile.pdf`
  → arquitectura de referencia del runtime, pipeline, policy gate.
- `/home/jp/AntonIA/source_docs/projects/teva/Chatbot/antonIA_Arquitectura_V4.2_Vistas_UML.html`
  → vistas UML de flujo y componentes.
- `/home/jp/AntonIA/source_docs/projects/teva/Chatbot/conversacion_marlin_jul26.md` y
  `hoja_estudio_martes_28.md` → contexto de decisiones y dominio.

### Fuentes destiladas (átomos ya curados)

- `/home/jp/AntonIA/projects/teva/Chatbot/desk/atoms/` → consent lifecycle
  (`atom-consent-lifecycle-states.md`), AE safety net, pipeline de ruteo, PII scope
  (`data/atom-hcp-professional-pii-scope.md`), Kiteworks, PostgreSQL state store.
- `/home/jp/AntonIA/planification/teva/client-inputs/` → insumos del cliente: base
  opt-in, contenido MLR, farmacovigilancia, Twilio bundle, SSO.

### Referencias de implementación (este repo)

- `knowledge/atoms/` → KB PSP original: gates, reglas anti-alucinación, fallback, steps
  (patrones de forma ya copiados a `knowledge_hcp/atoms/`).
- `tests/knowledge/` → KB Don Peppe: ejemplo de átomos tipados por modelo.
- `knowledge_base/taxonomy/modelation-guide.md` → guía de modelación y anti-patrones.
- `kb_agent/models/knowledge/` → clases Python de los modelos.

## 5. Plan de ejecución

1. **Investigación (subagentes)**: extraer de las fuentes primarias todo lo relativo a
   consent lifecycle, farmacovigilancia, flujo conversacional, filtrado por perfil y
   catálogo de medicamentos/campañas. Evidencias en `runs/subagents/`.
2. **Rama de dominio**: crear `knowledge_hcp/atoms/campaigns/` con `DomainAtom`s por
   medicamento × especialidad (mucha profundidad: indicación, presentación, oferta,
   personalización por perfil).
3. **Flujo**: crear los `ConversationStep` del diagrama de la sección 3.
4. **Guardarraíles**: refactorizar los átomos copiados a modelos tipados
   (`CapabilityBoundary`, `FallbackRule`) según el redo ya propuesto.
5. **Registro SLDB**: registrar modelos y trackear documentos en `knowledge_hcp/.sldb`.
