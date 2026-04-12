# mtg-harness

`mtg-harness` is a planned Python project for simulating Magic: The Gathering game play.

The repository is intentionally starting in a harness-engineering style:

- root files stay short and navigational
- `docs/` is the system of record
- plans and contracts are versioned before implementation

## Current Status

This repository now contains an initial source-ingestion workflow and a narrow engine slice for a small `Portal` micro-universe.

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

Define enough contracts and architecture to begin implementation of a Python-first simulation backend without locking in premature UI work.

## Immediate Next Work

The next concrete work remains engine-facing:

- choose the next text-bearing, non-keyword `Portal` card group
- update the rules envelope and coverage manifests before implementing that next rule family
- extend the engine through simple noncreature spell resolution before moving into broader mechanic families
- keep coverage manifests and contracts aligned with the implemented engine path
- use `.codex/skills/card-source-sync/` whenever the declared source scope under `information/` changes
