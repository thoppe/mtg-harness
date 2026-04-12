# Engine Package Plan

## Goal

Define the first package boundaries before writing engine code.

## Planned Initial Layout

- `engine/mtg_engine/`
  - `cards/`: loaded canonical card records and card-instance helpers
  - `game_state/`: players, zones, permanents, turn state
  - `actions/`: legal player actions in the initial slice
  - `rules/`: executable rule families for the initial slice
  - `services/`: setup and orchestration entry points used by CLI or later APIs
- `engine/tests/`
  - `cards/`
  - `game_state/`
  - `actions/`
  - `rules/`
  - `services/`

## Boundary Rules

- `cards/` should not own ingestion logic.
- `rules/` should operate on explicit state and actions, not on UI concerns.
- `services/` may coordinate workflows but must not hide rule decisions.
- Tests should be written against the smallest contract that proves behavior.

## First Contracts To Define In Code

- initial game setup from the declared micro-universe
- zone model for library, hand, battlefield, graveyard, and stack
- legal actions:
  - play land
  - tap Plains for white mana
  - cast a creature spell
  - declare attackers
  - declare blockers
- turn skeleton sufficient to move from setup to combat
