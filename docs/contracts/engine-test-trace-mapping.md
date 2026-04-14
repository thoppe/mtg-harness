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

### `simple_card_draw_sorceries_minimal`

- Planned tests:
  - `engine/tests/test_spells.py`
  - `engine/tests/test_priority.py`
  - `engine/tests/test_turns.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
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
  - `simple_card_draw_sorceries_minimal` now has engine coverage for `Touch of Brilliance`.
  - `targeted_battlefield_to_library_sorceries_minimal` now has engine coverage for `Time Ebb`.
  - `targeted_damage_sorceries_minimal` now has engine coverage for `Volcanic Hammer` and `Lava Axe`.
  - `targeted_discard_sorceries_minimal` now has engine coverage for `Mind Rot`.
  - `targeted_land_destruction_sorceries_minimal` now has engine coverage for `Winter's Grasp`.
  - `fixed_multi_target_land_destruction_sorceries_minimal` now has engine coverage for `Rain of Salt`.
  - `targeted_battlefield_to_hand_sorceries_minimal` now has engine coverage for `Symbol of Unsummoning`.
  - `global_land_destruction_sorceries_minimal` now has engine coverage for `Armageddon`.
  - `global_creature_destruction_sorceries_minimal` now has engine coverage for `Wrath of God`.
  - `opponent_mass_creature_destruction_sorceries_minimal` now has engine coverage for `Rain of Daggers`.
  - `flying_keyword_minimal` now has engine coverage for `Armored Pegasus`, `Wind Drake`, `Bog Imp`, and `Storm Crow`.
  - `defender_keyword_minimal` now has engine coverage for `Wall of Granite`.
  - The current slice now has a real lethal-damage proof via `Border Guard` versus `Muck Rats`, so the earlier synthetic SBA shortcut is no longer needed.
