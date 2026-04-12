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
- Planned trace assertions:
  - `turn_started`
  - `step_changed`
  - `turn_ended`

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
  - `engine/tests/test_turns.py`
  - `engine/tests/test_replay_log.py`
- Planned trace assertions:
  - `spell_cast`
  - `spell_resolved`
  - `object_moved_between_zones`

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
