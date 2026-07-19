# Execution Plan: Treetop Defense Mana-Action Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
Treetop Defense attackers-window regression obtain green mana through accepted
basic-land mana actions instead of directly replacing the defending player's
mana pool.

## Scope

- Preserve the existing manifest-backed Wave 2 card and rule boundary.
- Keep battlefield and combat fixture construction explicit; this increment
  corrects only the mana-production shortcut named by `engine/package-plan.md`.
- Exercise both required Forests through `ActivateManaAbilityAction` and the
  ordinary attackers-step turn-flow handler before casting Treetop Defense.
- Make no source, card, coverage-manifest, contract-behavior, or engine-behavior
  change.

## Verification

- Run the focused Treetop Defense priority regression.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The Treetop Defense attackers-window regression now fills the defending
  player's mana pool only through two accepted Forest activation actions.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the accepted-action mana path in this regression.
