---
id: cmd-pron-serve
system: pron
command_path: serve
synopsis: Keep one or more worlds open and answer sentences over a Unix socket (spec
  11 §8, 12 §7).
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:cli_command
provenance: src/pron/cli/main.py:_cmd_serve
---

# serve

## Synopsis

Keep one or more worlds open and answer sentences over a Unix socket (spec 11 §8, 12 §7).

## Purpose

Keep one or more worlds open and answer sentences over a Unix socket (spec 11 §8, 12 §7).

## How It Works

Imports, caches and sessions are paid once; `say`, `repl` and runtimes use the socket
while it listens. --world is repeatable, as PATH or NAME=PATH; the first is the default
and its .pron/serve.sock is the daemon's socket unless --socket says otherwise; every
other world gets a .pron/serve.sock pointing at it. A caller from another world may
open only the projections a world exposes. Runs in the foreground until --stop is
sent from another shell or the process is interrupted; --mount NAME=PATH adds a world
to a running daemon.

## Arguments

--world | required | World root, or NAME=PATH; repeatable, the first is the default
--pythonpath | optional | Project path where the worlds' models import from
--socket | optional | Socket path (default: the first world's .pron/serve.sock)
--stop | optional | Stop the server listening at the socket
--mount | optional | NAME=PATH to add a world to the running daemon

## Usage

pron serve --world . [--world other=../other] [--pythonpath .] [--socket PATH]
  pron serve --world . --mount other=../other
  pron serve --world . --stop
