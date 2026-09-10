---
id: surface-pron-embedder
system: pron
surface: embedder
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/embedder.py
---

# embedder

## Purpose

The approximate-matching port and its no-network fallback.

## How It Works

An application injects an Embedder (spec 11 §2). Without one, pron matches with
difflib over accent-stripped strings, and says so in the trace. Neither ever
executes anything: they only rank neighbors to offer.

## Commands

Embedder
normalize
cosine
DifflibMatcher
Matcher
DocumentIndex
