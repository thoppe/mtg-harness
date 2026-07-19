# Execution Plan: Wave 7 Trigger-Resolution Choices

## Goal

Replace Wave 7's deterministic first-legal fallbacks with explicit,
chooser-owned and replayable trigger-resolution decisions, without widening
the engine into a general triggered-ability or target-selection framework.

## Scope

This is a rule-correction increment for the already-active Wave 7 cards. It
does not add card source artifacts or promote new cards. The contract remains
name-scoped and deliberately chooses targets only when the trigger resolves.

## Required Stages

1. Extend `PendingDecision` with an explicit option scope (`object` by
   default; `player` only for Ebon Dragon and Ingenious Thief). Keep existing
   decision serialization and replay compatibility intact.
2. On Wave 7 trigger resolution, snapshot legal options and request exactly
   one continuation for each named target, optional action, hidden-zone
   search, or payment. Do not emit `triggered_ability_resolved` until that
   continuation finishes.
3. Resolve the continuation with current zone and object-identity validation.
   A stale target/payment must produce the documented no-effect or unpaid
   sacrifice outcome; it must never act on a new object sharing an instance
   ID.
4. Preserve redaction: public events record decision metadata and counts, not
   unrevealed hand/library identities. Player-target decisions contain only
   player identifiers.
5. Add behavioral tests in `engine/tests/test_wave7_trigger_choices.py` for
   a declined optional effect, a non-first legal choice, mandatory target
   handling, Owl Familiar's post-draw discard, each payment cardinality,
   unavailable payment, stale selections, player targets, Wood Elves search,
   and replay equivalence.
6. Update the Wave 7 contract, rule/card coverage test references, and the
   active-plan resume note in the same verified commit.

## Explicit Card Groups

- Player choices: Ebon Dragon; Ingenious Thief.
- Optional object targets: Gravedigger, Serpent Assassin, Seasoned Marshal.
- Mandatory object targets when legal: Fire Imp, Fire Dragon, Man-o'-War,
  Fire Snake. Wood Elves may choose zero or one qualifying Forest, then
  shuffles.
- Post-draw discard: Owl Familiar discards one chosen hand card if able.
- Pay-or-sacrifice: Mercenary Knight (one creature hand card), Thundering
  Wurm (one land hand card), Plant Elemental (one Forest), Primeval Force
  (three distinct Forests), and Thing from the Deep (one Island).

Pillaging Horde remains a deterministic RNG discard path because its oracle
text does not give its controller a choice.

## Verification

Run the new focused Wave 7 choice tests, the existing Wave 7 identity test,
replay tests, and the full `engine/tests` suite before marking this increment
complete. The recorded limitation in the Wave 7 contract remains active until
all stages pass.

## Resume Here

Implement stages 1--3 as one coherent rule change, beginning with the
`PendingDecision` option scope and continuation dispatcher. Do not mark any
Wave 7 card fully oracle-faithful until the behavioral and replay coverage in
stage 5 is present.
