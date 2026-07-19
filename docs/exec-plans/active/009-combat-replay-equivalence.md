# Execution Plan: Combat Replay Equivalence

## Goal

Close the replay-reduction evidence gap for the already-supported combat
declaration action family.

## Scope

- Preserve the active card, source, rule, and engine boundaries.
- Advance from precombat main to the first combat declaration window through
  the accepted `AdvanceStepAction`.
- Replay an empty attacker declaration, both intervening priority passes, and
  an empty blocker declaration.
- Assert complete state and event-log equivalence between direct transitions
  and the accepted-action reducer.
- Do not add combat-damage reduction, cards, mechanics, or action models.

## Status

- Phase: complete
- Completed: direct and reduced state/event equivalence through blocker
  declaration, including the combat-step event tail.

## Verification

- Run the focused replay-reducer tests.
- Run the complete engine and information suites.
- Parse all coverage YAML and run `git diff --check`.

## Resume Here

Return to the active source strategy plan and select the smallest remaining
recorded in-slice limitation or manifest-backed `Portal` increment. Preserve
this regression when widening replay into later combat transitions.
