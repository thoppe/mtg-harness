# Contract: Replay Reduction

## Purpose

Make replay an executable property rather than an assertion over event labels.

## Guarantee

Given the same explicit setup input and an accepted-action log, the replay
reducer must produce an equivalent state and event sequence. Equivalence includes
turn state, zones and their ordering, object state, life totals, mana pools,
combat state, and stack state.

## Required Boundaries

- Accepted player actions are represented by the immutable action models with
  stable action type and complete payload before or alongside their resulting
  engine events.
- Automatic transitions remain events, but are recomputed by the reducer rather
  than treated as an unvalidated source of truth.
- The accepted-action log is trusted replay input and may contain private
  choice selections. The public event log is an observation stream and must
  retain the redaction guarantees in `replay-event-log.md`; it is not a
  substitute for private replay input.
- The reducer rejects malformed, out-of-order, or illegal actions rather than
  silently producing a divergent state.
- Tests for each implemented action family must include at least one replay
  equivalence assertion once that family is migrated to the reducer.

## v0 Migration

- Existing trace tests remain useful event-vocabulary checks.
- The reducer now covers setup, first-turn start, land play, mana and supported
  nonmana abilities, casting, priority passing, the current combat
  declarations, and an explicit turn handoff from combat damage through
  cleanup into the next precombat main. Equivalence
  tests cover land play, mana production, creature casting, targeted
  noncreature casting and resolution, both stack passes, and an empty combat
  through attacker and blocker declaration. A `Personal Tutor` regression also
  covers private choice resolution, deterministic shuffle, reveal, and
  library-top placement. A `Capricious Sorcerer` regression crosses two turn
  handoffs before activation, proving source aging, activation, stack
  resolution, state, and event equivalence; add equivalent tests as each
  remaining action family is widened.

## Related Contracts

- `docs/contracts/replay-event-log.md`
- `docs/contracts/deterministic-game-setup.md`
- `docs/contracts/stack-and-priority.md`
