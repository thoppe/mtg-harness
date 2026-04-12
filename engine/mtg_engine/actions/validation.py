from __future__ import annotations

from mtg_engine.state.models import GameState


def require_active_player(state: GameState, player_id: str) -> None:
    if state.turn.active_player != player_id:
        raise ValueError("player is not the active player")
    if state.turn.priority_player != player_id:
        raise ValueError("player does not have priority")


def require_step(state: GameState, step: str) -> None:
    if state.turn.step != step:
        raise ValueError(f"action requires step {step}, got {state.turn.step}")
