# Execution Plan: Wave 3 Vigilance Combat-Entry Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
Wave 3 vigilance regression reach its attacker declaration window through
supported turn and combat flow instead of directly constructing turn 2's
declare-attackers step.

## Scope

- Preserve the existing manifest-backed Wave 3 card and rule boundary.
- Keep battlefield fixture construction and pre-existing battlefield age
  explicit; this increment corrects only the turn and combat-entry shortcut.
- Enter the first turn and advance to combat through supported flow handlers
  before exercising the existing Archangel and Ardent Militia vigilance
  assertions.
- Make no source, card, coverage-manifest, contract-behavior, or engine-behavior
  change.

## Verification

- Run the focused Wave 3 vigilance regression.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The Wave 3 vigilance regression now reaches its attacker declaration window
  through supported first-turn and combat-entry flow.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the supported vigilance combat-entry path in this
regression.
