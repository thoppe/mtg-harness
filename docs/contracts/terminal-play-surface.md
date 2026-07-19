# Contract: Terminal Play Surface

## Purpose

Define a Rich-capable, local two-player terminal surface that makes the
engine's current legal actions understandable without duplicating rules logic
or leaking hidden information.

## Scope

- The v0 surface is an in-process, two-player local game. It is a presentation
  and input adapter over a `GameSession` or legal-deck session, not a second
  game engine.
- The surface supports both legal Portal deck games and explicit rules-harness
  scenarios. A rules-harness scenario must be visibly labeled as such and must
  never be represented as a legal Portal deck game.
- Rich formatting is optional infrastructure: the command must remain usable
  when color is unavailable or explicitly disabled. Formatting must not change
  action availability, action order, or submitted payloads.

## Player-Safe State View

- Every rendered frame has an explicit viewer/player context. The normal
  interactive frame is scoped to the player with priority; an observer view is
  a separate, explicitly requested role and obeys the same redaction rules as
  the legal-actions API.
- A player-safe frame may show public information: turn and step, active and
  priority player, outcome, life totals, mana pools, public zones and their
  ordered public objects, stack, combat assignments, and public counts for
  hidden zones.
- A frame may show only the viewer's own hidden hand identities and only when
  the engine has made that view available. It must not show either library
  order, either player's hidden hand identities to another player, private
  mulligan-bottom identities, or unselected hidden decision options.
- Rendering must consume a role-redacted session/state projection. Terminal
  formatting must not obtain raw hidden state merely to decide which items to
  hide.

## Legal Actions And Parameters

- The action pane lists every descriptor returned by
  `legal_actions(player_id)` for the current player-scoped revision. It may
  group or label descriptors for readability but must neither synthesize an
  action nor omit a returned descriptor.
- The pane must identify the current state revision and the player whose
  actions are being displayed. A submitted choice carries that revision.
- After an action is selected, the terminal collects only its declared
  parameter slots. Target and choice pickers must query `valid_targets` for
  each partial selection and present only returned candidates.
- Multi-target, ordered, allocation, X-value, additional-cost, and boolean
  slots remain explicit interactions. The terminal must not guess a target,
  auto-select a private option, construct an internal action directly, or use
  card-specific presentation code to relax validation.
- A stale or rejected submission displays the structured, player-safe rejection
  and refreshes the state and action panes from the session. It must not retain
  or reveal candidates from the rejected revision.

## Rich Live Presentation

- The live layout must include a concise state header, a player-safe board,
  the current stack/combat context when nonempty, a current legal-action pane,
  and recent event timeline entries.
- Rich color and styling may distinguish players, zones, action families,
  costs, errors, priority, and automatic versus player-chosen events. Color is
  supplemental: labels and text remain sufficient in monochrome output.
- The event timeline derives from the append-only public event stream. It
  renders event type and a player-safe summary in sequence order and must not
  expose private accepted-action payloads as an event convenience.
- Rendering a frame is observational. It must not advance priority, consume a
  choice, shuffle, mutate the event log, or otherwise change game state.

## Scenario Launcher

- The CLI provides a named scenario-launch path in addition to deck-file game
  start. Scenario names resolve to explicit, deterministic setup fixtures;
  arbitrary raw state construction is not exposed as a player command.
- Each scenario declares its category (`legal_deck` or `rules_harness`), seed
  or ordered setup, starting viewer/priority context, and the intended
  interesting decision point. Rules-harness scenarios may use `Rain of
  Daggers`; legal-deck scenarios may not.
- The initial catalog must include mid-game states that exercise at least
  combat-response timing, multiple blockers and damage ordering, stack
  responses/countering, a multi-target or allocation spell, a private
  choice/search, and a turn-effect or cleanup-expiry boundary.
- Scenario start follows the ordinary session, descriptor, validation, event,
  and replay paths. A scenario may not install hand-authored legal actions or
  bypass ordinary action dispatch.

## Replay, Inspection, And Test Evidence

- Interactive commands may save accepted replay input through the existing
  replay boundary. A public terminal timeline is not replay input and must
  retain public-event redaction.
- The surface offers bounded inspection of current public objects, the
  viewer's permitted objects, and recent public events without changing state.
- End-to-end tests must cover each named scenario through descriptor-driven
  input, including visible legal-action completeness, valid-target collection,
  rejection refresh, and no hidden-information leakage.
- Render tests must cover both Rich-capable and no-color/plain output using
  stable semantic snapshots. Snapshots assert required labels and safe content,
  not terminal-width-specific box geometry or ANSI escape sequences.

## Non-Goals

- Networked remote play, authentication, matchmaking, spectators with broader
  privileges, browser UI implementation, sideboards, and match play.
- A free-form terminal command that can mutate engine state outside the
  legal-action descriptor surface.

## Related Contracts

- `legal-actions-and-targets-api.md`
- `surface-api.md`
- `deck-construction-and-game-start.md`
- `replay-event-log.md`
- `replay-reduction.md`
