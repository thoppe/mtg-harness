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

## Non-Goals For Initial Slice

- Full comprehensive-rules coverage on day one
- UI-specific logic
- Real-time networking concerns
- Keyword abilities beyond what is required by the first playable slice

## Initial Slice Constraints

- All engine implementation code and tests live under `engine/`.
- The first playable slice is a two-player game only.
- The first playable card universe is exactly three card instances:
  - one `Border Guard`
  - one `Foot Soldiers`
  - one `Plains`
- Oracle text is the gameplay authority for cards; flavor text is ignored.
- The first slice should avoid keyword support unless a chosen initial card set requires it.

## Initial Engine Package Contracts

- `engine/` must expose a package layout that separates domain state, rules execution, and surface-facing orchestration.
- `engine/tests/` must mirror the main engine package areas closely enough that coverage is obvious from file layout.
- The first engine contract work should define:
  - game setup for the declared three-card universe
  - minimal zones and player state
  - legal actions available in the initial slice
  - deterministic turn progression for a two-player game

## Decisions Needed

- Replay/logging format
