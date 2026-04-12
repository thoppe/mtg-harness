# Execution Plan: Project Scaffold

## Goal

Create a durable, agent-legible repository scaffold for a Python-based Magic: The Gathering simulator before any implementation code is written.

## Status

- Phase: active
- Owner: repository scaffold

## Tasks

1. Create root navigation files.
2. Create docs index and major sections.
3. Seed initial contracts for knowledge ingestion, card modeling, game state, play engine, and surface API.
4. Capture open human decisions that block sound implementation.
5. Review the scaffold for gaps before writing code.

## Decision Log

- We are using a short `AGENTS.md` as a map into `docs/`, not as a monolithic instruction file.
- We are separating human-owned policy and decisions into `HUMAN_INPUT.md`.
- We are keeping frontend work out of scope while still reserving a backend-facing surface contract for later browser use.

## Exit Criteria

- A new contributor or agent can find the current scope, constraints, and open decisions from repository-local docs.
- Initial code work can start without inventing undocumented interfaces.

## Follow-On Plans

- Select knowledge sources and legal constraints.
- Decide engine architecture for the first implementation slice.
- Define Python package layout before creating modules.
