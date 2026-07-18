# Contract: Deterministic RNG And Shuffle

## Purpose

Specify deterministic shuffle behavior without making a seed alone a hidden
implementation detail.

## State And Algorithm

- Game state stores `rng_seed`, `rng_cursor`, and the algorithm identifier.
- v0 uses `python_random_mt19937_v1`: seed a fresh `random.Random` with the
  game seed plus cursor, perform one Fisher-Yates shuffle, then increment the
  cursor once.
- The shuffled zone order is persisted in normal zone state; replay uses the
  same algorithm/version and cursor transition.

## Events

- `library_shuffled` records player, algorithm, cursor before/after, and count.
- It does not reveal library order or hidden identities.
- Effects that reveal a selected card emit their separate public reveal event
  before the shuffle event.
- Alabaster Dragon's supported death trigger first moves the captured card
  instance from its owner's graveyard to that owner's library, then performs
  exactly one library shuffle on resolution. If the card is no longer in that
  graveyard, it performs no shuffle and consumes no cursor position.

## Boundaries

- Every shuffle consumes one cursor position, including a tutor that finds no
  matching card.
- Alabaster Dragon consumes one cursor position only for the successful
  graveyard-to-library-and-shuffle resolution above; putting its trigger on the
  stack consumes none.
- No source of randomness may call ambient process RNG.
- Algorithm migrations require a new identifier and replay compatibility path.
