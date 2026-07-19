# Execution Plan: Summer Bloom Turn-Action Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
Summer Bloom additional-land regression enter precombat main through the
supported first-turn flow instead of directly replacing the turn step.

## Scope

- Preserve the existing manifest-backed Portal sorcery-wave card and rule
  boundary.
- Keep spell resolution fixture construction explicit; this increment corrects
  only the initial turn-state shortcut named by `engine/package-plan.md`.
- Enter the first precombat main phase through `start_first_turn`, then retain
  the existing direct resolution and accepted land-play path.
- Make no source, card, coverage-manifest, contract-behavior, or engine-behavior
  change.

## Verification

- Run the focused Summer Bloom regression.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The Summer Bloom additional-land regression now enters precombat main through
  `start_first_turn` before resolving the spell and exercising all four
  accepted land plays.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the supported first-turn entry in this regression.
