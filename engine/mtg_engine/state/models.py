from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardInstance:
    instance_id: str
    oracle_id: str
    owner_id: str
    controller_id: str
    zone: str


@dataclass(frozen=True)
class PlayerState:
    player_id: str
    life_total: int
    library: tuple[str, ...]
    hand: tuple[str, ...]
    battlefield: tuple[str, ...]
    graveyard: tuple[str, ...]
    mana_pool: tuple[str, ...]


@dataclass(frozen=True)
class TurnState:
    turn_number: int
    active_player: str
    priority_player: str
    step: str


@dataclass(frozen=True)
class GameState:
    game_id: str
    rng_seed: int
    players: dict[str, PlayerState]
    objects: dict[str, CardInstance]
    stack: tuple[str, ...]
    turn: TurnState
