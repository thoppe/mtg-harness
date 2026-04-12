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
  - two `Border Guard`
  - one `Plains`
- Oracle text is the gameplay authority for cards; flavor text is ignored.
- The first slice should avoid keyword support unless a chosen initial card set requires it.

## Decisions Needed

- Replay/logging format
