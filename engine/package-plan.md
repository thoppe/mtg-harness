# Engine Package Plan

## Goal

Define the first package boundaries before writing engine code.

## Planned Initial Layout

- `engine/mtg_engine/`
  - `cards/`: loaded canonical card records and card-instance helpers
  - `state/`: players, zones, objects, mana pools, turn state
  - `actions/`: legal player actions in the initial slice
  - `flow/`: setup, turn structure, and priority orchestration
  - `events/`: append-only replay event definitions and logging helpers
  - `rules/`: executable rule families for the initial slice
  - `services/`: thin orchestration entry points used by CLI or later APIs when needed
- `engine/tests/`
  - setup and replay tests first
  - package-aligned tests as additional modules come online

## Boundary Rules

- `cards/` should not own ingestion logic.
- `state/` should not depend on `flow` or `rules`.
- `events/` should not own legality decisions.
- `rules/` should operate on explicit state and actions, not on UI concerns.
- `flow/` may coordinate state, events, and rules but must not hide rule decisions.
- `services/` may coordinate workflows but should stay thin.
- Tests should be written against the smallest contract that proves behavior.

## First Contracts To Define In Code

- initial game setup from the active support slice
- zone model for library, hand, battlefield, graveyard, and stack
- legal actions:
  - play land
  - tap a basic land for its intrinsic color
  - cast a creature spell
  - declare attackers
  - declare blockers
- turn skeleton sufficient to move from setup to combat

## Next Session Targets

- Add `flow/priority.py` for explicit priority and next-action availability.
- Continue replacing test-only mana or turn-state shortcuts when a normal
  engine path can provide them. The Wave 2 targeted-spell enumeration
  regression now produces mana through accepted basic-land activation actions.
  The Treetop Defense attackers-window regression now does the same for its two
  green mana and reaches cleanup through accepted priority, combat, and
  turn-flow actions rather than direct turn-state replacement. The Alabaster
  Dragon full-cost casting regression now also enters precombat main through
  the supported first-turn flow, as does the Summer Bloom additional-land
  regression. Other fixture shortcuts should be corrected only in similarly
  bounded increments. The Renewing Dawn resolution regression now also enters
  precombat main through the supported first-turn flow. The Treetop Defense
  attackers-window regression now also reaches that window through first-turn
  entry, step advancement, and an accepted attacker declaration rather than
  direct combat and turn-state construction. The Wave 3 vigilance regression
  now likewise enters its attacker declaration window through supported
  first-turn and combat-entry flow rather than direct turn state construction.
  The Alabaster Dragon death-trigger fixture now also enters precombat main
  through supported first-turn flow rather than direct turn-state
  construction. The shared Wave 3 combat fixture now likewise reaches the
  blockers declaration window through supported first-turn, attacker
  declaration, and priority flow rather than direct combat and turn-state
  construction. The shared Wave 4 combat fixture now reaches that window
  through the same supported flow rather than direct combat and turn-state
  construction.
- Keep `rules/` focused on consequences and checks, while `flow/` owns when action windows open and close.
