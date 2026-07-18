# Contract: Object Identity And Zone Changes

## Purpose

Separate the persistent card represented by a deck entry from the game object that
currently represents it in a zone. This prevents battlefield state from leaking
through zone changes while retaining deterministic traceability.

## Required Identifiers

- `card_instance_id` identifies the persistent deck/card instance for setup,
  ownership, hidden-zone ordering, and source provenance.
- `object_id` identifies one game-object incarnation of that card instance.
- `zone_change_counter` is monotonically increasing for each card instance and
  is part of a game object's stable identity.

## Zone-Change Rule

- Moving a card from one zone to another creates a new game object, except where
  a future explicit rule contract defines an exception.
- A new object retains the card instance's owner and oracle identity, but it does
  not retain battlefield-only state such as tapped status, marked damage,
  summoning/entered-turn data, combat participation, attachments, or temporary
  effects.
- A card entering the battlefield is untapped unless the resolving effect says
  otherwise, and receives a new `entered_battlefield_turn` value.
- Events must identify the moved card instance and include the pre- and
  post-change object identities when an object changes zone.
- Alabaster Dragon's bounded death trigger uses last-known information from the
  battlefield object that died. Its trigger entry must retain that old
  `object_id`, card instance, and owner rather than treating the newly-created
  graveyard object as the trigger source.

## v0 Migration

- The initial implementation may retain `instance_id` as its public object key
  while it introduces the explicit counter and reset behavior. This is a
  compatibility bridge, not the long-term identity model.
- Any effect that moves a permanent in the active slice must be regression-tested
  for the state reset required by this contract.

## Related Contracts

- `docs/contracts/game-state.md`
- `docs/contracts/replay-event-log.md`
- `docs/contracts/stack-and-priority.md`
