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
- `triggered_ability_on_stack`
- `spell_resolving`
- `state_based_actions_check`
- `extra_turn_queued`
- `combat_skipped`

## v0 Legal Action Families

- `play_land`
- `activate_mana_ability`
- `cast_creature_spell`
- `cast_noncreature_spell`
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

- The first slice currently enumerates `precombat_main_step`, `declare_attackers_step`, and `declare_blockers_step` actions for the currently relevant player. While the stack is nonempty, the sole legal v0 action is for the current priority player to pass; two consecutive passes resolve its top entry.
- The first slice may limit stack interactions to creature spells, a narrow sorcery-speed noncreature spell path, and mana abilities required by the declared five basic lands.
- The only triggered stack interaction in the slice is Alabaster Dragon's
  name-scoped death trigger, created after the destruction or state-based-
  action operation in which it dies and resolved through the normal priority
  cycle. A combat-damage death keeps the combat-damage priority window open
  until the stack clears.
- The first slice may model combat with a single combat-damage checkpoint rather than broader combat variants.
- The currently implemented turn flow reaches cleanup, emits `turn_ended`, and can hand off into the next active player's precombat main.
- Full long-run game-loop completion beyond the supported subset still remains future work.
- When exactly one attacker is blocked by multiple creatures, blocker
  declaration queues an ordered, attacking-player-owned decision before combat
  damage. The decision offers every blocker assigned to that attacker exactly
  once, revalidates each blocker's object identity and battlefield membership,
  and stores the selected order as the combat-damage assignment order.
- Simultaneous ordering choices for multiple multiply blocked attackers remain
  outside the current combat model.
- The targeted-discard slice resolves `Mind Rot` through an explicit
  target-player-owned decision for exactly the lesser of two cards or that
  player's hand size.
- Wave 6 may consume a name-scoped next-untap marker during `untap_step`, skip
  all combat transition points through a `combat_skipped` transition, or apply
  a name-scoped forced-attack requirement during `declare_attackers_step`.
  Last Chance alone may enqueue an immediate next extra turn and end the game
  at the beginning of that queued turn's `end_step`.

## Expansion Guardrails

- Do not encode transition names that assume only sorcery-speed gameplay forever.
- Do not merge combat declaration and combat-damage processing into a single opaque step.
- Leave explicit attachment points for future trigger generation, replacement checks, and continuous-effect refresh.

## Related Contracts

- `docs/contracts/play-engine.md`
- `docs/contracts/replay-event-log.md`
