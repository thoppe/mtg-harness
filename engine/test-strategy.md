# Engine Test Strategy

## Goal

Define what the first engine tests need to prove before implementation begins.

## Initial Test Categories

- fixture-loading tests
  - the active support slice can be loaded from canonical card files and manifest data
- setup tests
  - a legal two-player starting state can be created
- replay-log tests
  - deterministic setup emits the expected append-only event sequence
- action-legality tests
  - only valid actions are offered in a given state
- mana tests
  - each declared basic land can produce its intrinsic color
- spell-casting tests
  - declared creature and noncreature spells can be cast with the required mana
  - each newly introduced spell text family has targeted legality, resolution, and replay-log coverage
- combat tests
  - attackers and blockers can be declared legally
  - combat damage updates state correctly
- state-based tests
  - lethal damage moves a creature to the graveyard

## Test Philosophy

- Prefer explicit scenario tests over heavily abstracted fixtures for the initial slice.
- Each test should mention the rule family or manifest item it proves when practical.
- New cards should not be added without adding or updating tests for any new rule family they require.
