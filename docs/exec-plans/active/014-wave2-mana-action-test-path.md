# Execution Plan: Wave 2 Mana-Action Test Path

## Goal

Close the smallest explicit engine test-harness shortcut by making the Wave 2
targeted-spell enumeration regression obtain mana through accepted basic-land
mana actions instead of directly replacing a player's mana pool.

## Scope

- Preserve the existing manifest-backed Wave 2 card and rule boundary.
- Keep battlefield fixture construction explicit; this increment corrects only
  the mana-production shortcut named by `engine/package-plan.md`.
- Exercise each required white, blue, and green mana source through
  `ActivateManaAbilityAction` and the ordinary turn-flow handler.
- Make no source, card, coverage-manifest, or engine behavior change.

## Verification

- Run the focused Wave 2 regression module.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The targeted-spell enumeration regression now reaches precombat main through
  normal turn start and fills its mana pool only through accepted basic-land
  mana actions.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the accepted-action mana path in this regression.
