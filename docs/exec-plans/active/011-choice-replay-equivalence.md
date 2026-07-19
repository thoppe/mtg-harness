# Execution Plan: Choice Replay Equivalence

## Goal

Close the smallest remaining replay-reducer evidence gap by proving exact state
and event equivalence for an accepted `ResolveChoiceAction`.

## Scope

- Use the already supported `Personal Tutor` path.
- Replay land play, mana activation, casting, both priority passes, the private
  sorcery selection, deterministic shuffle, reveal, and library-top placement.
- Add no card, source, manifest, rule-family, or engine behavior.

## Verification

1. Run the focused replay-reducer tests.
2. Run the complete engine and information test suites.
3. Parse all coverage YAML and run `git diff --check`.

## Status

Complete when the focused regression proves direct and replayed state/event
equivalence and the broader verification remains green.

## Resume Here

Return to the active source-strategy plan and select the smallest remaining
recorded in-slice limitation or manifest-backed `Portal` increment. Preserve
the direct replay evidence for choice resolution added by this increment.
