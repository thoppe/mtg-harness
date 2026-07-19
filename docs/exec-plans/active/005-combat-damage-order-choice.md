# Execution Plan: Combat Damage Order Choice

## Goal

Replace the implicit defender-listed damage order with an explicit,
attacker-owned choice when one attacker is blocked by multiple creatures.

## Status

Complete.

## Scope

- Preserve the active `Portal` card manifest without adding cards or source
  artifacts.
- After blockers are declared, suspend combat damage for an ordered choice
  owned by the attacking player.
- Offer exactly the blockers assigned to the single multiply blocked attacker.
- Revalidate blocker object identity and battlefield membership when the choice
  resolves, then store the chosen order as the combat assignment order.
- Preserve the existing lethal-before-next-blocker damage calculation and
  public combat assignment events.
- Add focused choice ownership, enumeration, non-declaration-order assignment,
  stale-object rejection, and replay-event tests.

## Explicit Boundary

This increment covers exactly one attacker blocked by multiple creatures.
Simultaneous ordering choices for multiple multiply blocked attackers remain
deferred.

## Verification

1. Run focused combat and replay tests.
2. Run the full engine test suite.
3. Run the information test suite.
4. Parse the coverage YAML and run `git diff --check`.

## Resume Here

Return to the active source strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve the explicit boundary that simultaneous ordering choices
for multiple multiply blocked attackers remain deferred.
