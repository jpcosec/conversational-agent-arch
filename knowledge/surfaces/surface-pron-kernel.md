---
id: surface-pron-kernel
system: pron
surface: kernel
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/kernel.py
---

# kernel

## Purpose

The kernel: the action verbs, each one an sldb write (spec 04), plus refresh and undo
(spec 11 §7). Every write is pre-validated, guarded by the document's hash_c, recorded
with its previous value, and followed by a re-evaluation of the conditions of the edges
around the document. Nothing here knows any model.

## How It Works

The kernel: the action verbs, each one an sldb write (spec 04), plus refresh and undo
(spec 11 §7). Every write is pre-validated, guarded by the document's hash_c, recorded
with its previous value, and followed by a re-evaluation of the conditions of the edges
around the document. Nothing here knows any model.

## Commands

Write
Kernel
