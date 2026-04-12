# Project Scope

## Mission

Build a Python-first Magic: The Gathering simulation backend that can ingest authoritative game knowledge, execute games according to explicit rules models, and support both CLI and future browser-facing experiences.

## In Scope For Early Phases

- Repository scaffolding for agent-first development
- Card and rules knowledge-source evaluation
- Core simulation architecture
- Deterministic game-state and action modeling
- CLI-oriented workflows for driving and inspecting games
- Backend contracts suitable for later browser integration
- A tiny two-player playable slice starting from a restricted `Portal` micro-universe

## Out Of Scope For Early Phases

- Frontend implementation
- Visual polish
- Multiplayer UX
- Production deployment concerns

## Candidate Milestones

1. Decide data sources, rules envelope, and engine architecture.
2. Define package and contract layout.
3. Build ingestion pipeline and canonical domain models.
4. Build minimal deterministic game loop.
5. Add CLI workflows for setup, progression, and inspection.
6. Expose stable backend-facing contracts for a future browser client.
