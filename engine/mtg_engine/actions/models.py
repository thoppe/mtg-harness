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
    chosen_x: int = 0
    additional_cost_instance_id: str | None = None

    def __init__(
        self,
        player_id: str,
        card_instance_id: str,
        target_instance_id: str | None = None,
        target_instance_ids: tuple[str, ...] | None = None,
        chosen_x: int = 0,
        additional_cost_instance_id: str | None = None,
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
        if chosen_x < 0:
            raise ValueError("chosen_x must not be negative")
        object.__setattr__(self, "chosen_x", chosen_x)
        object.__setattr__(self, "additional_cost_instance_id", additional_cost_instance_id)

    @property
    def target_instance_id(self) -> str | None:
        if len(self.target_instance_ids) == 1:
            return self.target_instance_ids[0]
        return None


@dataclass(frozen=True)
class PassPriorityAction:
    player_id: str


@dataclass(frozen=True, init=False)
class ResolveChoiceAction:
    player_id: str
    decision_id: str
    selected_instance_ids: tuple[str, ...]
    ordered_instance_ids: tuple[str, ...]
    declared_count: int | None
    choice_boolean: bool | None
    shuffle_library: bool | None

    def __init__(
        self,
        player_id: str,
        decision_id: str,
        selected_instance_id: str | None = None,
        *,
        selected_instance_ids: tuple[str, ...] | None = None,
        ordered_instance_ids: tuple[str, ...] = (),
        declared_count: int | None = None,
        choice_boolean: bool | None = None,
        shuffle_library: bool | None = None,
    ) -> None:
        """Record an explicit hidden-zone decision.

        The positional ``selected_instance_id`` form is retained for existing
        Wave 3 tutor replays.  New callers use ``selected_instance_ids`` for
        set choices and ``ordered_instance_ids`` when the source asks a player
        to arrange cards in a particular order.
        """
        if selected_instance_ids is not None and selected_instance_id is not None:
            raise ValueError("use selected_instance_id or selected_instance_ids, not both")
        normalized_selection = (
            () if selected_instance_id is None else (selected_instance_id,)
        ) if selected_instance_ids is None else tuple(selected_instance_ids)
        normalized_order = tuple(ordered_instance_ids)
        if len(set(normalized_selection)) != len(normalized_selection):
            raise ValueError("selected_instance_ids must not contain duplicates")
        if len(set(normalized_order)) != len(normalized_order):
            raise ValueError("ordered_instance_ids must not contain duplicates")
        if declared_count is not None and declared_count < 0:
            raise ValueError("declared_count must not be negative")
        object.__setattr__(self, "player_id", player_id)
        object.__setattr__(self, "decision_id", decision_id)
        object.__setattr__(self, "selected_instance_ids", normalized_selection)
        object.__setattr__(self, "ordered_instance_ids", normalized_order)
        object.__setattr__(self, "declared_count", declared_count)
        object.__setattr__(self, "choice_boolean", choice_boolean)
        object.__setattr__(self, "shuffle_library", shuffle_library)

    @property
    def selected_instance_id(self) -> str | None:
        """Compatibility view for the original one-card choice contract."""
        if len(self.selected_instance_ids) == 1:
            return self.selected_instance_ids[0]
        return None


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
