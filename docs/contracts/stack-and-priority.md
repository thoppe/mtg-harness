# Contract: Stack And Priority

## Purpose

Define the minimum stack lifecycle needed for rules-faithful, deterministic spell
resolution, plus the one bounded triggered ability required by Alabaster Dragon.

## Required Lifecycle

1. A legal cast pays costs, records declared targets, and moves the spell to the
   stack.
2. The casting player receives priority after casting; priority then passes in
   turn order.
3. When every player passes with a nonempty stack, the top object resolves.
4. When every player passes with an empty stack, the current step may advance.
5. When Alabaster Dragon (`2392a41a-59d3-4749-be94-4d9df0af9c4c`) dies, its
   death trigger is created and put onto the stack after the destruction or
   state-based-action operation completes. It is a stack entry, not a card
   moved to the stack.
6. That entry resolves through the same two-player priority cycle as a spell.

## Current Scope

- Two players only.
- Creature spells and the declared name-scoped sorcery implementations may use
  this lifecycle.
- Mana abilities resolve outside the stack.
- The declared attackers step opens a priority window when an instant is
  available. The current narrow instant predicate is Treetop Defense: only
  its controller, after being attacked in that combat, may cast it there.
- If combat damage creates an Alabaster trigger, combat remains in the combat-
  damage priority window until that trigger resolves and both players pass on
  an empty stack; cleanup cannot bypass that stack entry.
- Both players' pass actions and the automatic resolution transition are
  visible in the event log.
- Target legality is rechecked at resolution. A spell whose required targets are
  all illegal on resolution emits `spell_countered_on_resolution`, does not
  apply its effect, and moves to its normal destination.
- The Alabaster entry captures its source controller, owner, last-known
  battlefield identity, and the newly created graveyard identity. On resolution
  it shuffles that card instance into its owner's library only if that same
  graveyard object still exists; otherwise the entry resolves with no shuffle
  effect.

## State Requirements

- A stack entry must preserve the spell card instance, controller, paid costs,
  and chosen targets independently from later state changes.
- The bounded Alabaster trigger entry must additionally preserve its kind,
  source controller, source `object_id`, source `card_instance_id`, owner, and
  expected graveyard `object_id` independently from the death zone change.
- Priority state must record enough information to determine whether all players
  have passed consecutively since the last stack-changing action.
- In the two-player v0 slice, the caster's pass gives priority to the opponent;
  the opponent's following pass resolves the top stack entry and returns
  priority to the active player.

## Non-Goals

- Activated nonmana abilities, triggered abilities other than Alabaster
  Dragon's name-scoped death trigger, copies, split second, and multiplayer
  priority ordering remain separate increments.

## Related Contracts

- `docs/contracts/state-machine-transitions.md`
- `docs/contracts/replay-event-log.md`
- `docs/contracts/object-identity-and-zone-changes.md`
