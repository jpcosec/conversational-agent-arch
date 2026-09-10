---
id: surface-pron-surface-tokens
system: pron
surface: surface.tokens
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/surface/tokens.py
---

# surface.tokens

## Purpose

Segmenting and classifying a sentence against the lexicon (spec 06 steps 1–2).

## How It Works

A sentence becomes a list of items. Each item is one of: `det`, `referent`, `wh`,
`conj`, `punct`, `number`, `literal`, `word` (one or more lexicon words sharing the
matched form, ambiguity kept), or `unknown`. Matching is greedy longest-first over
listed forms; forms may carry slots: N (a number), X (free text up to the next known
word), Z (an enum value), DAY and TIME (normalized by pron.surface.dates).

## Commands

Item
tokenize
Classifier
