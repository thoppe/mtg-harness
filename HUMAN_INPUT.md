# HUMAN_INPUT.md

This file captures decisions, constraints, and open questions that are explicitly owned by humans.

## Locked In

- Project type: Magic: The Gathering simulation platform
- Primary implementation language: Python
- Current phase: narrow v0 engine slice with in-repo source artifacts, contracts, and initial implemented gameplay support
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
- The active playable micro-universe is defined exclusively by
  `docs/coverage/slices/portal.initial.yaml`; do not copy its card membership
  into this human-input file.
- Multiplicity within the initial micro-universe follows normal game rules and scenario setup needs
- Initial play mode is two-player normal play structure only
- For this initial slice, oracle text is the only gameplay text authority; flavor text is never used for implementation
- Keyword and combat-text support is limited to the active manifest and its
  bounded contracts, including the original `Flying`, `Reach`, `Swampwalk`,
  and `Defender` support plus Wave 2's temporary `Forestwalk` and name-scoped
  attack/block restrictions; broader keyword support remains deferred
- Default persisted card image asset type: JPG
- Deterministic simulation and replayability are first-class requirements in v0, especially for tests
- The first engine architecture pattern is a deterministic state machine with an append-only event log

## Working Assumptions

- The backend should be designed so the rules engine is usable by both CLI and future browser-facing surfaces.
- The repository should optimize for agent legibility first: contracts, plans, and decisions must be discoverable in-repo.
- Early project work should bias toward explicit domain modeling over rapid prototype code.
- Raw source snapshots and implemented engine behavior are different artifacts and must not be conflated.
- "standard play format" is interpreted here as normal two-player gameplay structure, not current Standard-constructed legality enforcement.

## Decisions To Make

- Simulation goal:
  - Full-rules fidelity, constrained format fidelity, or staged capability by mechanic family?
- Priority game modes:
  - 1v1 first, multiplayer later, or multiplayer-aware from day one?
- API boundary:
  - Internal Python objects only at first, or stable JSON contracts early for future browser integration?
- Implementation progression:
  - Which sets should follow `Portal` as the next supported vertical slices?

## Near-Term Human Inputs Needed

- No immediate human input is required for the current v0 rules slice.

## Change Policy

- Add new human decisions here when they are policy-level, cross-cutting, or unresolved.
- Move stable, implementation-relevant details into `docs/` once they become contracts or architecture.
