"""Player-scoped, versioned views of the reducer's legal action list.

This module deliberately derives every option from ``enumerate_legal_actions``.
It is presentation plumbing, not another rules or target-legality engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
import json
from typing import Any, Mapping

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.priority import enumerate_legal_actions
from mtg_engine.rules.characteristics import effective_power, effective_toughness
from mtg_engine.state.models import GameState


SCHEMA_VERSION = "v0"


@dataclass(frozen=True)
class ParameterSlot:
    """One input required to turn a descriptor into an enumerated action."""

    name: str
    kind: str
    required: bool = True
    minimum: int | None = None
    maximum: int | None = None
    ordered: bool = False
    distinct: bool = False


@dataclass(frozen=True)
class ActionSource:
    instance_id: str
    object_id: str
    label: str


@dataclass(frozen=True)
class LegalActionDescriptor:
    action_id: str
    kind: str
    player_id: str
    source: ActionSource | None
    parameters: tuple[ParameterSlot, ...]


@dataclass(frozen=True)
class LegalActionsResponse:
    schema_version: str
    game_id: str
    state_revision: str
    player_id: str
    actions: tuple[LegalActionDescriptor, ...]


@dataclass(frozen=True)
class TargetCandidate:
    """A visible candidate value for one parameter slot."""

    candidate_id: str
    value: object
    kind: str
    label: str


@dataclass(frozen=True)
class ValidTargetsResponse:
    schema_version: str
    game_id: str
    state_revision: str
    player_id: str
    action_id: str
    slot: ParameterSlot
    candidates: tuple[TargetCandidate, ...]


class LegalActionApiError(ValueError):
    """A safe, structured-facing rejection for descriptor operations."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def state_revision(state: GameState) -> str:
    """Opaque deterministic revision for stale-client protection.

    GameState is immutable and contains only reducer data, so a canonical
    dataclass representation makes the revision change with every state
    change without requiring a separate mutable counter.
    """
    return sha256(_canonical_json(_jsonable(state)).encode()).hexdigest()[:20]


def build_legal_actions_response(
    state: GameState,
    card_repository: CardRepository,
    player_id: str,
    revision: str | None = None,
) -> LegalActionsResponse:
    """Return actions currently executable by ``player_id`` only."""
    _require_player(state, player_id)
    groups = _descriptor_groups(state, card_repository, player_id)
    return LegalActionsResponse(
        schema_version=SCHEMA_VERSION,
        game_id=state.game_id,
        state_revision=revision or state_revision(state),
        player_id=player_id,
        actions=tuple(group[0] for group in groups),
    )


def valid_targets_response(
    state: GameState,
    card_repository: CardRepository,
    player_id: str,
    action_id: str,
    slot: str,
    partial_selection: Mapping[str, object] | None = None,
    revision: str | None = None,
) -> ValidTargetsResponse:
    """Return candidates compatible with a partially-filled descriptor.

    The candidates are projections of actual, currently enumerated actions.
    This is intentionally conservative: if an action is absent from the
    reducer enumeration, it cannot be suggested here.
    """
    descriptor, actions = _find_descriptor_group(state, card_repository, player_id, action_id)
    parameter = next((item for item in descriptor.parameters if item.name == slot), None)
    if parameter is None:
        raise LegalActionApiError("unknown_slot", "parameter slot is not available for this action")
    partial = {key: _normalize(value) for key, value in (partial_selection or {}).items()}
    unknown = set(partial).difference(item.name for item in descriptor.parameters)
    if unknown:
        raise LegalActionApiError("malformed_parameters", "partial selection contains an unknown slot")
    candidates = _candidates_for_slot(state, card_repository, actions, parameter, partial)
    return ValidTargetsResponse(
        schema_version=SCHEMA_VERSION,
        game_id=state.game_id,
        state_revision=revision or state_revision(state),
        player_id=player_id,
        action_id=action_id,
        slot=parameter,
        candidates=candidates,
    )


def action_for_descriptor(
    state: GameState,
    card_repository: CardRepository,
    player_id: str,
    action_id: str,
    parameters: Mapping[str, object] | None = None,
) -> object:
    """Resolve an API descriptor to the existing immutable reducer action.

    Callers cannot invent actions: this returns one of the objects generated
    by the current reducer enumeration, or raises a non-revealing error.
    """
    descriptor, actions = _find_descriptor_group(state, card_repository, player_id, action_id)
    supplied = {key: _normalize(value) for key, value in (parameters or {}).items()}
    unknown = set(supplied).difference(slot.name for slot in descriptor.parameters)
    if unknown:
        raise LegalActionApiError("malformed_parameters", "parameters contain an unknown slot")
    matches = [
        action for action in actions
        if all(_normalize(_action_parameters(action)[key]) == value for key, value in supplied.items())
    ]
    if not matches:
        raise LegalActionApiError("no_longer_legal", "action parameters are not currently legal")
    if len(matches) != 1:
        raise LegalActionApiError("incomplete_parameters", "action parameters do not select one legal action")
    return matches[0]


def _descriptor_groups(
    state: GameState, card_repository: CardRepository, player_id: str,
) -> tuple[tuple[LegalActionDescriptor, tuple[object, ...]], ...]:
    actions = tuple(
        action for action in enumerate_legal_actions(state, card_repository)
        if getattr(action, "player_id", None) == player_id
    )
    grouped: dict[str, list[object]] = {}
    for action in actions:
        grouped.setdefault(_action_id(action), []).append(action)
    result = []
    for action_id, variants in grouped.items():
        first = variants[0]
        result.append((
            LegalActionDescriptor(
                action_id=action_id,
                kind=type(first).__name__,
                player_id=player_id,
                source=_source_for_action(state, card_repository, first),
                parameters=_parameter_slots(tuple(variants)),
            ),
            tuple(variants),
        ))
    return tuple(result)


def _find_descriptor_group(
    state: GameState, card_repository: CardRepository, player_id: str, action_id: str,
) -> tuple[LegalActionDescriptor, tuple[object, ...]]:
    _require_player(state, player_id)
    for descriptor, actions in _descriptor_groups(state, card_repository, player_id):
        if descriptor.action_id == action_id:
            return descriptor, actions
    raise LegalActionApiError("unknown_descriptor", "action descriptor is not currently available")


def _action_id(action: object) -> str:
    identity = {"kind": type(action).__name__, "player_id": getattr(action, "player_id", None)}
    for name in ("card_instance_id", "source_instance_id", "decision_id", "to_step"):
        if hasattr(action, name):
            identity[name] = getattr(action, name)
    digest = sha256(_canonical_json(identity).encode()).hexdigest()[:16]
    return f"{type(action).__name__}:{digest}"


def _parameter_slots(actions: tuple[object, ...]) -> tuple[ParameterSlot, ...]:
    """Describe fields using the reducer's currently legal variants.

    The action map identifies parameter shapes, while the actual variants set
    accurate bounds for this descriptor (such as a one-to-three target spell
    or the legal X range at the current mana pool).
    """
    first = actions[0]
    name = type(first).__name__
    slots: dict[str, tuple[str, int | None, int | None, bool, bool]] = {
        "CastNonCreatureSpellAction": {
            "target_instance_ids": ("targets", 0, None, False, True),
            "chosen_x": ("number", 0, None, False, False),
            "additional_cost_instance_id": ("additional_cost", 0, 1, False, False),
            "damage_assignments": ("allocation", 0, None, True, True),
        },
        "ActivateAbilityAction": {"target_instance_ids": ("targets", 0, None, False, True)},
        "ResolveChoiceAction": {
            "selected_instance_ids": ("choice", 0, None, False, True),
            "ordered_instance_ids": ("choice", 0, None, True, True),
            "declared_count": ("number", 0, None, False, False),
            "choice_boolean": ("boolean", None, None, False, False),
            "shuffle_library": ("boolean", None, None, False, False),
        },
        "DeclareAttackersAction": {"attacker_ids": ("targets", 0, None, False, True)},
        "DeclareBlockersAction": {"blockers": ("blocker_assignment", 0, None, False, True)},
    }.get(name, {})
    parameters = _action_parameters(first)
    return tuple(
        _parameter_slot(slot_name, details, actions)
        for slot_name, details in slots.items()
        # Only include meaningful fields.  This avoids requiring clients to
        # submit synthetic None/empty values for a card with no such cost.
        if slot_name in parameters and _field_is_meaningful(slot_name, parameters[slot_name])
    )


def _parameter_slot(
    slot_name: str,
    details: tuple[str, int | None, int | None, bool, bool],
    actions: tuple[object, ...],
) -> ParameterSlot:
    kind, minimum, maximum, ordered, distinct = details
    values = tuple(_action_parameters(action)[slot_name] for action in actions)
    if kind in {"targets", "choice", "allocation"}:
        lengths = tuple(len(value) for value in values if isinstance(value, tuple))
        if lengths:
            minimum, maximum = min(lengths), max(lengths)
    elif kind == "blocker_assignment":
        lengths = tuple(len(value) for value in values if isinstance(value, dict))
        if lengths:
            minimum, maximum = min(lengths), max(lengths)
    elif kind == "number":
        numbers = tuple(
            value for value in values
            if isinstance(value, int) and not isinstance(value, bool)
        )
        if numbers:
            minimum, maximum = min(numbers), max(numbers)
    return ParameterSlot(slot_name, kind, True, minimum, maximum, ordered, distinct)


def _field_is_meaningful(name: str, value: object) -> bool:
    if name in {"target_instance_ids", "selected_instance_ids", "ordered_instance_ids", "damage_assignments", "attacker_ids", "blockers"}:
        return True
    return value is not None


def _action_parameters(action: object) -> dict[str, object]:
    names = {
        "CastNonCreatureSpellAction": ("target_instance_ids", "chosen_x", "additional_cost_instance_id", "damage_assignments"),
        "ActivateAbilityAction": ("target_instance_ids",),
        "ResolveChoiceAction": ("selected_instance_ids", "ordered_instance_ids", "declared_count", "choice_boolean", "shuffle_library"),
        "DeclareAttackersAction": ("attacker_ids",),
        "DeclareBlockersAction": ("blockers",),
    }.get(type(action).__name__, ())
    return {name: getattr(action, name) for name in names}


def _source_for_action(state: GameState, card_repository: CardRepository, action: object) -> ActionSource | None:
    instance_id = getattr(action, "card_instance_id", None) or getattr(action, "source_instance_id", None)
    if instance_id is None or instance_id not in state.objects:
        return None
    card = state.objects[instance_id]
    # A descriptor is player-scoped.  Its source can only be the querying
    # player's own hand card or a public permanent; never an opponent's hand.
    if card.zone == "hand" and card.owner_id != getattr(action, "player_id", None):
        return None
    return ActionSource(instance_id, card.object_id, card_repository.get(card.oracle_id).name)


def _candidates_for_slot(
    state: GameState,
    card_repository: CardRepository,
    actions: tuple[object, ...],
    slot: ParameterSlot,
    partial: Mapping[str, object],
) -> tuple[TargetCandidate, ...]:
    values: list[object] = []
    selected_here = partial.get(slot.name)
    for action in actions:
        parameters = _action_parameters(action)
        if not _matches_partial(parameters, partial, skip=slot.name):
            continue
        value = _normalize(parameters[slot.name])
        for candidate in _remaining_values(value, selected_here, slot):
            if candidate not in values:
                values.append(candidate)
    return tuple(_candidate(state, card_repository, candidate, slot.kind) for candidate in values)


def _matches_partial(parameters: Mapping[str, object], partial: Mapping[str, object], skip: str) -> bool:
    for name, value in partial.items():
        if name == skip or name not in parameters:
            continue
        if _normalize(parameters[name]) != value:
            return False
    return True


def _remaining_values(value: object, selected: object | None, slot: ParameterSlot) -> tuple[object, ...]:
    if slot.kind not in {"targets", "choice"} or not isinstance(value, tuple):
        return (value,)
    chosen = _normalize(selected) if selected is not None else ()
    if not isinstance(chosen, tuple):
        return ()
    if slot.ordered:
        if value[:len(chosen)] != chosen:
            return ()
    elif not set(chosen).issubset(value):
        return ()
    return tuple(item for item in value if item not in chosen)


def _candidate(state: GameState, card_repository: CardRepository, value: object, kind: str) -> TargetCandidate:
    label = _candidate_label(state, card_repository, value, kind)
    if isinstance(value, str) and value in state.objects:
        return TargetCandidate(value, value, kind, label)
    if isinstance(value, str) and value in state.players:
        return TargetCandidate(value, value, kind, value)
    rendered = _canonical_json(_jsonable(value))
    return TargetCandidate(rendered, value, kind, label)


def _candidate_label(
    state: GameState, card_repository: CardRepository, value: object, kind: str,
) -> str:
    """Return a player-facing description while retaining ``value`` verbatim.

    Composite candidates are complete legal choices, not data intended for a
    human to parse.  In particular, blocker assignments contain instance IDs
    by necessity; those IDs must never become terminal-facing labels.
    """
    if kind == "blocker_assignment":
        return _blocker_assignment_label(state, card_repository, value)
    if kind == "allocation":
        return _damage_allocation_label(state, card_repository, value)
    if isinstance(value, str) and value in state.objects:
        # Candidate object identities are only emitted from visible battlefield
        # targets or from the querying player's pending choice.  The latter is
        # protected by player filtering at descriptor-group construction.
        return _object_label(state, card_repository, value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _object_label(state: GameState, card_repository: CardRepository, instance_id: object) -> str:
    """Name an object without exposing its engine instance identifier."""
    if isinstance(instance_id, str) and instance_id in state.objects:
        card = state.objects[instance_id]
        if card.zone == "library":
            return "private card"
        definition = card_repository.get(card.oracle_id)
        if definition.is_creature:
            power = effective_power(state, card_repository, instance_id)
            toughness = effective_toughness(state, card_repository, instance_id)
            return f"{definition.name} ({power}/{toughness})"
        return definition.name
    return "unknown object"


def _blocker_assignment_label(
    state: GameState, card_repository: CardRepository, value: object,
) -> str:
    if not isinstance(value, tuple):
        return "Invalid blocker assignment"
    if not value:
        return "Declare no blockers"
    assignments: list[str] = []
    for entry in value:
        if not (isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[1], tuple)):
            return "Invalid blocker assignment"
        attacker_id, blocker_ids = entry
        attacker = _object_label(state, card_repository, attacker_id)
        blockers = [_object_label(state, card_repository, blocker_id) for blocker_id in blocker_ids]
        if not blockers:
            continue
        verb = "blocks" if len(blockers) == 1 else "block"
        assignments.append(f"{' and '.join(blockers)} {verb} {attacker}")
    return "; ".join(assignments) if assignments else "Declare no blockers"


def _damage_allocation_label(
    state: GameState, card_repository: CardRepository, value: object,
) -> str:
    if not isinstance(value, tuple) or not value:
        return "No damage allocation"
    assignments: list[str] = []
    for entry in value:
        if not (isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[1], int)):
            return "Invalid damage allocation"
        target_id, amount = entry
        noun = "damage" if amount != 1 else "damage"
        assignments.append(f"{amount} {noun} to {_object_label(state, card_repository, target_id)}")
    return "Deal " + " and ".join(assignments)


def _require_player(state: GameState, player_id: str) -> None:
    if player_id not in state.players:
        raise LegalActionApiError("wrong_player", "player is not part of this game")


def _normalize(value: object) -> object:
    if isinstance(value, list):
        return tuple(_normalize(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_normalize(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _normalize(item)) for key, item in value.items()))
    return value


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
