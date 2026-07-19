# Execution Plan: Wave 4 Attackers-Step Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
shared Wave 4 attacker-legality fixture reach its attacker declaration window
through supported first-turn and combat-entry flow instead of directly
constructing precombat main and the attackers step.

## Scope

- Preserve the existing manifest-backed Wave 4 card, Haste, and Defender
  boundaries.
- Enter the first turn, place the selected fixture creature onto the
  battlefield during that turn, and advance to combat through the supported
  flow handler before exercising the existing attacker-legality assertions.
- Remove the fixture-only turn-number parameter because none of these
  name-scoped legality assertions requires a later turn.
- Make no source, card, coverage-manifest, contract-behavior, or
  engine-behavior change.

## Verification

- Run the focused Wave 4 regressions.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The shared Wave 4 attacker-legality fixture now reaches its attacker
  declaration window through supported first-turn and combat-entry flow.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the supported Wave 4 attacker-window path in these
regressions.
