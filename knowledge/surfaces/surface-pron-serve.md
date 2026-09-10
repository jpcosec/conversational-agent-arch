---
id: surface-pron-serve
system: pron
surface: serve
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/serve.py
---

# serve

## Purpose

Serve worlds: one process keeps one store open, the daemon's, with the nodes' stores
linked into it; each world is a projection over its own store, and every local caller
(the CLI, the REPL, an agent runtime) says its sentences through the socket instead of
opening a store again (spec 01 §Un mundo en varios stores, 11 §8, 12 §7).

## How It Works

One request per connection, one JSON object per line. Requests are handled one at a
time: a store has one writer, and a turn is short. Each request names the world it
speaks to (a linked store, or the daemon's own) and the caller's own world, `home`; a
caller whose home is another world may open only the projections that world exposes,
its interface lexicon, and nothing else (spec 12 §6): talking to another world is
semantic, never access to its store. The server speaks as whoever the client says it is;
identity is the application's (11 §6). Every mounted world gets `<root>/.pron/serve.sock`
pointing at the daemon's socket, so a client that only knows its world finds the daemon.
The client side is pron.client.

## Commands

Server
