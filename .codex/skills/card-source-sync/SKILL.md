---
name: card-source-sync
description: Use when working on mtg-harness source acquisition for Scryfall cards, card images, or Wizards Comprehensive Rules. This skill defines the repo-specific workflow for downloading or refreshing source artifacts into information/cards and information/rules, enforcing oracle_id-based filenames, JPG image defaults, provenance capture, and manifest-aware scope checks before widening support.
---

# Card Source Sync

Use this skill for any task that downloads, refreshes, validates, or plans external source artifacts for this repository.

## What This Skill Owns

- Scryfall card metadata pulls
- Scryfall card image pulls
- Wizards Comprehensive Rules text pulls
- provenance capture for pulled artifacts
- checks that raw source updates do not silently claim engine support

## Repo Rules

- Pull code and pull tests live under `information/`.
- Rules artifacts live under `information/rules/`.
- Card metadata lives under `information/cards/data/`.
- Card images live under `information/cards/images/`.
- Canonical card metadata filename: `<oracle_id>.json`
- Canonical card image filename: `<oracle_id>.jpg` by default
- Canonical card identity uses Scryfall `oracle_id`.
- Raw source presence does not imply gameplay support.

## Workflow

1. Read `HUMAN_INPUT.md`, `docs/contracts/knowledge-sources.md`, and `docs/coverage/`.
2. Confirm the requested scope:
   - current micro-universe
   - broader `Portal`
   - rules snapshot refresh
3. For cards:
   - prefer bulk-data workflows for large syncs
   - use meaningful `User-Agent` and `Accept` headers
   - store one metadata file per card at `information/cards/data/<oracle_id>.json`
   - store one JPG image per card at `information/cards/images/<oracle_id>.jpg`
   - preserve printing-level provenance inside the metadata
4. For rules:
   - fetch the official plain-text Comprehensive Rules snapshot
   - store it under `information/rules/`
   - preserve source URL and effective date
5. After any pull plan or pull execution, identify whether coverage manifests or contracts need updates.

## Expansion Guardrail

When new cards are introduced, inspect their oracle text and structure for:

- new rule families
- activated or triggered abilities
- keywords
- unusual targeting or combat clauses
- replacement or prevention effects

If any appear, update planning docs and manifests before claiming implementation support.

## Current Scope Source

The active playable card universe is declared in `docs/coverage/slices/portal.initial.yaml`.
Do not copy that card list into this skill; read the manifest before pulling or widening sources.

Some source artifacts may exist outside the active support slice. Raw source presence is only acquisition state,
not an implementation claim.
