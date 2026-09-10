---
id: cmd-pron-lexicon
system: pron
command_path: lexicon
synopsis: List what this projection can say.
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:cli_command
provenance: src/pron/cli/main.py:_cmd_lexicon
---

# lexicon

## Synopsis

List what this projection can say.

## Purpose

List what this projection can say.

## How It Works

Every word with its kind, what it names and its motive; with a model, the verbs that
class takes and its fields. Answers "what can I say?".

## Arguments

--world | optional | World root (contains .sldb)
--pythonpath | optional | Project path where the world's models import from
model | required | 
--projection | optional | 
--json | optional | 

## Usage

pron lexicon --world . [--projection all] [MODEL] [--json]
