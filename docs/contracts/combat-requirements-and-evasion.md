# Contract: Combat Requirements And Evasion

## Purpose

Keep combat action enumeration and submitted declarations subject to the same
evasion and requirement rules.

## Required v0+ Rules

- A creature without haste cannot attack during the turn it entered its
  controller's battlefield; haste is an explicit exception.
- Generic landwalk checks the defending player's battlefield for the named land
  subtype and prevents blocks when present.
- The supported landwalk mapping is explicit: `Swampwalk` -> `Swamp`,
  `Forestwalk` -> `Forest`, `Islandwalk` -> `Island`, and `Mountainwalk` ->
  `Mountain`. It does not model land-type-changing effects or arbitrary
  landwalk names.
- A creature with Flying may be subject to the bounded static restriction
  “can block only creatures with flying.” This restriction applies to Cloud
  Dragon, Cloud Pirates, and Cloud Spirit through one shared predicate, and
  applies in both legal-action enumeration and submitted blocker validation.
- A creature with Vigilance does not tap when declared as an attacker. It
  remains eligible to block if otherwise legal later in that combat.
- A requirement such as “all creatures able to block target creature do so” is
  represented in combat state, considered by legal-action enumeration, and
  revalidated on submitted blockers.

## Guardrail

Do not implement a card with a combat requirement by mutating one caller's
legal-action list only; submitted actions must reject the same illegal result.

## Wave 3--4 Boundary

The rules above are the complete combat scope for Waves 3--4. Wave 3E adds
only Alabaster Dragon's separate, name-scoped death trigger; it does not widen
combat handling, shuffle behavior generally, or static-ability support. Wave 4
adds `Mountainwalk` only for Mountain Goat and applies the already-required
haste exception only to Raging Cougar, Raging Goblin, Raging Minotaur, and
Volcanic Dragon.
Those additions do not create arbitrary landwalk handling, a general
summoning-sickness framework beyond combat legality, or triggered/static
ability support.
