# System Overview

This document describes the intended high-level decomposition. It is provisional until the first implementation phase begins.

## Planned Subsystems

### 1. Knowledge Ingestion

Responsibilities:

- Gather card metadata, oracle text, keyword definitions, and rules references
- Normalize external sources into internal canonical representations
- Version imported snapshots and derived artifacts

### 2. Play Engine

Responsibilities:

- Represent game state and zones
- Validate and apply player actions
- Resolve turn structure, priority, stack behavior, and effects
- Produce deterministic state transitions and replayable logs

Chosen v0 shape:

- A deterministic state machine is the primary runtime controller.
- Accepted actions and resolved outcomes are recorded in an append-only event log.
- Replay is derived from explicit starting inputs plus the event log, not inferred from mutable state alone.

### 3. Interaction Surfaces

Responsibilities:

- CLI commands for setup, inspection, and simulation control
- Backend service contracts for a future browser-facing viewer/player

## Architectural Constraints

- Python is the primary implementation language.
- Core engine logic should not depend on any specific UI surface.
- Browser support should be achieved via backend contracts, not UI-coupled engine code.
- External sources must be normalized before entering the simulation core.
- Deterministic execution is required for tests and replay workflows in v0.
- The runtime state container, transition controller, event log, and rules evaluators must remain separable concerns.

## Expansion Guardrails

- Do not hardcode the engine around the current vanilla-creature slice in a way that prevents later insertion of replacement effects, triggers, or continuous-effect evaluation.
- Keep rule evaluation boundaries explicit so future subsystems can add:
  - state-based action passes
  - trigger generation and ordering
  - replacement and prevention checks
  - continuous-effect and layer evaluation
- Treat the event log as an audit and replay surface, not as a shortcut for collapsing all rules evaluation into ad hoc state mutation.

## Open Architecture Questions

- Where should continuous effects and dependency layers be modeled?
- How early should serialization and replay formats be frozen?
