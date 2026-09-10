---
id: cmd-pron-repl
system: pron
command_path: repl
synopsis: Talk to a world, one sentence per line.
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:cli_command
provenance: src/pron/cli/main.py:_cmd_repl
---

# repl

## Synopsis

Talk to a world, one sentence per line.

## Purpose

Talk to a world, one sentence per line.

## How It Works

The same session as `say`, kept open: pending questions and referents survive between
lines. `:trace` toggles the trace, `:lexicon [MODEL]` lists words, `:quit` leaves.
Through the running server when one listens; --local opens the world here.

## Arguments

--world | optional | World root (contains .sldb)
--pythonpath | optional | Project path where the world's models import from
--projection | optional | 
--speaker | optional | 
--now | optional | 
--local | optional | Open the world here even if a server listens
--socket | optional | The daemon's socket, when the world's .pron/serve.sock is not it
--home | optional | The caller's own world (name or path); another world opens only its exposed projections

## Usage

pron repl --world . [--projection all] [--speaker me] [--local]
