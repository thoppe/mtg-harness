# Contract: Deterministic Game Setup

## Purpose

Define the explicit inputs required to create a reproducible initial game state
for the current active support slice.

## v0 Scope

- Two players only
- Active support slice only, as declared in `docs/coverage/slices/portal.initial.yaml`
- Rules-harness setup may use any multiplicity of those card identities that a
  scenario requires
- The explicit ME4 `Rain of Daggers` testbed is allowed only in a dedicated
  rules-harness scenario. A Portal deck or future deck-construction path must
  exclude it even though it remains loadable for engine tests.

## Legal Deck Game Setup

Playable Portal games must begin through the validated deck path in
`deck-construction-and-game-start.md`, not through an arbitrary ordered
library. That path supplies profile, deck lists, deterministic shuffle,
opening hands, and London-mulligan decisions.

## Rules-Harness Setup Inputs

- `game_id`: stable identifier for the game instance under test or replay
- `players`: ordered list of exactly two player identifiers
- `starting_player`: identifier of the player who takes the first turn
- `libraries`: ordered card lists for each player
- `opening_hands`: explicit opening hand card lists for each player, or a declared draw procedure driven by the seed
- `rng_seed`: deterministic seed used for any randomized operation
- `starting_life_total`: integer life total for each player
- `mulligan_policy`: explicit policy identifier, even if v0 fixes this to a simplified no-mulligan path

## Guarantees

- The engine must be able to build the same initial state from the same setup inputs.
- Hidden information ordering must be reproducible from the recorded setup inputs.
- Tests may bypass shuffle behavior by supplying explicit ordered libraries and opening hands.
- If a setup helper derives any value from randomness, the helper must record enough information to reproduce that derivation.

## Rules-Harness Simplifications

- The rules harness may use preconstructed ordered libraries rather than a full deck-construction flow.
- The rules harness may fix mulligans to a documented simplified path.
- The first engine slice may use explicit opening hands in tests instead of draw-step derivation.

## Invalid Setup Conditions

- Any card outside the active support slice
- Any player count other than two
- Missing or duplicate player identifiers
- Missing `rng_seed`
- Library or opening-hand contents that cannot be reconciled with declared player card pools
- `Rain of Daggers` in any setup declared to be a Portal deck rather than a
  dedicated rules-harness scenario

## Related Contracts

- `docs/contracts/game-state.md`
- `docs/contracts/play-engine.md`
- `docs/contracts/replay-event-log.md`
