# Contract: Characteristics And Continuous Effects

## Purpose

Define the bounded characteristics model used by the Portal expansion waves.

## v0+ Guarantees

- Effective power and toughness equal printed values plus explicit temporary
  bonuses attached to the current `object_id`.
- Combat assignment and lethal-damage SBAs use effective characteristics.
- Temporary bonuses expire at cleanup and immediately when their object changes
  zones; they never follow a persistent `card_instance_id` into a new object.
- The initial model supports additive power/toughness bonuses and granted
  keywords only. It is not a general layer system.

## Expansion Guardrail

Cards needing copy effects, base-setting P/T, dependency/layer ordering, or
arbitrary characteristic-changing effects require a new contract increment.
