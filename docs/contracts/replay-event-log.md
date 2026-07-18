# Contract: Replay Event Log

## Purpose

Define the minimum append-only event types required for deterministic replay and trace-based tests.

## Event Log Rule

- The replay log is append-only.
- Events describe accepted actions and automatic rules outcomes in execution order.
- Replay must not depend on unlogged hidden mutations.

## Required Event Fields

- `event_id`: stable identifier within a game log
- `game_id`: identifier of the game instance
- `sequence`: strictly increasing integer position
- `event_type`: stable event type name
- `active_player`: player whose turn or action context is active
- `state_ref`: optional pointer or digest for the post-event state snapshot when stored
- `payload`: event-specific structured data

## v0 Required Event Types

- `game_initialized`
- `game_ended`
- `opening_hand_assigned`
- `turn_started`
- `step_changed`
- `priority_passed`
- `land_played`
- `mana_added`
- `spell_cast`
- `object_moved_between_zones`
- `spell_resolved`
- `spell_countered_on_resolution`
- `triggered_ability_put_on_stack`
- `triggered_ability_resolved`
- `trigger_order_requested`
- `activated_ability_activated`
- `activated_ability_resolved`
- `damage_prevented`
- `spell_countered`
- `choice_requested`
- `choice_resolved`
- `cards_revealed`
- `library_prefix_ordered`
- `damage_applied`
- `attackers_declared`
- `blockers_declared`
- `combat_damage_assigned`
- `combat_damage_applied`
- `life_total_changed`
- `permanent_tapped`
- `state_based_actions_checked`
- `permanent_destroyed`
- `turn_ended`
- `extra_turn_queued`
- `combat_skipped`

## Guarantees

- The event log must distinguish player-chosen actions from automatic engine progress.
- Zone changes must be visible as events rather than inferred from unrelated records, including `card_instance_id`, `from_object_id`, and `to_object_id`.
- Replay tests must be able to assert exact event sequences for the initial slice.
- The event vocabulary may grow, but existing event meanings should not drift silently.
- Automatic-destruction events should record the engine reason for that destruction when the current rule family can identify it explicitly.

## v0 Simplifications

- The initial slice provides registered trigger and activated-ability event
  families only for the named Wave 7 cards and Alabaster Dragon. It does not
  otherwise provide arbitrary trigger dispatch, replacement effects, or
  continuous-effect recalculation.
- The first slice may use a single zone-movement event type rather than highly specialized movement events.
- The currently implemented event log covers setup, first-turn step progression, drawing, explicit action windows for precombat main and combat declarations, two-player priority passing for supported spells and Alabaster Dragon's bounded trigger, land play, five-basic-land mana production, simple creature spell resolution, the declared sorcery families, minimal combat and spell damage/state-based destruction, shared combat-legality checks for the supported `Defender`, `Flying`, `Reach`, `Swampwalk`, `Forestwalk`, `Islandwalk`, and `Vigilance` cards, and printed-color target filtering limited to `Hand of Death`'s nonblack-creature restriction. A spell whose only required targets are illegal when it resolves emits `spell_countered_on_resolution` and moves to its graveyard.
- The current SBA path emits `state_based_actions_checked` even when no permanents are destroyed.
- The current turn-flow implementation also emits `turn_ended` after cleanup.
- The current noncreature-spell implementation may emit repeated `permanent_destroyed` and `object_moved_between_zones` events when one spell destroys multiple permanents, including multi-target and global-destruction effects.
- If Alabaster Dragon dies, its `permanent_destroyed` and battlefield-to-
  graveyard zone event precede `triggered_ability_put_on_stack`. A successful
  later resolution emits the graveyard-to-library zone event, `library_shuffled`,
  and `triggered_ability_resolved`; an unsuccessful resolution emits only the
  resolved event with its no-effect outcome. Trigger payloads retain the
  source's last-known object identity and owner.

## Expansion Guardrails

- Future effect systems must be able to add event types without invalidating the append-only model.
- Event payloads should use stable object identifiers, not transient memory positions.
- Replay design must allow future insertion of trigger, replacement, and continuous-effect evaluation events beyond the Alabaster-specific pair.
- Wave 5's decision, reveal, ordering, and RNG-event payload boundaries are
  defined in `docs/contracts/wave5-hidden-zone-expansion.md`; adding them must
  preserve the append-only replay model and must not expose nonrevealed hidden
  options.
- Wave 6 event payloads must preserve declared X, target order and allocation,
  Final Strike's captured sacrificed power, next-turn marker creation and
  consumption, skipped combat, queued extra-turn identity, and Last Chance's
  terminal end-step outcome. They may not infer any of those facts from
  implicit control flow.
- Wave 7 event payloads must preserve source/event snapshots, APNAP ordering,
  activation costs, target choices, expected graveyard identities, countered
  stack-object identity, and prevention/retaliation application without
  exposing nonrevealed hand or library identities.

## Related Contracts

- `docs/contracts/deterministic-game-setup.md`
- `docs/contracts/state-machine-transitions.md`
- `docs/contracts/play-engine.md`
