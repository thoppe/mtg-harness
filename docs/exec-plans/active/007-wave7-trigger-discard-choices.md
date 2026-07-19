# Execution Plan: Wave 7 Trigger Discard Choices

## Goal

Replace the remaining hand-order discard shortcuts in Ebon Dragon and Noxious
Toad trigger resolution with explicit affected-player choices.

## Scope

- Preserve Ebon Dragon's optional controller-owned opponent selection.
- If an opponent is selected and has cards in hand, queue a second decision
  owned by that opponent for exactly one snapshotted hand object.
- When Noxious Toad's dies trigger resolves, queue the same exact-one decision
  for its opponent when that player has cards in hand.
- Revalidate hand zone and object identity before applying either discard.
- Redact the selected hidden object from `choice_resolved`; the subsequent
  public hand-to-graveyard event exposes the discarded card normally.
- Do not widen card, source, trigger, multiplayer, or discard-effect scope.

## Verification

- Add focused non-first-choice, empty-hand, ownership, legal-action, and replay
  event tests.
- Run the focused Wave 7 trigger-choice tests, the complete engine suite, and
  the information suite.
- Parse all coverage YAML and run `git diff --check`.

## Resume Here

After this correction is complete, resume from
`docs/exec-plans/active/002-source-strategy-and-coverage-plan.md` and select the
smallest remaining recorded in-slice limitation or manifest-backed `Portal`
increment.
