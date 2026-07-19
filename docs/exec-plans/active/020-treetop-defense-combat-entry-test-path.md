# Execution Plan: Treetop Defense Combat-Entry Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
Treetop Defense attackers-window regression reach its response window through
supported turn and combat actions instead of directly constructing combat and
turn state.

## Scope

- Preserve the existing manifest-backed Wave 2 card and rule boundary.
- Keep battlefield fixture construction explicit; this increment corrects only
  the combat-entry shortcut named by `engine/package-plan.md`.
- Enter the first turn, advance to combat, and declare Border Guard as an
  attacker through supported flow handlers before exercising the existing
  mana, instant, priority, blockers, damage, and cleanup path.
- Make no source, card, coverage-manifest, contract-behavior, or engine-behavior
  change.

## Verification

- Run the focused Treetop Defense priority regression.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The Treetop Defense attackers-window regression now reaches its response
  window through first-turn entry, step advancement, and accepted attacker
  declaration.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the accepted-action combat-entry and cleanup path in this
regression.
