from __future__ import annotations

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    AdvanceStepAction,
    CastCreatureSpellAction,
    PassPriorityAction,
    PlayLandAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.state.models import GameState


def enumerate_legal_actions(state: GameState, card_repository: CardRepository) -> tuple[object, ...]:
    if state.turn.step != "precombat_main_step":
        return ()

    if state.turn.priority_player != state.turn.active_player:
        return _enumerate_non_active_priority_actions(state)

    return _enumerate_active_precombat_main_actions(state, card_repository)


def _enumerate_active_precombat_main_actions(
    state: GameState,
    card_repository: CardRepository,
) -> tuple[object, ...]:
    player = state.players[state.turn.active_player]
    actions: list[object] = []

    if player.lands_played_this_turn == 0:
        for instance_id in player.hand:
            card = state.objects[instance_id]
            card_definition = card_repository.get(card.oracle_id)
            if card_definition.is_land:
                actions.append(
                    PlayLandAction(
                        player_id=state.turn.active_player,
                        card_instance_id=instance_id,
                    )
                )

    for instance_id in player.battlefield:
        permanent = state.objects[instance_id]
        card_definition = card_repository.get(permanent.oracle_id)
        if card_definition.name == "Plains" and not permanent.tapped:
            actions.append(
                ActivateManaAbilityAction(
                    player_id=state.turn.active_player,
                    source_instance_id=instance_id,
                )
            )

    for instance_id in player.hand:
        card = state.objects[instance_id]
        card_definition = card_repository.get(card.oracle_id)
        if not card_definition.is_creature:
            continue
        required_white, required_generic = _parse_mana_cost(card_definition.mana_cost)
        if player.mana_pool.count("W") >= required_white + required_generic:
            actions.append(
                CastCreatureSpellAction(
                    player_id=state.turn.active_player,
                    card_instance_id=instance_id,
                )
            )

    actions.append(
        AdvanceStepAction(
            player_id=state.turn.active_player,
            to_step="begin_combat_step",
        )
    )
    actions.append(PassPriorityAction(player_id=state.turn.active_player))
    return tuple(actions)


def _enumerate_non_active_priority_actions(state: GameState) -> tuple[object, ...]:
    return ()


def _parse_mana_cost(mana_cost: str) -> tuple[int, int]:
    if not mana_cost:
        return 0, 0

    required_white = 0
    required_generic = 0
    symbols = mana_cost.replace("{", " ").replace("}", " ").split()
    for symbol in symbols:
        if symbol == "W":
            required_white += 1
        elif symbol.isdigit():
            required_generic += int(symbol)
        else:
            raise ValueError(f"unsupported mana symbol in v0: {symbol}")
    return required_white, required_generic
