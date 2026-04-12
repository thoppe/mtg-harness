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
- Canonical card metadata filename convention: `information/cards/data/<oracle_id>.json`
- Canonical card image filename convention: `information/cards/images/<oracle_id>.<ext>`
- All engine implementation code and tests must live under `engine/`
- Initial playable micro-universe is exactly three card instances:
  - one copy of `Border Guard` from `Portal`
  - one copy of `Foot Soldiers` from `Portal`
  - one copy of `Plains` from `Portal`
- Initial play mode is two-player normal play structure only
- For this initial slice, oracle text is the only gameplay text authority; flavor text is never used for implementation
- No keyword ability support is required in the initial micro-universe
- Default persisted card image asset type: JPG

## Working Assumptions

- The backend should be designed so the rules engine is usable by both CLI and future browser-facing surfaces.
- The repository should optimize for agent legibility first: contracts, plans, and decisions must be discoverable in-repo.
- Early project work should bias toward explicit domain modeling over rapid prototype code.
- Raw source snapshots and implemented engine behavior are different artifacts and must not be conflated.
- "standard play format" is interpreted here as normal two-player gameplay structure, not current Standard-constructed legality enforcement.

## Decisions To Make

- Simulation goal:
  - Full-rules fidelity, constrained format fidelity, or staged capability by mechanic family?
- Determinism strategy:
  - What must be reproducible for testing, replay, and AI-vs-AI simulation?
- Priority game modes:
  - 1v1 first, multiplayer later, or multiplayer-aware from day one?
- API boundary:
  - Internal Python objects only at first, or stable JSON contracts early for future browser integration?
- Implementation progression:
  - Which sets should follow `Portal` as the next supported vertical slices?
- Engine architecture:
  - Event-sourced engine, state machine, layered effect system, or hybrid?

## Near-Term Human Inputs Needed

- Decide whether replayability and deterministic simulation are first-class requirements in v0.
- Decide the first engine architecture pattern.

## Change Policy

- Add new human decisions here when they are policy-level, cross-cutting, or unresolved.
- Move stable, implementation-relevant details into `docs/` once they become contracts or architecture.
