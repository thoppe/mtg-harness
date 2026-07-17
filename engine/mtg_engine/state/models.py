from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardInstance:
    instance_id: str
    oracle_id: str
    owner_id: str
    controller_id: str
    zone: str
    tapped: bool = False
    entered_battlefield_turn: int | None = None
    damage_marked: int = 0


@dataclass(frozen=True)
class PlayerState:
    player_id: str
    life_total: int
    library: tuple[str, ...]
    hand: tuple[str, ...]
    battlefield: tuple[str, ...]
    graveyard: tuple[str, ...]
    mana_pool: tuple[str, ...]
    lands_played_this_turn: int = 0


@dataclass(frozen=True)
class TurnState:
    turn_number: int
    active_player: str
    priority_player: str
    step: str


@dataclass(frozen=True)
class CombatState:
    attacking_player: str
    defending_player: str
    attackers: tuple[str, ...]
    blockers: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class StackEntry:
    card_instance_id: str
    controller_id: str
    target_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class GameState:
    game_id: str
    rng_seed: int
    players: dict[str, PlayerState]
    objects: dict[str, CardInstance]
    stack: tuple[str, ...]
    turn: TurnState
    combat: CombatState | None = None
    stack_entries: tuple[StackEntry, ...] = ()
    consecutive_passes: int = 0
