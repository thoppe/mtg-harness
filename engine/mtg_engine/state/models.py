from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardInstance:
    instance_id: str
    oracle_id: str
    owner_id: str
    controller_id: str
    zone: str
    zone_change_counter: int = 0
    tapped: bool = False
    entered_battlefield_turn: int | None = None
    damage_marked: int = 0
    temporary_power_bonus: int = 0
    temporary_toughness_bonus: int = 0

    @property
    def object_id(self) -> str:
        """Stable identity for this particular zone incarnation."""
        return f"{self.instance_id}@{self.zone_change_counter}"


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
    chosen_x: int = 0


@dataclass(frozen=True)
class PendingDecision:
    decision_id: str
    chooser_id: str
    kind: str
    source_object_id: str
    option_ids: tuple[str, ...]
    selected_card_type: str


@dataclass(frozen=True)
class GameOutcome:
    status: str = "in_progress"
    winner_id: str | None = None
    loser_ids: tuple[str, ...] = ()
    reason: str | None = None


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
    outcome: GameOutcome = GameOutcome()
    pending_decision: PendingDecision | None = None
    rng_cursor: int = 0
