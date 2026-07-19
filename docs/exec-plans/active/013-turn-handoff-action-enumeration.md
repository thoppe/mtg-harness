# Execution Plan: Turn-Handoff Action Enumeration

## Goal

Close the smallest remaining action-surface gap without widening card, source,
or support-manifest scope: enumerate the already replayable turn handoff at its
only valid transition boundary.

## Scope

- Add `advance_turn` to the contracted legal-action families.
- At `combat_damage_step`, enumerate exactly one `AdvanceTurnAction` owned by
  the active player.
- Reuse the existing `advance_turn` validation and transition implementation.
- Add focused regression coverage inside the accepted-action replay path.
- Align turn-structure coverage, trace mapping, and active resume notes.

## Boundaries

- No card, source artifact, support-slice membership, rules-source, event
  family, or turn-transition changes.
- No arbitrary turn skipping or enumeration outside `combat_damage_step`.
- Pending combat damage-order decisions continue to take precedence over all
  other legal actions.

## Verification

- Focused replay-reducer regression.
- Full engine and information test suites.
- Coverage YAML parse check and `git diff --check`.

## Status

- Phase: complete
