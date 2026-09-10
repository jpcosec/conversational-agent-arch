---
id: cmd-pron-check
system: pron
command_path: check
synopsis: Run pron's lints over a world and fail on any violation.
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:cli_command
provenance: src/pron/cli/main.py:_cmd_check
---

# check

## Synopsis

Run pron's lints over a world and fail on any violation.

## Purpose

Run pron's lints over a world and fail on any violation.

## How It Works

Run pron's lints over a world and fail on any violation.

## Arguments

--world | optional | World root (contains .sldb)
--pythonpath | optional | Project path where the world's models import from

## Usage

pron check --world .
