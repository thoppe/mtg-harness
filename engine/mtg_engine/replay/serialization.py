"""Stable JSON representation for a recorded replay input."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from mtg_engine.replay.reducer import ReplayInput


def replay_input_json(input: ReplayInput) -> str:
    """Encode setup and accepted actions without relying on pickle or repr."""
    return json.dumps(
        {
            "setup": asdict(input.setup),
            "start_first_turn": input.start_first_turn,
            "actions": [
                {"type": type(action).__name__, "payload": asdict(action)}
                for action in input.actions
            ],
        },
        sort_keys=True,
        indent=2,
    ) + "\n"


def write_replay_input(path: str | Path, input: ReplayInput) -> None:
    Path(path).write_text(replay_input_json(input), encoding="utf-8")
