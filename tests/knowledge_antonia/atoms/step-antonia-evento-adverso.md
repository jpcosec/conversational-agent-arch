---
id: step-antonia-evento-adverso
title: Evento adverso — derivacion
atom_type: step
kind: handout
tags:
- conversation:steps.evento_adverso
- system:laboratorio-chile
domain_ref: psp-selfix
---

# Evento adverso — derivacion

## Instructions

Responder con calidez y sin alarmar. No interpretar la gravedad ni dar indicaciones clinicas. Registrar internamente el evento con fecha, hora y texto textual para derivacion a farmacovigilancia. Indicar que un profesional la contactara y que si es urgente acuda a su medico o urgencia.

## Required Slots

descripcion del sintoma, si es urgente

## Handout Target

farmacovigilancia Laboratorio Chile / medico tratante

## Tool

no aplica

## Allowed Transitions

conversation:steps.despedida

## Grounding Atoms

rule-antonia-eventos-adversos, boundary-antonia-clinico

## Completion Condition

El evento quedo registrado para derivacion y la persona sabe que el equipo la contactara.
