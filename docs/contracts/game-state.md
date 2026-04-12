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
- Deterministic replay must be possible from explicit setup inputs plus the append-only event log.

## v0 Required State Partitions

- `players`: identifiers, life totals, and ownership relations
- `turn_state`: active player, step, and priority holder
- `zones`: library, hand, battlefield, graveyard, and stack
- `objects`: stable object records keyed independently from their current zone
- `mana_pools`: at minimum the five basic colors needed for the declared `Portal` micro-universe
- `rng_state`: deterministic seed and any derived RNG cursor state
- `damage_marks`: creature damage marked on objects until cleared by later turn handling

## v0 State Rules

- Hidden-zone ordering must be stable and replayable.
- Zone movement must preserve object identity across transitions.
- The engine may derive convenience views, but replay cannot depend on untracked derived state.
- The first slice may omit counters, attachments, and status markers not required by the declared micro-universe.
- Damage marked on creatures must be represented explicitly rather than inferred only from event history.

## Open Questions

- What state should be persisted for debugging versus recomputed on demand?
- Should hidden information be modeled directly or through player-relative views?
