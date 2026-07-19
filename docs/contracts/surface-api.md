# Contract: Surface API

## Purpose

Define the boundary between the backend engine and user-facing surfaces.

## Principles

- The play engine must be callable from a CLI without special-case logic.
- Future browser integration should use explicit serialized contracts rather than internal Python object sharing.
- Surface-specific formatting should be outside the simulation core.
- The initial engine surface only needs to serve a two-player local game flow.
- Reusable terminal presentation helpers may live alongside the engine as a surface-support package, so long as they consume engine state and events without embedding rules decisions.

## Candidate Interface Types

- In-process Python game-session service for CLI workflows, started from two
  validated decks and exposing legal actions, state, accepted actions, replay,
  and terminal outcome
- Serialized request/response contracts for browser-facing use later
- Replay or event stream format for inspection tools

## Open Questions

- When should JSON contracts become stable?
- The CLI should call the game-session service rather than transitions directly;
  the service is the future browser boundary.
