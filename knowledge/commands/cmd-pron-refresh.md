---
id: cmd-pron-refresh
system: pron
command_path: refresh
synopsis: Rebuild the world's indexes and its typed graph.
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:cli_command
provenance: src/pron/cli/main.py:_cmd_refresh
---

# refresh

## Synopsis

Rebuild the world's indexes and its typed graph.

## Purpose

Rebuild the world's indexes and its typed graph.

## How It Works

sldb stores update, then kgdb's typed ingest into .pron/graph.nx.json, in-process.

## Arguments

--world | optional | World root (contains .sldb)
--pythonpath | optional | Project path where the world's models import from

## Usage

pron refresh --world .
