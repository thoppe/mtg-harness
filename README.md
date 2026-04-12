# mtg-harness

`mtg-harness` is a planned Python project for simulating Magic: The Gathering game play.

The repository is intentionally starting in a harness-engineering style:

- root files stay short and navigational
- `docs/` is the system of record
- plans and contracts are versioned before implementation

## Current Status

This repository is in planning mode. No implementation code has been added yet.

## Intended Major Components

- Knowledge ingestion for cards, oracle text, keywords, and rules references
- Core game and rules execution engine
- CLI-facing interaction layer
- Browser-facing API/backend layer for a future viewer/player

## Repository Layout

- `AGENTS.md`: short operating map for agents
- `HUMAN_INPUT.md`: human-owned constraints, decisions, and open questions
- `docs/`: contracts, architecture notes, design docs, references, and execution plans
- `information/`: external-source pull scripts, tests, and pulled source artifacts
- `engine/`: Python package for engine implementation and engine tests

## How To Use This Repo Right Now

1. Start with `HUMAN_INPUT.md` for currently fixed constraints and unresolved decisions.
2. Read `docs/index.md` for the knowledge map.
3. Use the active execution plan in `docs/exec-plans/active/` to drive the next changes.

## Immediate Goal

Define enough contracts and architecture to begin implementation of a Python-first simulation backend without locking in premature UI work.
