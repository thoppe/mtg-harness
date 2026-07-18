# Contract: Engine Test And Trace Mapping

## Purpose

Define how the current rule-family coverage should map to future engine tests and replay-trace assertions.

## Mapping Rules

- Every `implemented` rule family must name at least one engine test file.
- Replay-sensitive rule families must also name an expected event-trace surface.
- Tests should assert both state outcomes and the relevant event sequence when deterministic replay is part of the contract.

## Initial Rule-Family Mapping

### `game_setup_minimal`

- Planned tests:
  - `engine/tests/test_setup.py`
- Planned trace assertions:
  - `game_initialized`
  - `opening_hand_assigned`

### `turn_structure_minimal`

- Planned tests:
  - `engine/tests/test_turns.py`
  - `engine/tests/test_spells.py`
- Planned trace assertions:
  - `turn_started`
  - `step_changed`
  - `object_moved_between_zones`
  - `turn_ended`

### `precombat_priority_minimal`

- Planned tests:
  - `engine/tests/test_priority.py`
  - `engine/tests/test_turns.py`
  - `engine/tests/test_spells.py`
- Planned trace assertions:
  - `priority_passed`
  - `step_changed`

### `combat_action_windows_minimal`

- Planned tests:
  - `engine/tests/test_priority.py`
  - `engine/tests/test_combat.py`
- Planned trace assertions:
  - `attackers_declared`
  - `blockers_declared`
  - `step_changed`

### `instant_priority_minimal`

- Planned tests:
  - `engine/tests/test_wave2.py`
  - `engine/tests/test_priority.py`
- Planned trace assertions:
  - `spell_cast`
  - `priority_passed`
  - `spell_resolved`
  - `step_changed`

### `temporary_characteristics_minimal`

- Planned tests:
  - `engine/tests/test_wave2.py`
  - `engine/tests/test_portal_expansion_wave.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `object_moved_between_zones`

### `combat_restrictions_minimal`

- Planned tests:
  - `engine/tests/test_wave2.py`
  - `engine/tests/test_portal_expansion_wave.py`
  - `engine/tests/test_priority.py`
- Planned trace assertions:
  - `attackers_declared`
  - `blockers_declared`

### `land_playing_minimal`

- Planned tests:
  - `engine/tests/test_turns.py`
- Planned trace assertions:
  - `land_played`
  - `object_moved_between_zones`

### `mana_generation_basic`

- Planned tests:
  - `engine/tests/test_turns.py`
- Planned trace assertions:
  - `mana_added`

### `creature_spells_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_combat.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `object_moved_between_zones`

### `targeted_sorcery_spells_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `object_moved_between_zones`
  - `permanent_destroyed`
  - `life_total_changed`

### `color_restricted_creature_destruction_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `object_moved_between_zones`
  - `permanent_destroyed`

### `simple_card_draw_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_turns.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `object_moved_between_zones`

### `simple_life_gain_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `life_total_changed`
  - `object_moved_between_zones`

### `targeted_battlefield_to_library_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `object_moved_between_zones`

### `targeted_damage_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `damage_applied`
  - `life_total_changed`
  - `state_based_actions_checked`
  - `permanent_destroyed`
  - `object_moved_between_zones`

### `targeted_discard_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `object_moved_between_zones`

### `targeted_land_destruction_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `permanent_destroyed`
  - `object_moved_between_zones`

### `targeted_battlefield_to_hand_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `object_moved_between_zones`

### `targeted_creature_tapping_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `permanent_tapped`
  - `object_moved_between_zones`

### `fixed_multi_target_land_destruction_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `permanent_destroyed`
  - `object_moved_between_zones`

### `global_land_destruction_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `permanent_destroyed`
  - `object_moved_between_zones`

### `opponent_mass_creature_destruction_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `permanent_destroyed`
  - `object_moved_between_zones`
  - `life_total_changed`

### `global_creature_destruction_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `permanent_destroyed`
  - `object_moved_between_zones`

### `flying_keyword_minimal`

- Planned tests:
  - `engine/tests/test_combat.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_spells.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `attackers_declared`
  - `blockers_declared`

### `reach_keyword_minimal`

- Planned tests:
  - `engine/tests/test_combat.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_spells.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `blockers_declared`

### `swampwalk_keyword_minimal`

- Planned tests:
  - `engine/tests/test_combat.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_spells.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `attackers_declared`
  - `blockers_declared`

### `islandwalk_keyword_minimal`

- Planned tests:
  - `engine/tests/test_combat.py`
  - `engine/tests/test_wave3.py`
- Planned trace assertions:
  - `attackers_declared`
  - `blockers_declared`

### `vigilance_keyword_minimal`

- Planned tests:
  - `engine/tests/test_combat.py`
  - `engine/tests/test_wave3.py`
- Planned trace assertions:
  - `attackers_declared`
  - `blockers_declared`

### `flying_only_blocker_restriction_minimal`

- Planned tests:
  - `engine/tests/test_combat.py`
  - `engine/tests/test_wave3.py`
- Planned trace assertions:
  - `attackers_declared`
  - `blockers_declared`

### `alabaster_dragon_death_trigger_minimal`

- Planned tests:
  - `engine/tests/test_wave3.py`
- Planned trace assertions:
  - `state_based_actions_checked`
  - `permanent_destroyed`
  - `object_moved_between_zones`
  - `triggered_ability_put_on_stack`
  - `priority_passed`
  - `library_shuffled`
  - `triggered_ability_resolved`

### `defender_keyword_minimal`

- Planned tests:
  - `engine/tests/test_priority.py`
  - `engine/tests/test_combat.py`
  - `engine/tests/test_spells.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `attackers_declared`

### `combat_minimal`

- Planned tests:
  - `engine/tests/test_combat.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `attackers_declared`
  - `blockers_declared`
  - `combat_damage_assigned`
  - `combat_damage_applied`

### `zones_minimal`

- Planned tests:
  - `engine/tests/test_setup.py`
  - `engine/tests/test_turns.py`
- Planned trace assertions:
  - `object_moved_between_zones`

### `state_based_actions_minimal`

- Planned tests:
  - `engine/tests/test_combat.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `state_based_actions_checked`
  - `permanent_destroyed`
  - `life_total_changed`

## Initial Status Rule

- Until engine code exists, these mappings are planning declarations rather than implementation claims.
- When a rule family becomes `implemented`, this contract and the coverage manifest must agree on the named tests.
- Current implementation note:
  - `game_setup_minimal`, `turn_structure_minimal`, `precombat_priority_minimal`, `combat_action_windows_minimal`, `land_playing_minimal`, `mana_generation_basic`, `creature_spells_minimal`, `combat_minimal`, and `state_based_actions_minimal` now have engine coverage.
  - `targeted_sorcery_spells_minimal` now has engine coverage for `Vengeance` and `Path of Peace`.
  - `color_restricted_creature_destruction_sorceries_minimal` now has engine coverage for `Hand of Death`.
  - `simple_card_draw_sorceries_minimal` now has engine coverage for `Touch of Brilliance`.
  - `targeted_battlefield_to_library_sorceries_minimal` now has engine coverage for `Time Ebb`.
  - `targeted_damage_sorceries_minimal` now has engine coverage for `Volcanic Hammer` and `Lava Axe`.
  - `targeted_discard_sorceries_minimal` now has engine coverage for `Mind Rot`.
  - `targeted_land_destruction_sorceries_minimal` now has engine coverage for `Winter's Grasp`.
  - `fixed_multi_target_land_destruction_sorceries_minimal` now has engine coverage for `Rain of Salt`.
  - `targeted_battlefield_to_hand_sorceries_minimal` now has engine coverage for `Symbol of Unsummoning`.
  - `targeted_creature_tapping_sorceries_minimal` now has engine coverage for `Tidal Surge`.
  - `global_land_destruction_sorceries_minimal` now has engine coverage for `Armageddon`.
  - `global_creature_destruction_sorceries_minimal` now has engine coverage for `Wrath of God`.
  - `opponent_mass_creature_destruction_sorceries_minimal` now has engine coverage for `Rain of Daggers`.
  - `flying_keyword_minimal` now has engine coverage for `Armored Pegasus`, `Wind Drake`, `Bog Imp`, and `Storm Crow`.
  - `reach_keyword_minimal` now has engine coverage for `Keen-Eyed Archers`.
  - `swampwalk_keyword_minimal` now has engine coverage for `Anaconda`.
  - `islandwalk_keyword_minimal`, `vigilance_keyword_minimal`, and
    `flying_only_blocker_restriction_minimal` now have focused Wave 3 engine
    coverage in `engine/tests/test_wave3.py`.
  - `alabaster_dragon_death_trigger_minimal` has focused Wave 3 coverage for
    stack creation, successful deterministic shuffle, and no-effect resolution
    after the Dragon leaves its graveyard.
  - `defender_keyword_minimal` now has engine coverage for `Wall of Granite`.
  - `simple_life_gain_sorceries_minimal` now has engine coverage for `Sacred Nectar`.
  - `instant_priority_minimal`, `temporary_characteristics_minimal`, and
    `combat_restrictions_minimal` now have focused Wave 2 engine coverage,
    including targeted action enumeration and Valorous Charge's
    all-battlefields white-creature modifier.
  - The current slice now has a real lethal-damage proof via `Border Guard` versus `Muck Rats`, so the earlier synthetic SBA shortcut is no longer needed.
