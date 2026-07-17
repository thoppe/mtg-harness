# Contract: Replay Reduction

## Purpose

Make replay an executable property rather than an assertion over event labels.

## Guarantee

Given the same explicit setup input and an accepted-action log, the replay
reducer must produce an equivalent state and event sequence. Equivalence includes
turn state, zones and their ordering, object state, life totals, mana pools,
combat state, and stack state.

## Required Boundaries

- Accepted player actions are recorded with stable action type and complete
  payload before or alongside their resulting engine events.
- Automatic transitions remain events, but are recomputed by the reducer rather
  than treated as an unvalidated source of truth.
- The reducer rejects malformed, out-of-order, or illegal actions rather than
  silently producing a divergent state.
- Tests for each implemented action family must include at least one replay
  equivalence assertion once that family is migrated to the reducer.

## v0 Migration

- Existing trace tests remain useful event-vocabulary checks.
- Add reducer coverage first for setup, land play, mana abilities, casting,
  priority passing, and the current combat declarations. Expand from there.

## Related Contracts

- `docs/contracts/replay-event-log.md`
- `docs/contracts/deterministic-game-setup.md`
- `docs/contracts/stack-and-priority.md`
