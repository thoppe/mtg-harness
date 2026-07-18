# Contract: Costs And X Values

## Guarantee

The caster chooses a nonnegative X while casting. The paid generic component,
chosen X, targets, and controller are stored in the stack entry; resolution
uses that immutable snapshot rather than recalculating X.

## v0+ Scope

- `{X}` contributes exactly the chosen amount to the generic mana requirement.
- A cast fails before entering the stack if its chosen X cannot be paid.
- Existing fixed-cost spells use `chosen_x = 0`.
- Wave 6 reuses this snapshot only for Blaze and Earthquake. Each applies the
  stored X as printed and neither changes the payment model.
- A name-scoped additional sacrifice cost may require the selected controlled
  permanent to be legal immediately before payment and may capture only the
  printed last-known value needed by its spell. Natural Order captures no
  value; Final Strike captures the sacrificed creature's power. This is not a
  general additional-cost or last-known-value framework.

## Deferred

Hybrid/variable alternatives, cost reduction/increase effects, and split
payments require a later cost-model increment.
