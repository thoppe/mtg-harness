# Execution Plan: Mind Rot Discard Choice

## Goal

Close the recorded `Mind Rot` hand-order simplification by making the targeted
player choose the cards discarded on resolution.

## Scope

This is a rule correction inside the active Portal support slice. It adds no
card or source artifacts and reuses the existing chooser-owned public-hand
decision surface.

## Required Stages

1. On resolution, snapshot the target player's hand and request exactly the
   lesser of two cards or that hand's current size.
2. Suspend the effect behind a target-player-owned `PendingDecision`; unrelated
   actions remain illegal until the choice resolves.
3. Validate distinct selected instances against the snapshotted hand options,
   discard them publicly, and preserve normal spell movement and replay events.
4. Cover non-first selection, short hands, chooser ownership, legal-action
   enumeration, and replay equivalence with focused regression tests.
5. Update coverage, contracts, and the active-plan resume note in the same
   verified commit.

## Status

- Phase: complete
- Completed: target-player ownership, exact short-hand cardinality, legal
  action enumeration, non-first selection, and replay-event coverage

## Resume Here

The recorded `Mind Rot` simplification is closed. Resume from
`docs/exec-plans/active/002-source-strategy-and-coverage-plan.md`. The next
smallest recorded in-slice rules limitation is attacker-owned damage ordering
for one attacker blocked by multiple creatures.
