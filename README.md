# mtg-harness

`mtg-harness` is a planned Python project for simulating Magic: The Gathering game play.

The repository is intentionally starting in a harness-engineering style:

- root files stay short and navigational
- `docs/` is the system of record
- plans and contracts are versioned before implementation

## Current Status

This repository contains a manifest-backed source-ingestion workflow and a deterministic, two-player engine slice for the active `Portal`-led micro-universe. The frozen active roster implements all 200 `Portal` cards plus the explicitly declared ME4 `Rain of Daggers` mass-destruction testbed. A player-safe Rich command-line surface exposes the current legal actions and valid targets during play. The coverage manifests remain the authoritative statement of the exact rules and card boundaries.

## Intended Major Components

- Knowledge ingestion for cards, oracle text, keywords, and rules references
- Core game and rules execution engine
- CLI-facing interaction layer
- Browser-facing API/backend layer for a future viewer/player

## Repository Layout

- `AGENTS.md`: short operating map for agents
- `HUMAN_INPUT.md`: human-owned constraints, decisions, and open questions
- `docs/`: contracts, architecture notes, design docs, references, and execution plans
- `information/`: external-source pull scripts, tests, and pulled source artifacts
- `engine/`: Python package for engine implementation and engine tests
- `.codex/skills/`: repo-local Codex skill definitions for repeatable workflows

## How To Use This Repo Right Now

1. Start with `HUMAN_INPUT.md` for currently fixed constraints and unresolved decisions.
2. Read `docs/index.md` for the knowledge map.
3. Use the active execution plan in `docs/exec-plans/active/` to drive the next changes.

## Demo

Run the current lethal-damage walkthrough with:

```bash
python3 demo.py
```

## Play From The Terminal

Install the package, then start a deterministic two-player Portal deck game:

```bash
mtg-harness --deck-a white.json --deck-b blue.json --seed 31
```

The default terminal surface uses Rich color to show the current turn, public
board, priority player's hand, recent public events, and every currently legal
action. Target and choice prompts offer only candidates returned by the
player-scoped legal-actions API. Use `NO_COLOR=1` when a plain terminal is
preferable.

For compact, deterministic decision points, list and launch the rules-harness
scenarios:

```bash
mtg-harness --list-scenarios
mtg-harness --scenario combat-blockers
```

Scenarios are explicitly rules harnesses rather than constructed deck games.
In particular, `rain-of-daggers-harness` is the scenario-only ME4 testbed and
is never a legal Portal deck.

## Verification

Install the project dependencies, then run both test suites from the repository
root:

```bash
python3 -m pip install .
python3 -m unittest discover -s engine/tests -v
python3 -m unittest discover -s information/tests -v
```

The GitHub Actions workflow runs those same commands on supported Python
versions.

<details>
<summary>Example terminal output</summary>

```text
╭───────────────────────── Board State Before Combat ──────────────────────────╮
│ Turn 7 | Active player: alice | Priority: alice | Step: precombat_main_step  │
╰──────────────────────────────────────────────────────────────────────────────╯
                                Players
┏━━━━━━━━┳━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Player ┃ Life ┃ Mana Pool ┃ Library ┃ Hand ┃ Battlefield ┃ Graveyard ┃
┡━━━━━━━━╇━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ alice  │   20 │ -         │       0 │    0 │           4 │         0 │
│ bob    │   20 │ -         │       0 │    0 │           2 │         0 │
└────────┴──────┴───────────┴─────────┴──────┴─────────────┴───────────┘
╭─────────────────────────────── Combat Script ────────────────────────────────╮
│ 1. Alice advances to combat.                                                 │
│ 2. Alice attacks with Border Guard.                                          │
│ 3. Bob blocks with Muck Rats.                                                │
│ 4. Combat damage resolves and state-based actions are checked.               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭────────────────────────── Board State After Combat ──────────────────────────╮
│ Turn 7 | Active player: alice | Priority: bob | Step: end_combat_step        │
╰──────────────────────────────────────────────────────────────────────────────╯
                                 Recent Events
┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   # ┃ Event                       ┃ Summary                                  ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 136 │ blockers_declared           │ Muck Rats blocks Border Guard            │
│ 138 │ combat_damage_assigned      │ Border Guard assigns 1 to Muck Rats      │
│ 140 │ state_based_actions_checked │ SBA check destroys Muck Rats for lethal  │
│     │                             │ damage (1 >= 1)                          │
│ 141 │ permanent_destroyed         │ Muck Rats is destroyed for lethal damage │
│     │                             │ (1 >= 1)                                 │
│ 142 │ object_moved_between_zones  │ bob:2 moves battlefield -> graveyard     │
└─────┴─────────────────────────────┴──────────────────────────────────────────┘
```

</details>

## Immediate Goal

Maintain and deliberately widen the deterministic Python-first simulation backend without implying support beyond the declared slice or introducing premature UI work.

## Current Engine Surface

- `mtg-harness` presents only the priority player's current legal action
  descriptors and collects target/choice candidates through the same API.
- Named mid-game rules-harness scenarios exercise combat, multi-target spells,
  stack responses, private choices, cleanup, and the isolated Rain testbed.
- Continue frozen-roster hardening through
  `docs/exec-plans/active/028-legal-actions-api-and-long-traces.md`; preserve
  the player-safe terminal and deterministic replay boundaries.
