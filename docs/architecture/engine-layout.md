# Engine Layout

## Repository Boundary

All engine implementation code and engine tests must live under `engine/`.

## Planned Layout

- `engine/`: Python package root
- `engine/tests/`: engine-specific tests

## Boundary Rule

- Ingestion code belongs in `information/`, not `engine/`.
- Simulation logic belongs in `engine/`, not `information/`.
- Shared contracts remain under `docs/contracts/` until code exists that realizes them.
