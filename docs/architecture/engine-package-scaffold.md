# Engine Package Scaffold

## Purpose

Define the first package-level layout the repository should create once engine scaffolding begins.

## v0 Package Plan

- `engine/__init__.py`
- `engine/state/__init__.py`
- `engine/state/models.py`
- `engine/state/zones.py`
- `engine/state/identifiers.py`
- `engine/actions/__init__.py`
- `engine/actions/models.py`
- `engine/actions/validation.py`
- `engine/flow/__init__.py`
- `engine/flow/setup.py`
- `engine/flow/turns.py`
- `engine/flow/priority.py`
- `engine/events/__init__.py`
- `engine/events/models.py`
- `engine/events/log.py`
- `engine/rules/__init__.py`
- `engine/rules/state_based_actions.py`
- `engine/rules/combat.py`
- `engine/rules/spells.py`
- `engine/output/__init__.py`
- `engine/output/terminal.py`
- `engine/tests/test_setup.py`
- `engine/tests/test_turns.py`
- `engine/tests/test_combat.py`
- `engine/tests/test_replay_log.py`

## Package Responsibilities

### `engine/state`

- Hold authoritative runtime state structures.
- Keep stable identifiers for players, cards, permanents, and stack objects.
- Represent zones and zone movement without embedding rules decisions.

### `engine/actions`

- Define the player-action vocabulary for the current slice.
- Validate action shape before deeper rules evaluation.
- Avoid direct game-state mutation.

### `engine/flow`

- Build initial states from deterministic setup inputs.
- Drive named turn and step transitions.
- Orchestrate priority windows and action application order.

### `engine/events`

- Define append-only replay event types.
- Append events in execution order.
- Support deterministic trace assertions in tests.

### `engine/rules`

- Apply rules-specific logic invoked by flow control.
- Host state-based action checks for lethal damage in v0.
- Host minimal combat and spell-resolution logic for the active support slice.

### `engine/output`

- Hold terminal-facing formatting helpers for inspection and demo workflows.
- Render engine state and event traces without owning simulation rules or legality.
- Stay optional for callers so engine behavior remains usable without Rich output.

## Initial Import Rule

- `engine/flow` may depend on `state`, `actions`, `events`, and `rules`.
- `engine/rules` may depend on `state` and `events`.
- `engine/state` must not depend on `flow` or `rules`.
- `engine/events` must not own legality decisions.

## Test Layout Rule

- Each v0 package area should have at least one directly corresponding test module.
- Replay-log assertions should live in dedicated tests rather than being incidental side effects of state tests.
- Combat tests should assert both resulting state and emitted event traces.

## Expansion Guardrails

- Future continuous-effect or trigger packages may be added under `engine/rules/` without restructuring the current package roots.
- If the engine later needs a service layer, it should wrap these packages rather than collapse them.

## Next Session Focus

- Add `engine/flow/priority.py`.
- Add tests that prove action availability at `precombat_main_step`.
- Prefer replacing test-only state shortcuts with normal engine progression before widening the supported rule surface.
