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
- `land_play_allowance_changed`
- `mana_added`
- `spell_cast`
- `object_moved_between_zones`
- `spell_resolved`
- `spell_countered_on_resolution`
- `triggered_ability_put_on_stack`
- `triggered_ability_resolved`
- `activated_ability_activated`
- `activated_ability_resolved`
- `damage_prevented`
- `spell_countered`
- `choice_requested`
- `choice_resolved`
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
- `card_revealed`
- `hand_looked_at`
- `hand_revealed`
- `library_shuffled`
- `random_choice_resolved`
- `delayed_turn_effect_created`
- `extra_turn_scheduled`
- `extra_turn_started`
- `untap_prevented`
- `combat_phase_skipped`
- `combat_requirement_created`

## Guarantees

- The event log must distinguish player-chosen actions from automatic engine progress.
- Zone changes must be visible as events rather than inferred from unrelated records, including `card_instance_id`, `from_object_id`, and `to_object_id`.
- Replay tests must be able to assert exact event sequences for the initial slice.
- The event vocabulary may grow, but existing event meanings should not drift silently.
- Automatic-destruction events should record the engine reason for that destruction when the current rule family can identify it explicitly.

## Event Names And Visibility

- Event names are singular, lower-snake-case facts.  The v0 vocabulary uses
  `card_revealed`, not `cards_revealed`; `combat_phase_skipped`, not
  `combat_skipped`; and `extra_turn_scheduled`, not `extra_turn_queued`.
  Consumers must use the names in the required list rather than infer aliases.
- `choice_requested` always exposes only `decision_id`, `chooser_id`, `kind`,
  and `option_count`.  It must not expose a hidden option ID, a hidden library
  order, or a private continuation payload.
- `choice_resolved` always identifies the decision; its chooser and kind are
  obtained from the matching request (and its active-player context). A
  selection from a nonrevealed hand or library is represented only by its
  public aggregate (`selected_count`, declared count, or yes/no outcome).
  It may identify an individual selected card only when the effect separately
  emits `card_revealed` or the resulting zone change makes that identity public.
- `hand_looked_at` records viewer, viewed player, and count only.  By contrast,
  `hand_revealed` records the hand's card-instance and oracle identities because
  the source text makes those facts public.
- `card_revealed` records the revealed instance, oracle ID, owner/controller
  context when applicable, and a stable reason such as `tutor` or `search`.
  It is the only generic public reveal event; no plural alias exists.
- `library_shuffled` and `random_choice_resolved` record the algorithm
  identifier and cursor transition, plus public counts.  Neither records a
  library order or the pre-random hidden option list.
- Zone movement is authoritative for public card identities after a card leaves
  a hidden zone.  A reveal event is not a substitute for the corresponding
  `object_moved_between_zones` event.

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
- Wave 5 uses `hand_looked_at`, `hand_revealed`, `choice_requested`,
  `choice_resolved`, `card_revealed`, `random_choice_resolved`, and
  `library_shuffled`.  Hidden selection identities remain absent until an
  explicit reveal or a public zone movement.
- Wave 6 uses `delayed_turn_effect_created`, `extra_turn_scheduled`,
  `extra_turn_started`, `untap_prevented`, and `combat_phase_skipped`.  These
  records expose the affected player and declared rule outcome, rather than an
  implicit marker implementation.
- Wave 7 uses `combat_requirement_created` in addition to the trigger,
  activation, counter, and prevention events listed above.

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
