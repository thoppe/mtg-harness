# Execution Plan: Multiple Combat Damage Order Choices

## Goal

Extend the existing attacker-owned blocker-order decision to combat where more
than one attacker is blocked by multiple creatures.

## Status

Complete.

## Scope

- Preserve the active `Portal` card manifest without adding cards or source
  artifacts.
- Queue one ordered decision per multiply blocked attacker, in declared-attacker
  order.
- Keep every decision owned by the attacking player and offer exactly the
  blockers assigned to that attacker.
- Complete and validate one decision before requesting the next.
- Preserve blocker object-identity and battlefield revalidation, redacted
  choice events, and public applied combat assignments.
- Add focused tests for queue order, independent selected orders, legal-action
  enumeration, replay events, and combat-damage gating until all decisions
  resolve.

## Explicit Boundary

This increment does not add first strike, double strike, trample, banding,
damage reassignment after a blocker leaves combat, or simultaneous composite
choice UI.

## Verification

1. Run focused combat tests.
2. Run the full engine test suite.
3. Run the information test suite.
4. Parse the coverage YAML and run `git diff --check`.

## Resume Here

Return to the active source strategy plan and select the smallest remaining
recorded in-slice limitation or the smallest manifest-backed `Portal`
increment. Preserve sequential declared-attacker ordering and the per-decision
identity checks.
