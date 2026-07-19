# Engine Test Strategy

## Goal

Define the evidence required to maintain the frozen Portal-led engine slice.

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

## Adversarial Hardening Phase

The roster is frozen while engine confidence is improved. Add scenario tests
that intentionally combine supported behavior at its boundaries rather than
adding cards to create new coverage.

- legal-action closure
  - enumerate every legal action at each supported priority and decision
    window; reject near-miss actions without mutating state or consuming RNG
- resolution invalidation
  - remove or move targets, sources, and chosen objects between declaration
    and resolution; assert the documented all- or partial-resolution outcome
- choice and hidden-information isolation
  - replay every chooser-owned continuation, assert object revalidation, and
    ensure public events do not reveal private hand or library identities
- deterministic replay
  - reduce full traces for multi-step turns, nested choices, shuffle/search,
    combat, triggers, extra turns, and cleanup; assert state and event-log
    equivalence to the live execution
- state invariants
  - assert zone uniqueness, owner/controller preservation, stack/priority
    consistency, mana and turn-marker expiry, and state-based-action
    idempotence after every relevant transition
- metamorphic scenarios
  - vary independent library order, legal target order, and equivalent action
    encodings; assert only the documented deterministic differences occur

## Test Philosophy

- Prefer explicit scenario tests over heavily abstracted fixtures for the initial slice.
- Each test should mention the rule family or manifest item it proves when practical.
- New cards should not be added without adding or updating tests for any new rule family they require.
- During the hardening phase, every discovered edge case should first become a
  minimal failing scenario with state and event-trace assertions.
