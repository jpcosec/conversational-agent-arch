---
id: surface-pron-ids
system: pron
surface: ids
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/ids.py
---

# ids

## Purpose

Export ids and addresses, with the store they belong to (spec 02, 12 §5).

## How It Works

An export id is `Model:doc` for a document of the local store and `store:Model:doc` for
one of a store linked into it; an address is `st.{Model}.doc` or `store:st.{Model}.doc`
(sldb's own prefix form). `None` and "local" both mean the local store. Nothing else in
pron splits an id by hand.

## Commands

is_local
split_id
join_id
model_of
doc_of
store_of
scope
address_of
export_id
relativize
qualify
convert_record
normalize_address
