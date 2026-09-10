---
id: surface-pron-surface-interpret
system: pron
surface: surface.interpret
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/surface/interpret.py
---

# surface.interpret

## Purpose

From a sentence to an Interpretation (spec 06): the six steps, with the world
consulted only at steps 2 (lexicon), 4 (addresses) and 5 (types).

## How It Works

The constructions are fixed and listed in patterns.yaml; a world never adds one, it
adds words. A sentence coordinated with "and" is one move with several parts.

## Commands

Part
Interpretation
examples
Interpreter
