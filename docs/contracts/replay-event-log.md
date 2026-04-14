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
- `opening_hand_assigned`
- `turn_started`
- `step_changed`
- `priority_passed`
- `land_played`
- `mana_added`
- `spell_cast`
- `object_moved_between_zones`
- `spell_resolved`
- `damage_applied`
- `attackers_declared`
- `blockers_declared`
- `combat_damage_assigned`
- `combat_damage_applied`
- `life_total_changed`
- `state_based_actions_checked`
- `permanent_destroyed`
- `turn_ended`

## Guarantees

- The event log must distinguish player-chosen actions from automatic engine progress.
- Zone changes must be visible as events rather than inferred from unrelated records.
- Replay tests must be able to assert exact event sequences for the initial slice.
- The event vocabulary may grow, but existing event meanings should not drift silently.
- Automatic-destruction events should record the engine reason for that destruction when the current rule family can identify it explicitly.

## v0 Simplifications

- The first slice does not need event families for triggered abilities, replacement effects, or continuous-effect recalculation.
- The first slice may use a single zone-movement event type rather than highly specialized movement events.
- The currently implemented event log covers setup, first-turn step progression, drawing, explicit action windows for precombat main and combat declarations, precombat priority passing through the currently supported forced-pass branch, land play, five-basic-land mana production, simple creature spell resolution, narrow targeted sorcery resolution for `Vengeance`, `Path of Peace`, `Volcanic Hammer`, `Lava Axe`, `Mind Rot`, `Winter's Grasp`, and `Symbol of Unsummoning`, no-target sorcery resolution for `Touch of Brilliance`, `Armageddon`, `Wrath of God`, and `Sacred Nectar`, and minimal combat and spell damage/state-based destruction.
- The current SBA path emits `state_based_actions_checked` even when no permanents are destroyed.
- The current turn-flow implementation also emits `turn_ended` after cleanup.
- The current noncreature-spell implementation may emit repeated `permanent_destroyed` and `object_moved_between_zones` events when one spell destroys multiple permanents, including multi-target and global-destruction effects.

## Expansion Guardrails

- Future effect systems must be able to add event types without invalidating the append-only model.
- Event payloads should use stable object identifiers, not transient memory positions.
- Replay design must allow future insertion of trigger, replacement, and continuous-effect evaluation events.

## Related Contracts

- `docs/contracts/deterministic-game-setup.md`
- `docs/contracts/state-machine-transitions.md`
- `docs/contracts/play-engine.md`
