# Contract: Characteristics And Continuous Effects

## Purpose

Define the bounded characteristics model used by the Portal expansion waves.

## v0+ Guarantees

- Effective power and toughness equal printed values plus explicit temporary
  effect records attached to the current `object_id`.
- Temporary effect records can grant the bounded Wave 2 keywords `Flying`,
  `Reach`, and `Forestwalk`, plus a color-restricted blocking constraint.
- Combat assignment and lethal-damage SBAs use effective characteristics.
- Temporary bonuses expire at cleanup and immediately when their object changes
  zones; they never follow a persistent `card_instance_id` into a new object.
- The initial model supports additive power/toughness bonuses and granted
  keywords only. It is not a general layer system.
- Wave 3's printed static keywords may be read by the shared combat predicates
  for `Islandwalk` and `Vigilance`; the latter changes only whether attacker
  declaration taps that creature. The bounded flying-only blocker restriction
  for Cloud Dragon, Cloud Pirates, and Cloud Spirit is likewise a combat
  predicate, not a continuous-effect layer.

## Expansion Guardrail

Cards needing copy effects, base-setting P/T, dependency/layer ordering, or
arbitrary characteristic-changing effects require a new contract increment.
Triggered abilities and effects that shuffle a library remain outside this
characteristics contract. Alabaster Dragon's name-scoped death trigger is
governed instead by the stack, identity, RNG, and replay contracts; it does
not extend this into a general triggered-ability or layer system.
