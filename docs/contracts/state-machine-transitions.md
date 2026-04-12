# Contract: State Machine Transitions

## Purpose

Define the minimum legal progression points for the first deterministic engine slice.

## Transition Model

- The engine advances through explicit states, not implicit control flow.
- Each accepted player action or automatic rules step must move the game through one or more named transition points.
- Transition points must be visible in logs and test traces.

## v0 Required Transition Points

- `game_setup`
- `opening_hand_ready`
- `turn_begin`
- `untap_step`
- `upkeep_step`
- `draw_step`
- `precombat_main_step`
- `begin_combat_step`
- `declare_attackers_step`
- `declare_blockers_step`
- `combat_damage_step`
- `end_combat_step`
- `postcombat_main_step`
- `end_step`
- `cleanup_step`
- `priority_window`
- `spell_on_stack`
- `spell_resolving`
- `state_based_actions_check`

## v0 Legal Action Families

- `play_land`
- `activate_mana_ability`
- `cast_creature_spell`
- `pass_priority`
- `declare_attackers`
- `declare_blockers`
- `advance_step`

## Guarantees

- The engine must be able to explain which transition point produced an action opportunity.
- Automatic transitions and player-selected actions must both be logged.
- State-based actions must run at explicit checkpoints rather than as invisible side effects.
- The initial slice may skip unsupported priority branches only if the skipped behavior is documented in the relevant rule-family scope.

## v0 Simplifications

- The first slice may treat many priority windows as forced-pass paths when no legal actions exist beyond the declared micro-universe.
- The first slice may limit stack interactions to creature spells and mana abilities required by `Plains`.
- The first slice may model combat with a single combat-damage checkpoint rather than broader combat variants.
- The currently implemented turn flow reaches cleanup, emits `turn_ended`, and can hand off into the next active player's precombat main.
- Full long-run game-loop completion beyond the supported subset still remains future work.
- The currently implemented combat model supports at most one blocker per attacker.

## Expansion Guardrails

- Do not encode transition names that assume only sorcery-speed gameplay forever.
- Do not merge combat declaration and combat-damage processing into a single opaque step.
- Leave explicit attachment points for future trigger generation, replacement checks, and continuous-effect refresh.

## Related Contracts

- `docs/contracts/play-engine.md`
- `docs/contracts/replay-event-log.md`
