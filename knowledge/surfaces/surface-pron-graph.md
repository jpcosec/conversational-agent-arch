---
id: surface-pron-graph
system: pron
surface: graph
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/graph.py
---

# graph

## Purpose

The only door to kgdb: read edges of the typed graph the projector built (spec 03, 10).

## How It Works

pron never writes to kgdb. The graph lives at <world>/.pron/graph.nx.json, built by
`kgdb ingest --store` through its library (see pron.world.World.refresh). It is fresh
when the model hashes it was built from are the store's current ones (the ledger's
model excluded); otherwise every read says so and callers fall back to sldb.

## Commands

doc_id
model_id
relation_type_id
field_id
tag_id
kind
bare
Graph
