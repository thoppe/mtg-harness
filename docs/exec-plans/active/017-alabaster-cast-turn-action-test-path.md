# Execution Plan: Alabaster Cast Turn-Action Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
Alabaster Dragon full-cost casting regression enter precombat main through the
supported first-turn flow instead of directly replacing the turn state.

## Scope

- Preserve the existing manifest-backed Wave 3 card and rule boundary.
- Keep battlefield fixture construction explicit; this increment corrects only
  the initial turn-state shortcut named by `engine/package-plan.md`.
- Enter the first precombat main phase through `start_first_turn`, then retain
  the existing accepted mana activation, casting, priority, and resolution
  path.
- Make no source, card, coverage-manifest, contract-behavior, or engine-behavior
  change.

## Verification

- Run the focused Alabaster Dragon casting regression.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The Alabaster Dragon full-cost casting regression now enters precombat main
  through `start_first_turn` before producing mana, casting, passing priority,
  and resolving the creature spell.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the supported first-turn entry in this regression.
