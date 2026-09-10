---
id: surface-pron-session
system: pron
surface: session
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/session.py
---

# session

## Purpose

A session: one world, one projection, one speaker, and the turn loop (spec 06, 07, 11).

## How It Works

turn(sentence): read hash_mundo → interpret → resolve → verify → decide → execute →
refresh if written → write the MoveDoc → answer. Everything the turn did is in the
trace; every trace line is a real call.

## Commands

Session
