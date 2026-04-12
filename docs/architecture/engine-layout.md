# Engine Layout

## Repository Boundary

All engine implementation code and engine tests must live under `engine/`.

## Planned Layout

- `engine/`: Python package root
- `engine/tests/`: engine-specific tests

## v0 Architectural Shape

- The first engine will use a deterministic state machine with an append-only event log.
- Runtime state is authoritative for current game facts.
- The event log is authoritative for replay, traceability, and regression tests.

## Planned Package Boundaries

- `engine/state/`: game state, zones, turn markers, and player-visible facts
- `engine/actions/`: action declarations and action-validation inputs
- `engine/flow/`: turn structure, priority flow, and state-machine transitions
- `engine/events/`: append-only event types and replay/logging helpers
- `engine/rules/`: rules evaluators such as state-based checks, triggers, and later effect systems
- `engine/tests/`: package-aligned engine tests

## Expansion Guardrails

- Do not merge rules evaluation directly into state mutation helpers.
- Do not make the event log the only source needed to understand legal next actions; that remains the job of the state machine plus rules evaluators.
- Design package boundaries so later full-rules work can expand `engine/rules/` without replacing the flow and event foundations.

## Boundary Rule

- Ingestion code belongs in `information/`, not `engine/`.
- Simulation logic belongs in `engine/`, not `information/`.
- Shared contracts remain under `docs/contracts/` until code exists that realizes them.
