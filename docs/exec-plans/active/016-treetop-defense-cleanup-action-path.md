# Execution Plan: Treetop Defense Cleanup-Action Test Path

## Goal

Close the next smallest explicit engine test-harness shortcut by making the
Treetop Defense attackers-window regression reach cleanup through accepted
combat and turn-flow actions instead of directly replacing the turn step.

## Scope

- Preserve the existing manifest-backed Wave 2 card and rule boundary.
- Keep battlefield and combat fixture construction explicit; this increment
  corrects only the post-resolution turn-state shortcut named by
  `engine/package-plan.md`.
- Pass priority through the remaining attackers window, declare no blockers,
  resolve combat damage, and enter cleanup through the ordinary flow handlers.
- Make no source, card, coverage-manifest, contract-behavior, or engine-behavior
  change.

## Verification

- Run the focused Treetop Defense priority regression.
- Run the full engine and information test suites.
- Parse every coverage YAML document and run `git diff --check`.

## Status

- Phase: complete
- The Treetop Defense attackers-window regression now passes priority through
  the rest of the response window, declares no blockers, resolves combat
  damage, and enters cleanup without directly replacing the turn step.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the accepted-action combat-to-cleanup path in this
regression.
