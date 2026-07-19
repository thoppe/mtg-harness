# Execution Plan: Renewing Dawn Turn-Action Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
Renewing Dawn resolution regression enter precombat main through the supported
first-turn flow instead of directly replacing the turn step.

## Scope

- Preserve the existing manifest-backed Portal sorcery-wave card and rule
  boundary.
- Keep battlefield and spell-resolution fixture construction explicit; this
  increment corrects only the initial turn-state shortcut named by
  `engine/package-plan.md`.
- Enter the first precombat main phase through `start_first_turn`, then retain
  the existing direct stack placement and resolution path.
- Make no source, card, coverage-manifest, contract-behavior, or engine-behavior
  change.

## Verification

- Run the focused Renewing Dawn regression.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The Renewing Dawn resolution regression now enters precombat main through
  `start_first_turn` before its existing direct stack placement and resolution
  assertions.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the supported first-turn entry in this regression.
