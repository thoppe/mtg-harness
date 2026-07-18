# Contract: Wave 5 Hidden-Zone Expansion

## Purpose

Define the minimum replayable decision and information model for the
dependency-ordered Portal Wave 5 cards. This contract applies only to the
named oracle IDs recorded by the coverage manifest when those cards are
promoted together with implementation and tests.

## Decision Records

- A pending decision may carry one selected ID, a selected-ID tuple, an
  ordered-ID tuple, a nonnegative declared count, or a yes/no value, according
  to its declared name-scoped kind.
- Legal option IDs are snapshot candidates, but every submitted selection and
  ordering is revalidated against the current state before it is applied.
- A multi-player resolution stores a continuation and installs exactly one
  chooser-owned decision at a time. Its affected players choose in active-
  player then nonactive-player order; no priority or unrelated action occurs
  between those choices.
- An explicit empty selection is valid only where the card says "up to" or
  "any number." A required selection uses all available legal candidates when
  fewer than the stated count exist.

## Visibility And Events

- Looking at a library prefix or a nonrevealed hand gives identities only to
  the specified chooser. Its public request/resolution events report stable
  decision IDs and counts, never the option list or order.
- `reveals their hand` and `reveal` emit a distinct public reveal event with
  the identities the oracle text exposes. They do not create persistent
  visibility after resolution.
- Cards moved from a hand to a graveyard use the ordinary public zone-movement
  event. Randomness need not disclose an option list; the resulting discarded
  object is visible through that zone change.
- A top-of-library ordering event records its decision ID and count but not
  identities or order unless the source text explicitly reveals them.

## Deterministic Randomness

- Mind Knives selects uniformly from the target opponent's current hand using
  the versioned RNG algorithm and advances the cursor once only when that hand
  is nonempty.
- Each instructed library shuffle uses the existing versioned shuffle and
  advances the cursor once, including a shuffle after an empty successful
  search and Winds of Change's empty-hand shuffle.
- When one spell shuffles multiple libraries, resolve and log them in
  active-player then nonactive-player order.

## Name-Scoped Boundaries

- The search predicates are exactly: Plains card (Gift of Estates), Forest
  card (Nature's Lore), basic land card (Untamed Wilds), any card (Cruel
  Tutor), and green creature card (Natural Order).
- The prefix operations are exactly top seven/select two (Ancestral Memories),
  top three/reorder/optional shuffle (Omen), and target opponent top
  five/select one to graveyard/order remainder (Cruel Fate).
- Natural Order's green-creature sacrifice is a casting cost, not a resolution
  choice. If no legal controlled green creature exists, casting is illegal.
- Prosperity's X is an explicit nonnegative declaration at casting. It has no
  implicit default and may not be reused as a general X-cost facility without
  a new contract.

## Replay Guarantee

The action log contains every player declaration and accepted decision. The
event log contains the resulting automatic zone changes, reveal boundaries,
life changes, deterministic RNG cursor transitions, and terminal outcomes.
Replaying setup plus actions reproduces hidden-zone order without depending on
ambient randomness or UI-local state.
