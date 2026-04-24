# Contract: Play Engine

## Purpose

Describe the responsibilities of the simulation core.

## Engine Must Eventually Support

- Initial game setup from explicit inputs
- Turn progression
- Priority passing
- Action validation
- Stack resolution
- Triggered and activated abilities
- Deterministic logging of state transitions

## v0 Architecture Commitments

- The engine will use a deterministic state machine as the primary controller of legal progression.
- The engine will record accepted actions and resolved outcomes in an append-only event log.
- Replayable execution must be possible from explicit initial inputs plus recorded events.
- Tests must be able to assert deterministic traces, not only final states.

## Non-Goals For Initial Slice

- Full comprehensive-rules coverage on day one
- UI-specific logic
- Real-time networking concerns
- Keyword abilities beyond what is required by the first playable slice

## Initial Slice Constraints

- All engine implementation code and tests live under `engine/`.
- The first playable slice is a two-player game only.
- The first playable card universe is the active support slice declared in `docs/coverage/slices/portal.initial.yaml`.
- Setup scenarios may use multiple legal copies of card identities from the active support slice.
- Oracle text is the gameplay authority for cards; flavor text is ignored.
- The first slice should avoid keyword support unless a chosen initial card set requires it.

## Initial Engine Package Contracts

- `engine/` must expose a package layout that separates domain state, rules execution, and surface-facing orchestration.
- `engine/tests/` must mirror the main engine package areas closely enough that coverage is obvious from file layout.
- The first engine contract work should define:
  - game setup for the active support slice
  - minimal zones and player state
  - legal actions available in the initial slice
  - deterministic turn progression for a two-player game
- The first engine contract work should also define:
  - the initial event types required for deterministic replay
  - the boundary between transition control and rules evaluation
  - where future state-based actions, triggers, and continuous effects will attach

## v0 Contract References

- Deterministic setup inputs: `docs/contracts/deterministic-game-setup.md`
- State-machine transition points: `docs/contracts/state-machine-transitions.md`
- Replay event vocabulary: `docs/contracts/replay-event-log.md`
