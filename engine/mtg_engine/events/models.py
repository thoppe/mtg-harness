from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameEvent:
    event_id: str
    game_id: str
    sequence: int
    event_type: str
    active_player: str
    payload: dict
    state_ref: str | None = None
