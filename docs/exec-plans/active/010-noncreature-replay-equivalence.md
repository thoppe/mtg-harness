# Execution Plan: Noncreature Replay Equivalence

## Goal

Close the smallest remaining replay-reducer evidence gap by proving exact state
and event equivalence for one already-supported targeted noncreature spell.

## Scope

- Use manifest-backed `Sorcerous Sight` as the one-mana, first-turn replay path.
- Cover land play, mana activation, targeted sorcery casting, both priority
  passes, hand inspection, draw, and stack-to-graveyard resolution.
- Do not change card, source, rule, manifest, or engine support scope.

## Verification

- Run the focused replay-reducer regression.
- Run the complete engine and information suites.
- Parse the coverage manifests and run `git diff --check`.

## Status

- Phase: complete
- Four focused reducer tests pass.
- All 190 engine tests and all 6 information tests pass.
- Coverage YAML parsing and `git diff --check` pass.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or manifest-backed `Portal` increment. Preserve
the exact accepted-action replay equivalence established here for targeted
noncreature casting and resolution.
