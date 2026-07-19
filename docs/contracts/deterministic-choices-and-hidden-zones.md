# Contract: Deterministic Choices And Hidden Zones

## Purpose

Define the explicit, replayable decision boundary needed for library search,
selection, ordering, and other effects whose legal options are not public.

## State

- A resolving effect may install exactly one `pending_decision` in game state.
- A pending decision records a stable `decision_id`, chooser, kind, source
  object ID, legal option instance IDs, and continuation payload. Its kind and
  the effect contract determine the visibility boundary; it is part of
  replayable state, not a UI-only prompt.
- While a decision is pending, only its chooser may submit the matching choice
  action; unrelated game actions are not legal.

## Hidden-Zone Rules

- Legal options from a library are visible to the chooser only.
- Public events may identify the selected card only when the effect says to
  reveal it. They must never expose the complete searched library.
- A choice is validated against the current pending decision and rejects an
  option that has changed zones or no longer satisfies the recorded predicate.

## v0 Tutor Scope

- `Personal Tutor` and `Sylvan Tutor` select exactly one matching card from
  the caster's library, reveal the chosen card, shuffle that library, then put
  the selected card on top.
- The selected card is fixed by the choice action before shuffle. A tutor with
  no matching card accepts an explicit no-selection decision and still shuffles.

## Wave 5 Extension Boundary

- The Wave 5 decision kinds, visibility rules, ordered continuations, and
  card-specific search/prefix bounds are defined in
  `docs/contracts/wave5-hidden-zone-expansion.md`.
- Those additions remain name-scoped. They do not make every library, hand,
  modal, multiple-choice, or ordering effect legal.

## Mind Rot Public-Hand Choice

- `Mind Rot` snapshots the targeted player's hand on resolution and installs a
  chooser-owned decision for exactly the lesser of two cards or the number of
  cards in that hand.
- The target player, not the spell's controller, chooses the distinct cards.
  The chosen cards remain public when moved from hand to graveyard.
- This name-scoped continuation reuses the existing public-hand selection
  boundary; it does not introduce general discard-effect parsing.

## Replay Guarantees

- Accepted choice actions carry the decision ID and the complete private
  selection needed by the reducer. Resulting public choice events carry the
  decision ID but redact selected hidden instance IDs unless the effect reveals
  them or makes them public through a zone change. The reducer can reproduce
  the transition from setup, action log, and deterministic RNG state.
- A decision is consumed exactly once; it cannot be re-applied after resolution
  or zone movement.
