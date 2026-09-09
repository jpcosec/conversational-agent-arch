# Informe de investigación — Dominio de campaña HCP (Teva / antonIA)

**Fecha:** 2026-09-04
**Subagente:** 20260904-kb-hcp-research
**Fuentes analizadas:**

| # | Fuente | Ruta |
|---|--------|------|
| F1 | Client input: base opt-in | `/home/jp/AntonIA/planification/teva/client-inputs/client-input-hcp-base-opt-in.md` |
| F2 | Client input: contenido MLR | `/home/jp/AntonIA/planification/teva/client-inputs/client-input-hcp-contenido-mlr.md` |
| F3 | Client input: farmacovigilancia | `/home/jp/AntonIA/planification/teva/client-inputs/client-input-hcp-farmacovigilancia.md` |
| F4 | Client input: bundle Twilio | `/home/jp/AntonIA/planification/teva/client-inputs/client-input-hcp-twilio-bundle.md` |
| F5 | `conversacion_marlin_jul26.md` | `/home/jp/AntonIA/source_docs/projects/teva/Chatbot/conversacion_marlin_jul26.md` |
| F6 | `hoja_estudio_martes_28.md` | `/home/jp/AntonIA/source_docs/projects/teva/Chatbot/hoja_estudio_martes_28.md` |
| F7 | PDF hilo de correo "Propuesta actualizada · antonIA HCP Conversational Platform · MX + CL v2" (extraído con pdftotext) | `/home/jp/AntonIA/source_docs/projects/teva/Propuesta actualizada · antonIA HCP Conversational Platform · MX + CL v2.pdf` |

> **Nota de fuentes:** F5 y F6 contienen el mismo texto (la hoja de estudio para la reunión TPRM del martes 28); F5 no es una conversación distinta con Marlyn. Se citan ambas cuando aplica.

---

## 1. Base opt-in de HCPs: qué es y cómo llega

### Definición y contenido
- Es la base de datos de profesionales de la salud (HCPs) que dieron **consentimiento previo (opt-in)** para ser contactados por la plataforma conversacional vía WhatsApp. [F1, F7]
- Campos solicitados a Teva: **nombre, teléfono, especialidad, consentimiento** (estado de consentimiento). [F1, F7]
- Es exactamente el mismo conjunto de datos personales que entra al sistema: "Name, phone number, specialty, consent status. Professional PII of HCPs. No patient data whatsoever, no PHI." [F5/F6]
- Pendientes de definir por Teva: **formato, volumen y fecha de entrega**. [F1, F7]

### Mecanismo de llegada
- Llega **vía Kiteworks/SFTP**, con **cadencia controlada por Teva**; el flujo de contenido es unidireccional y manual ("Content flows one way, through Kiteworks, manually"; "Content intake is fully out-of-band: manual Kiteworks/SFTP"). [F5/F6, F7]
- Requiere **creación de usuarios Kiteworks para antonIA** (Gianfranco y Juan Pablo). [F7]
- No hay integración con sistemas Teva (Veeva CRM, Veeva Vault, Salesforce, SAP, Azure AD fuera de scope); ningún usuario de Teva se conecta al backend. [F7]

### Propiedad y estado
- Owner del input: **Teva (Lab Chile)**. Estado: `requested` (2026-08-20), sin fecha de recepción; **bloquea `deliverable-h1-knowledge-base`**. [F1]
- La entrega de la base de HCPs figura entre los 3 ítems de mayor tiempo de espera que "condicionan todo lo demás" para el go-live de octubre (junto con Meta y Twilio). [F7]

### Roles de datos
- Teva es **data controller**; antonIA es **data processor**. Retención definida por contrato con Teva como controller; DSR API para acceso, rectificación y borrado; log de auditoría WORM de 5 años solo con eventos seudonimizados (sin PII). [F5/F6]
- Cobertura estimada del universo HCP objetivo durante el piloto: **83–100% en México, 71–100% en Chile** (con arranque directo en Tier 1 de Meta). [F7]

---

## 2. Ciclo MLR de aprobación de contenido

### Qué es y qué falta
- Todo el contenido que usa el bot debe ser **contenido aprobado por Medical Affairs** mediante el ciclo MLR (Medical-Legal-Regulatory). [F2, F7]
- Pendientes de Teva: **contenido aprobado para el lanzamiento, duración del ciclo MLR, y quién firma la aprobación final de cada plantilla**. El ciclo MLR "impacta directo el cronograma". [F2, F7]
- Owner: **Teva (Medical Affairs)**. Estado: `requested` (2026-08-20). **Bloquea `deliverable-h1-knowledge-base` y `deliverable-h5-fase-experimental`**. [F2]

### Cadena de aprobación
- La operación queda bajo **aprobación cross-funcional de cinco áreas** confirmadas por Marcos Cabral: **Pharmacovigilance, Regulatory Affairs, Legal, Compliance y Medical (vía Veeva PromoMats)**. [F7]
- Ruta de aprobación simplificada por ausencia de integración: "Medical Affairs, Legal and Compliance". [F5/F6]
- El contenido MLR aprobado llega vía Kiteworks/SFTP bajo cadencia controlada por Teva. [F7]

### Qué se puede decir y qué no (reglas de contenido operativas)
Las fuentes no contienen una lista explícita de claims permitidos/prohibidos, pero sí definen el marco de restricción:
- **Solo contenido aprobado por MLR**: el bot opera con "Closed RAG only (no open web)" — no puede responder fuera de la base de contenido aprobado. [F5/F6]
- **Pre- y post-guardrails en cada mensaje**, aislamiento por conversación (sin memoria compartida entre HCPs), **escalamiento humano con baja confianza**, y toda respuesta auditable. [F5/F6]
- **Sin datos de pacientes / sin PHI** en ninguna interacción; solo PII profesional de HCPs. [F5/F6]
- Pruebas en sandbox **con contenido aprobado por Teva** antes del lanzamiento (primera semana de octubre). [F7]
- Cada **plantilla** de mensaje requiere una firma de aprobación final (firmante por confirmar). [F2, F7]

---

## 3. Protocolo de farmacovigilancia (eventos adversos)

### Contacto
- Pendiente de Teva: **nombre y correo del contacto designado de farmacovigilancia** para manejo de eventos adversos. Owner: **Teva (Farmacovigilancia)**. Estado: `requested` (2026-08-20). **Bloquea `deliverable-h4-modelo-servicio`**. [F3, F7]

### Naturaleza del protocolo (AE safety-net)
- Posición oficial de antonIA: "It's a **channel obligation, not a PV system**. We **detect, flag, log pseudonymized, notify Teva's PV designee by email, and hand over**. Case management happens outside our infrastructure." [F5/F6]
- Flujo: detección del evento adverso en la conversación → marcado (flag) → registro seudonimizado → **notificación por correo al designado de PV de Teva** → entrega del caso; la gestión de casos ocurre fuera de la infraestructura de antonIA. [F5/F6]
- Farmacovigilancia es una de las 5 áreas de aprobación cross-funcional de la operación. [F7]

### Países
- El alcance del proyecto es **México y Chile** (plataforma "MX + CL"); no se especifica en las fuentes si hay contactos PV separados por país — el client input pide un único contacto designado. [F3, F7]

### Timing
- Las fuentes **no fijan un plazo específico de reporte de eventos adversos**. El único plazo comprometido relacionado es el de incidentes de seguridad: notificación a Teva dentro de **48 horas** de confirmar un incidente que afecte datos de Teva (es breach notification, no timing de AE). [F5/F6]
- **Gap identificado:** timing de reporte de AE (p. ej. 24h regulatorias típicas de PV) no está documentado en ninguna fuente leída.

---

## 4. Alcance de campañas / mensajería (Twilio + WhatsApp)

### Canal y arquitectura de mensajería
- Canal: **WhatsApp Business** vía Meta Cloud API. Ruta técnica: HCP → WhatsApp → Meta Cloud API → BSP → Cloudflare WAF/TLS → subred privada AWS (sin IPs públicas en backend; VPC endpoints para Bedrock, S3, KMS). [F5/F6]
- BSP: originalmente **ManyChat** (Meta-certified BSP, DPA en revisión legal); antonIA recomendó **reemplazarlo por Twilio**: "enterprise BSP, SOC 2 Type II, ISO 27001, standard DPA, pure transport with no application layer over content". [F5/F6]

### Bundle regulatorio Twilio (número Chile)
- Para aprovisionar el número en Chile, Twilio exige un **bundle regulatorio**: razón social, RUT, domicilio registrado, comprobante de domicilio; **se comprobó que basta el E-RUT en ambos campos** para crear el bundle. [F4, F7]
- El **número queda a nombre de Teva / Laboratorio Chile como titular**. [F4, F7]
- Al 25-ago-2026: antonIA estaba creando la subcuenta Twilio + regulatory bundle y solicitó a Lab Chile el **E-RUT** para subirlo como documento. [F7]
- Owner: **Teva (Legal / Lab Chile)**. Estado: `requested`. **Bloquea `deliverable-h5-fase-experimental`**. [F4]

### WABA y Meta Business
- Lab Chile ya tiene cuenta Meta Business (facebook.com/laboratoriochileteva); antonIA pidió acceso **partner con permisos acotados solo al activo WhatsApp Business Account**: gestión de WABA, números de teléfono y **plantillas de mensajes** (sin acceso a páginas ni campañas). [F7]
- Se crea una **nueva WABA para el proyecto**; verificación de negocio ante Meta ~3-4 días hábiles si falta. Se requiere definir **nombre visible del bot, foto de perfil y descripción** tal como los verán los médicos. [F7]
- WABA ownership definido: cuenta Meta Business **a nombre de Teva**, antonIA registra el número, verificación antes del go-live. [F5/F6]
- Accesos a la cuenta Meta de Lab Chile confirmados OK el 24-ago-2026. [F7]

### Plantillas
- Las **plantillas de mensajes** son un activo gestionado en la WABA; **cada plantilla requiere aprobación final firmada** por Teva (firmante por confirmar, ciclo MLR). [F2, F7]

### Ventanas de contacto y capacidad (tiers de Meta)
- Las fuentes no mencionan la ventana de 24h de WhatsApp explícitamente; el límite de alcance documentado son los **tiers de mensajería de Meta**:
  - Arranque directo en **Tier 1**, confirmado por Marcos gracias al Business Portfolio verificado de Teva. [F7]
  - Reglas Meta 2026: **evaluación de tier cada 6 horas**; ruta a **Tier 3 en 8–12 semanas**. [F7]
  - El piloto se extendió a **4 ciclos operacionales** para cerrar con al menos un ciclo completo estable en Tier 3. [F7]
  - Modelo de capacidad: "conversation-band model" — la capacidad crece con el uso real; la progresión de tiers la gestiona operacionalmente antonIA. [F5/F6]
- Cobertura estimada del universo HCP en piloto: **MX 83–100%, CL 71–100%**. [F7]

### Cronograma y economía del piloto
- Cronograma: **30-sep** entrega técnica (sistema operativo, listo para pen test); **primera semana de octubre** sandbox con contenido aprobado; **mediados de octubre** go-live. Continuidad proyectada hasta **marzo 2027**. [F7]
- Piloto: **USD 125.500 total** (reducido desde 145K, -14%); setup **USD 24.000 por mercado**; operación **USD 9.500/mes por mercado**; mensajería facturada **a costo** según tarifas Meta. [F7]
- Pago: net 30; capex en 3 hitos (40% PO / 40% entrega técnica 30-sep / 20% cierre 2º mes de operación ~15-dic); opex mensual por banda de uso. Dos órdenes de compra separadas (capex/opex). [F7]

---

## 5. Medicamentos, portafolio y especialidades médicas

### Hallazgo principal: ausencia casi total
- **Ninguna fuente menciona medicamentos específicos, marcas, moléculas ni portafolio de productos Teva.** No hay nombres de fármacos, áreas terapéuticas ni indicaciones en ninguno de los 7 documentos. [F1–F7]
- **Especialidades médicas:** solo aparecen como **campo de dato** de la base opt-in ("nombre, teléfono, **especialidad**, consentimiento"); no se enumeran especialidades objetivo concretas. [F1, F5/F6, F7]
- **Audiencia:** HCPs ("los médicos" que verán el perfil del bot) en México y Chile. [F7]

### Contexto corporativo indirecto
- Entidades Teva mencionadas: **Laboratorio Chile** (Chile), **Teva Pharmaceuticals México S.A. de C.V., Ivax Pharmaceuticals Mexico S.A. de C.V., Lemery S.A. de C.V.** (Teva México, disclaimer legal del correo), Teva Brasil (IT), Teva Bulgaria/Israel (seguridad/datos globales). [F7, F5/F6]
- Sistemas de contenido/CRM de Teva referenciados (fuera de scope de integración): **Veeva CRM, Veeva Vault, Veeva PromoMats, Salesforce, SAP, Azure AD**. [F7]
- **Gap identificado:** la definición del portafolio/productos cubiertos por el bot depende del contenido MLR aún no entregado (F2, status `requested`).

---

## 6. Personas clave (referencia rápida)

| Persona | Rol | Fuente |
|---|---|---|
| Marlyn Cedillo | Commercial IT Cluster Lead, Teva México (comercial) | F7 |
| Felipe Muñoz | Manager Omnichannel, Lab Chile; sponsor local, único usuario Teva del dashboard (read-only) | F5/F6, F7 |
| Marcos Cabral | Sr Mgr IT Brazil; validó arquitectura, confirmó 5 áreas de aprobación y Tier 1 | F5/F6, F7 |
| Charyl Molero | Lab Chile (MEPU) | F7 |
| Presiyana Zagorska | Senior Manager Cloud Security, Teva Bulgaria (TPRM) | F5/F6 |
| Omri Dotan | Director Enterprise Data Architecture, Teva global | F5/F6 |
| Nikolay Nikolov | Cloud/Infra Architect, Teva Bulgaria | F5/F6 |
| Gianfranco Raineri / Juan Pablo Ruiz | antonIA (usuarios Kiteworks solicitados) | F7 |

---

## 7. Gaps abiertos (todos con status `requested`, 2026-08-20)

- Base opt-in: formato, campos definitivos, volumen, fecha de entrega. [F1]
- Contenido MLR: contenido de lanzamiento, duración del ciclo, firmante final por plantilla. [F2]
- Contacto PV: nombre y correo del designado; timing de reporte de AE no documentado. [F3]
- Twilio: E-RUT de Lab Chile para el regulatory bundle (solicitado 25-ago). [F4, F7]
- Portafolio de medicamentos y especialidades objetivo: sin documentar en fuentes disponibles. [F1–F7]
