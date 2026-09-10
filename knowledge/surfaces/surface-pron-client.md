---
id: surface-pron-client
system: pron
surface: client
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/client.py
---

# client

## Purpose

The client of a running `pron serve` (spec 11 §8): stdlib only, so `pron say` through a
server costs a process start and a socket round trip, not sldb's imports. A request is one
connection, one JSON object per line.

## How It Works

The client of a running `pron serve` (spec 11 §8): stdlib only, so `pron say` through a
server costs a process start and a socket round trip, not sldb's imports. A request is one
connection, one JSON object per line.

## Commands

socket_path
request
alive
RemoteSession
RemoteGraph
RemoteWorld
