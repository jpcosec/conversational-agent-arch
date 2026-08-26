---
# pill-xxx
id: pill-adr-compliance-farmacéutico-en-el-contenido-de-la-kb-antonia
# e.g., language:python, library:pydantic
tags:
- system:antonia
- domain:psp
- topic:compliance
---

# ADR: Compliance farmacéutico en el contenido de la KB Antonia

## What

_Define the context or guardrail this pill carries._

Restricciones de contenido para todo átomo nuevo de la KB Antonia: (1) Antonia nunca indica, sugiere ni comenta cambios de dosis — la titulación 0.25->0.5->1 mg solo se menciona como información del programa, nunca como indicación. (2) Nunca diagnostica ni interpreta síntomas. (3) Ante cualquier malestar reportado: calidez, sin alarmar, registro textual con fecha/hora, marca [EVENTO ADVERSO DETECTADO], derivación FV <24h. (4) MedInfo es distinto de EA: pregunta clínica sin reacción reportada -> ticket MedInfo, no FV. (5) Todo texto médico proviene del corpus cerrado aprobado (folleto ISP + material Medical); nada se inventa ni se complementa con conocimiento externo. (6) La autoridad sanitaria la reporta Laboratorio Chile, no la plataforma ni Antonia.

## Why

_Explain why this context matters for safe execution._

PSP es un programa farmacéutico regulado. Un átomo mal redactado se convierte en comportamiento del agente frente a pacientes reales. Los boundaries existentes (boundary-antonia-clinico, rule-antonia-anti-alucinacion) ya codifican parte de esto; los átomos nuevos deben ser consistentes con ellos, no contradecirlos.

## When

_Describe when an agent should apply this pill._

Al redactar el answer/instructions de cualquier átomo nuevo, y como checklist de revisión antes de indexar el lote.

## Where

_Name the files, surfaces, or scope this pill applies to._

knowledge/atoms/ — en particular los átomos nuevos de clasificación, MedInfo, policy gate y journey. Referencias: boundary-antonia-clinico, boundary-antonia-manipulacion, rule-antonia-eventos-adversos, rule-antonia-anti-alucinacion, fallback-antonia.

## How

_Describe the correct way to apply this guidance._

Antes de dar por bueno un átomo, leerlo contra los 6 puntos del what. Verificar que las derivaciones (FV, MedInfo, médico tratante) coinciden con el flujo del spec psp-flujo-atencion-chatbot.yml. Mantener el tono de style-antonia — cálido, cercano, claro, sin tecnicismos innecesarios. CORPUS — el folleto ISP y el material Medical NO están disponibles en ningún repo local (verificado). Fallback obligatorio mientras no exista el corpus — para átomos que requieren contenido clínico aprobado (atom-antonia-molecula), redactar solo el marco no-clínico (qué es el programa, que la molécula es semaglutida como dato del spec PSP, derivación al médico para todo lo demás) y marcar el átomo con provenance pendiente y un TODO explícito en el answer indicando que el contenido clínico se completará cuando Medical entregue el corpus. NUNCA rellenar con conocimiento general del LLM.

## How Not

_Describe the shortcut or failure mode to avoid._

No copiar textos clínicos de fuentes no aprobadas. No redactar criterios de gravedad de síntomas (eso es interpretación clínica). No prometer tiempos de respuesta distintos de los del programa (<24h FV). No dejar que un step de journey genere texto libre: journeys F0 son contenido preaprobado.
