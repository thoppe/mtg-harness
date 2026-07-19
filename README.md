# mtg-harness

`mtg-harness` is a planned Python project for simulating Magic: The Gathering game play.

The repository is intentionally starting in a harness-engineering style:

- root files stay short and navigational
- `docs/` is the system of record
- plans and contracts are versioned before implementation

## Current Status

This repository contains a manifest-backed source-ingestion workflow and a deterministic, two-player engine slice for the active `Portal`-led micro-universe. The active slice implements 201 cards across the completed Portal Waves 1–7, including one explicitly sourced ME4 card; the coverage manifests remain the authoritative statement of its exact boundaries.

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

## Immediate Next Work

The next concrete work is to select and stage the smallest new manifest-backed increment:

- keep the active support-slice manifest, rules envelope, source scope, and coverage manifests aligned before implementing each card increment
- choose the smallest remaining Portal limitation or a new bounded Portal card/rule increment; do not infer support from source artifacts alone
- preserve the completed Waves 1–7 boundaries unless a new contract explicitly widens them
- use `.codex/skills/card-source-sync/` whenever the declared source scope under `information/` changes
