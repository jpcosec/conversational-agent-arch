---
id: cmd-pron-docs
system: pron
command_path: docs
synopsis: 'Regenerate pron''s own knowledge base from this repo: a CliCommandDoc per
  command, a'
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:cli_command
provenance: src/pron/cli/main.py:_cmd_docs
---

# docs

## Synopsis

Regenerate pron's own knowledge base from this repo: a CliCommandDoc per command, a

## Purpose

Regenerate pron's own knowledge base from this repo: a CliCommandDoc per command, a

## How It Works

SurfaceDoc per module, a SpecDoc per chapter of source/spec, and the implements edges
from each module to the chapters its docstring cites.

## Arguments

--world | optional | World root (contains .sldb)
--pythonpath | optional | Project path where the world's models import from
--check | optional | 

## Usage

pron docs --world . [--check]
