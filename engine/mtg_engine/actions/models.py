from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlayLandAction:
    player_id: str
    card_instance_id: str


@dataclass(frozen=True)
class ActivateManaAbilityAction:
    player_id: str
    source_instance_id: str


@dataclass(frozen=True)
class CastCreatureSpellAction:
    player_id: str
    card_instance_id: str


@dataclass(frozen=True, init=False)
class CastNonCreatureSpellAction:
    player_id: str
    card_instance_id: str
    target_instance_ids: tuple[str, ...] = field(default_factory=tuple)

    def __init__(
        self,
        player_id: str,
        card_instance_id: str,
        target_instance_id: str | None = None,
        target_instance_ids: tuple[str, ...] | None = None,
    ) -> None:
        object.__setattr__(self, "player_id", player_id)
        object.__setattr__(self, "card_instance_id", card_instance_id)
        if target_instance_ids is not None and target_instance_id is not None:
            raise ValueError("use target_instance_id or target_instance_ids, not both")
        if target_instance_ids is None:
            normalized = () if target_instance_id is None else (target_instance_id,)
        else:
            normalized = tuple(target_instance_ids)
        object.__setattr__(self, "target_instance_ids", normalized)

    @property
    def target_instance_id(self) -> str | None:
        if len(self.target_instance_ids) == 1:
            return self.target_instance_ids[0]
        return None


@dataclass(frozen=True)
class PassPriorityAction:
    player_id: str


@dataclass(frozen=True)
class AdvanceStepAction:
    player_id: str
    to_step: str


@dataclass(frozen=True)
class DeclareAttackersAction:
    player_id: str
    attacker_ids: tuple[str, ...]


@dataclass(frozen=True)
class DeclareBlockersAction:
    player_id: str
    blockers: dict[str, tuple[str, ...]]
