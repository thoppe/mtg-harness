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

### 3. Interaction Surfaces

Responsibilities:

- CLI commands for setup, inspection, and simulation control
- Backend service contracts for a future browser-facing viewer/player

## Architectural Constraints

- Python is the primary implementation language.
- Core engine logic should not depend on any specific UI surface.
- Browser support should be achieved via backend contracts, not UI-coupled engine code.
- External sources must be normalized before entering the simulation core.

## Open Architecture Questions

- Should rules evaluation be centered on an event log, direct state transitions, or a mixed model?
- Where should continuous effects and dependency layers be modeled?
- How early should serialization and replay formats be frozen?
