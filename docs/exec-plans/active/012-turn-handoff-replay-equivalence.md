# Execution Plan: Turn-Handoff Replay Equivalence

## Goal

Close the smallest remaining accepted-action replay gap without widening card,
rule-source, or support-manifest scope: make the existing combat-damage,
cleanup, and next-turn-start sequence replayable as one explicit turn-handoff
action, then prove a legal Wave 7 activated ability can be reconstructed after
its source has survived to its controller's next turn.

## Scope

- Add one immutable `AdvanceTurnAction` carrying the acting player.
- Accept it only for the active player in `combat_damage_step`, with no pending
  choice, then run the already-contracted combat damage, cleanup, and
  next-turn-start transitions.
- Route the action through the replay reducer.
- Add direct state-and-event equivalence coverage across two handoffs and a
  legal `Capricious Sorcerer` activation.
- Update the replay contract and active-plan resume notes.

## Boundaries

- No card, source artifact, coverage manifest, or rules-envelope membership
  changes.
- No new turn steps, priority windows, combat rules, activation predicates, or
  event families.
- The action is not a generic arbitrary-step skipper; it is valid only at the
  existing post-declaration combat-damage boundary.

## Verification

- Focused replay-reducer regression.
- Full engine and information test suites.
- Coverage YAML parse check and `git diff --check`.

## Status

- Phase: complete
