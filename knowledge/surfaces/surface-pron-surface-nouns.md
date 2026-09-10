---
id: surface-pron-surface-nouns
system: pron
surface: surface.nouns
tags:
- system:pron
- domain:system_architecture
- kind:software
- impl:here
- entity:module
provenance: src/pron/surface/nouns.py
---

# surface.nouns

## Purpose

Noun phrases: from a run of classified items to a scope and predicates (spec 02).

## How It Works

A noun phrase is a head (a model word, an alias for a model, or a referent) with a
determiner before it and modifiers after it. Modifiers are, in order of trial:
a proper name ("the client Ana", "the bridges one"), a value word ("the pending
reservations"), a predicate alias with its slots ("on the terrace", "for 6"), or a
field word followed by a value ("with capacity 6"). Every modifier becomes one
sldb predicate. A modifier whose word belongs to a model outside the head's family
is skipped for this phrase and left for the sentence.

"of X" after the head, and "X's" before it, are complements: what X is gets decided
at resolution (spec 02), in this order: a value of a field of the head, a document of
another class the head is related to (then the phrase crosses the edges of that
relation with its own predicates), a proper name of the head itself.

## Commands

NounPhrase
find_noun_phrases
field_is_string
value_run
