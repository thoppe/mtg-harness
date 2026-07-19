# Execution Plan: Alabaster Death First-Turn Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
Wave 3 Alabaster Dragon death-trigger fixture enter precombat main through the
supported first-turn flow instead of directly constructing that turn step.

## Scope

- Preserve the existing manifest-backed Alabaster Dragon trigger boundary.
- Keep battlefield fixture construction and lethal marked damage explicit;
  this increment corrects only the initial turn-state shortcut.
- Enter the first turn through `start_first_turn` before exercising the
  existing state-based-action and trigger-resolution assertions.
- Make no source, card, coverage-manifest, contract-behavior, or engine-behavior
  change.

## Verification

- Run the focused Wave 3 Alabaster trigger regressions.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The Alabaster Dragon death-trigger fixture now enters precombat main through
  supported first-turn flow.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the supported first-turn path in these regressions.
