# HUMAN_INPUT.md

This file captures decisions, constraints, and open questions that are explicitly owned by humans.

## Locked In

- Project type: Magic: The Gathering simulation platform
- Primary implementation language: Python
- Current phase: planning and repository scaffolding only
- Required root files: `AGENTS.md`, `HUMAN_INPUT.md`, `README.md`
- Contracts must live under `docs/`
- Frontend implementation is out of scope for now
- Planned interfaces eventually include both CLI and browser-facing experiences
- Canonical card data source: Scryfall
- Canonical game-rules source: Wizards of the Coast Comprehensive Rules
- Prefer text-based rule copies over PDF or DOCX when storing raw rules snapshots
- Scryfall ingestion should also download card images when needed, while respecting published API guidance and rate limits
- Rules implementation should progress from a raw/unimplemented corpus into explicitly implemented rule contracts
- Card implementation should progress from raw card data into explicitly supported set-based slices
- Prefer implementation planning by set rather than by isolated individual cards
- External information assets must live under `information/rules/` and `information/cards/`
- Information-pull code and tests must live under `information/`
- Card data files and card image files must be stored separately under `information/cards/`
- Initial target implementation set: `Portal` (`por`)
- Canonical card identity should be based on Scryfall cross-printing identity, with printing/set provenance stored separately

## Working Assumptions

- The backend should be designed so the rules engine is usable by both CLI and future browser-facing surfaces.
- The repository should optimize for agent legibility first: contracts, plans, and decisions must be discoverable in-repo.
- Early project work should bias toward explicit domain modeling over rapid prototype code.
- Raw source snapshots and implemented engine behavior are different artifacts and must not be conflated.

## Decisions To Make

- Simulation goal:
  - Full-rules fidelity, constrained format fidelity, or staged capability by mechanic family?
- Engine architecture:
  - Event-sourced engine, state machine, layered effect system, or hybrid?
- Determinism strategy:
  - What must be reproducible for testing, replay, and AI-vs-AI simulation?
- Priority game modes:
  - 1v1 first, multiplayer later, or multiplayer-aware from day one?
- API boundary:
  - Internal Python objects only at first, or stable JSON contracts early for future browser integration?
- Image policy:
  - Which image sizes, cache policy, and local storage conventions should be standard?
- Implementation progression:
  - Which sets should follow `Portal` as the next supported vertical slices?

## Near-Term Human Inputs Needed

- Choose the initial target format or rules envelope.
- Decide whether replayability and deterministic simulation are first-class requirements in v0.
- Choose the standard image variant to persist by default.

## Change Policy

- Add new human decisions here when they are policy-level, cross-cutting, or unresolved.
- Move stable, implementation-relevant details into `docs/` once they become contracts or architecture.
