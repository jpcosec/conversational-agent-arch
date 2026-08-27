---
id: strategy-vitali-slot-presentation
title: Presentacion de horarios
atom_type: strategy
tags:
- conversation:strategy
- agent:booking-workflow
- system:vitali
provenance: null
summary: Ofrecer 5-7 opciones (2-3 dias, 2-3 bloques), horas limpias, y cerrar preguntando
  si sirve alguna.
embedding: null
parent: null
semantic_anchors: null
---

# Presentacion de horarios

## Goal

Que elegir un horario sea simple.

## Approach

Sugerir 2-3 dias proximos con disponibilidad, 2-3 bloques por dia (maximo 5-7 opciones). Formato: 'Tengo disponibilidad el [Dia, Fecha]: [hora], [hora], [hora]'. Cerrar con '¿Te sirve alguno de estos horarios?'. No listar todos los bloques. Redondear al bloque de 30 minutos mas cercano; usar horas limpias (3:00 PM, 3:30 PM), nunca horas raras como 2:41 PM.

## Priorities

Pocas opciones claras por sobre exhaustividad.
