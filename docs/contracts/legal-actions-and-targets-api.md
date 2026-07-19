# Contract: Legal Actions And Targets API

## Purpose

Expose the engine's current legal choices as a player-scoped API without
creating a second action-validation or targeting rules system.

## Guarantees

- A response is bound to a game-state revision and acting player.
- Every returned action descriptor is executable only by its declared player at
  that revision; stale or forged submissions reject without state mutation.
- Target candidates derive from the same engine predicates used by action
  enumeration and transition validation.
- Player and spectator responses reveal only information visible to that role.
  Hidden hand/library identities and private choice options never appear in a
  public action or target response.
- The API supports partial selection so multi-target, ordered, X-value,
  allocation, additional-cost, and chooser-owned decision actions can describe
  their remaining legal parameters.

## v0 Surface

- `legal_actions(player_id)` returns typed action descriptors for the current
  state, including public source identity, required parameter slots, and a
  stable descriptor ID.
- `valid_targets(player_id, action_id, slot, partial_selection)` returns the
  currently legal candidates for that slot plus cardinality/distinctness rules.
- `submit_descriptor(player_id, action_id, parameters, revision)` converts only
  a current descriptor into the existing immutable action model and dispatches
  it through the ordinary transition path.
- Rejection responses distinguish stale revision, wrong player, unknown
  descriptor, malformed parameters, and no-longer-legal action without
  exposing hidden reasons or hidden objects.

## Descriptor-Driven CLI

- The CLI must display player-scoped descriptors, then collect only the slots
  declared by the selected descriptor.
- For every target or choice slot, the CLI must call `valid_targets` with the
  current partial selection and offer only returned candidates.
- Multi-target, ordered-choice, X-value, allocation, additional-cost, and
  boolean slots must be collected explicitly; the CLI must never infer a
  target, choose a hidden option, or submit an internal action directly.
- A rejected or stale descriptor submission refreshes the public action view
  without exposing additional private information.

## Non-Goals

- Stable browser/network JSON compatibility beyond this versioned v0 schema
- A generic parser for arbitrary card text
- Public inspection of hidden choices or private replay input

## Related Contracts

- `surface-api.md`
- `stack-and-priority.md`
- `deterministic-choices-and-hidden-zones.md`
- `replay-reduction.md`
