# Contract: Game State

## Purpose

Define the core state boundaries for simulation.

## Minimum State Areas

- Players
- Turn and phase structure
- Zones
- Objects on the stack
- Battlefield objects and attachments
- Life totals, counters, and status markers
- Randomness source / seed state

## Guarantees

- Game state transitions must be inspectable.
- The engine must be able to explain why a legal action was accepted or rejected.
- Deterministic replay must be possible if deterministic simulation is adopted as a project requirement.

## Open Questions

- What state should be persisted for debugging versus recomputed on demand?
- Should hidden information be modeled directly or through player-relative views?
