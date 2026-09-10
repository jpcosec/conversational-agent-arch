---
id: cmd-pron-init
system: pron
command_path: init
synopsis: Make a store a pron world.
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:cli_command
provenance: src/pron/cli/main.py:_cmd_init
---

# init

## Synopsis

Make a store a pron world.

## Purpose

Make a store a pron world.

## How It Works

Runs kgdb init (typed relations) and registers pron's models: AnchorDoc, ProjectionDoc,
MoveDoc; with --knowledge also SpecDoc, the command and module docs, and the relation
type implements, for pron's own knowledge base. Idempotent.

With --template DIR, the world is born with the words, projections and relation
types the template holds (anchors/, projections/, relations/types/, relations/).

## Arguments

--world | optional | World root (contains .sldb)
--pythonpath | optional | Project path where the world's models import from
--knowledge | optional | Also what pron's own knowledge base needs
--template | optional | World template directory: anchors/, projections/, relations/types/, relations/

## Usage

pron init --world . [--pythonpath .] [--knowledge] [--template DIR]
