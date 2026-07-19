# Execution Plan: Wave 3 Blockers-Step Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
shared Wave 3 combat fixture reach its blockers declaration window through
supported turn, attacker declaration, and priority flow instead of directly
constructing combat and the blockers step.

## Scope

- Preserve the existing manifest-backed Wave 3 card, combat, and trigger
  boundaries.
- Keep battlefield fixture construction and pre-existing attacker age
  explicit; this increment corrects only the turn and combat-entry shortcut.
- Enter the first turn, advance to combat, declare the selected attacker, and
  pass priority through the attackers window before exercising the existing
  flying, landwalk, blocking-restriction, and Alabaster combat assertions.
- Make no source, card, coverage-manifest, contract-behavior, or engine-behavior
  change.

## Verification

- Run the focused Wave 3 regressions.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The shared Wave 3 combat fixture now reaches its blockers declaration window
  through supported turn, attacker declaration, and priority flow.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the supported Wave 3 blockers-step path in these
regressions.
