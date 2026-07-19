# Contract: Deck Construction And Game Start

## Purpose

Define the legal-deck boundary for a playable two-player Portal game while
preserving explicit, nonlegal setup as a rules-harness facility.

## Portal Constructed v0 Profile

- A deck contains exactly 60 cards. This is the Portal v0 product profile;
  ordinary Constructed permits 60 or more cards, but exact size keeps this
  first playable surface deterministic and legible.
- A deck contains at most four cards with the same English card name, except
  basic lands, which have no copy limit.
- A deck may contain only deck-eligible identities in the active support
  slice. All Portal identities are eligible; ME4 `Rain of Daggers` is an
  engine testbed and is not deck eligible.
- Each player starts at 20 life, draws seven cards, and the starting player
  skips that player's first draw step.
- London mulligans apply: each player may repeatedly shuffle and draw seven;
  after keeping, that player privately chooses a number of cards equal to that
  player's mulligan count to put on the bottom in an ordered sequence.
- Sideboards, matches, and between-game card exchange are out of scope in v0.
  A future profile may add them without changing a deck's main-deck identity.

The copy-limit and basic-land rules follow Comprehensive Rules 100.2a; the
mulligan and first-draw behavior follow rules 103.4–103.5 and 103.8a. The
current official-source provenance must be refreshed before widening this
profile.

## Domain Boundaries

- `DeckList` is a persistent ordered multiset of oracle identities; it has no
  game-object identifiers.
- `DeckProfile` declares legal main-deck rules and explicitly records that
  sideboards are unsupported.
- Deck validation happens before shuffling, opening-hand draw, or game-object
  creation.
- A legal game start expands validated deck entries, deterministically shuffles
  each deck in player order, records public shuffle events, and creates game
  objects only from the resulting library order.
- The existing explicit `SetupInput` remains a rules-harness path. It may use
  tiny ordered libraries and scenario-only cards, but it must not be presented
  as a legal Portal deck game.

## Replay And Privacy

- Seed, profile key, deck identities, shuffle cursor use, mulligan decisions,
  and accepted actions are private replay inputs.
- Public events may record counts, decisions, and shuffle occurrence, but not
  private deck order, opening-hand identity, mulligan-bottom identity, or
  unselected hidden options.

## Related Contracts

- `deterministic-game-setup.md`
- `deterministic-rng-and-shuffle.md`
- `replay-event-log.md`
- `replay-reduction.md`
- `surface-api.md`
