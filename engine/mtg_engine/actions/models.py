from __future__ import annotations

from dataclasses import dataclass


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


@dataclass(frozen=True)
class CastNonCreatureSpellAction:
    player_id: str
    card_instance_id: str
    target_instance_id: str


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
