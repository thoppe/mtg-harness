# Contract: Costs And X Values

## Guarantee

The caster chooses a nonnegative X while casting. The paid generic component,
chosen X, targets, and controller are stored in the stack entry; resolution
uses that immutable snapshot rather than recalculating X.

## v0+ Scope

- `{X}` contributes exactly the chosen amount to the generic mana requirement.
- A cast fails before entering the stack if its chosen X cannot be paid.
- Existing fixed-cost spells use `chosen_x = 0`.

## Deferred

Hybrid/variable alternatives, cost reduction/increase effects, and split
payments require a later cost-model increment.
