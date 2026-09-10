---
id: surface-pron-docs
system: pron
surface: docs
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/docs.py
---

# docs

## Purpose

pron's own knowledge base is derived from this repo (spec 08 step 9): a CliCommandDoc
per `_cmd_*` handler from its docstring and its argparse arguments, a SurfaceDoc per
module from its module docstring, a SpecDoc per chapter of source/spec, and one
`implements` edge from each module or command to every chapter its docstring cites
("spec 06", "spec 11 §2"). Nothing is hand-kept: the docstrings are the source.

## How It Works

pron's own knowledge base is derived from this repo (spec 08 step 9): a CliCommandDoc
per `_cmd_*` handler from its docstring and its argparse arguments, a SurfaceDoc per
module from its module docstring, a SpecDoc per chapter of source/spec, and one
`implements` edge from each module or command to every chapter its docstring cites
("spec 06", "spec 11 §2"). Nothing is hand-kept: the docstrings are the source.

## Commands

command_specs
surface_specs
spec_specs
synchronize_docs
