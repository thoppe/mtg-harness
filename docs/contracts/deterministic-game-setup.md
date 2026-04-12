# Contract: Deterministic Game Setup

## Purpose

Define the explicit inputs required to create a reproducible initial game state for the first playable slice.

## v0 Scope

- Two players only
- Declared micro-universe only:
  - `Border Guard`
  - `Foot Soldiers`
  - `Muck Rats`
  - `Swamp`
  - `Forest`
  - `Island`
  - `Mountain`
  - `Plains`
- Setup may use any multiplicity of those card identities that the scenario requires

## Required Setup Inputs

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

## v0 Simplifications

- The first engine slice may use preconstructed ordered libraries rather than a full deck-construction flow.
- The first engine slice may fix mulligans to a documented simplified path.
- The first engine slice may use explicit opening hands in tests instead of draw-step derivation.

## Invalid Setup Conditions

- Any card outside the declared micro-universe
- Any player count other than two
- Missing or duplicate player identifiers
- Missing `rng_seed`
- Library or opening-hand contents that cannot be reconciled with declared player card pools

## Related Contracts

- `docs/contracts/game-state.md`
- `docs/contracts/play-engine.md`
- `docs/contracts/replay-event-log.md`
