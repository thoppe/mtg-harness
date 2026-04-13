from __future__ import annotations

from dataclasses import replace

from .models import CardInstance, GameState, PlayerState


ZONE_FIELDS = {
    "library": "library",
    "hand": "hand",
    "battlefield": "battlefield",
    "graveyard": "graveyard",
}


def move_object(
    state: GameState,
    *,
    instance_id: str,
    from_zone: str,
    to_zone: str,
    player_id: str,
) -> GameState:
    object_record = state.objects[instance_id]

    if from_zone == "stack":
        state = replace(state, stack=tuple(value for value in state.stack if value != instance_id))
    elif from_zone in ZONE_FIELDS:
        player = state.players[player_id]
        from_values = tuple(value for value in getattr(player, ZONE_FIELDS[from_zone]) if value != instance_id)
        state = update_player(state, replace(player, **{ZONE_FIELDS[from_zone]: from_values}))
    else:
        raise ValueError(f"unsupported from_zone: {from_zone}")

    if to_zone == "stack":
        state = replace(state, stack=state.stack + (instance_id,))
    elif to_zone in ZONE_FIELDS:
        player = state.players[player_id]
        to_values = getattr(player, ZONE_FIELDS[to_zone]) + (instance_id,)
        state = update_player(state, replace(player, **{ZONE_FIELDS[to_zone]: to_values}))
    else:
        raise ValueError(f"unsupported to_zone: {to_zone}")

    entered_turn = object_record.entered_battlefield_turn
    if to_zone == "battlefield":
        entered_turn = state.turn.turn_number
    damage_marked = object_record.damage_marked
    if to_zone != "battlefield":
        damage_marked = 0
    updated_object = replace(
        object_record,
        zone=to_zone,
        entered_battlefield_turn=entered_turn,
        damage_marked=damage_marked,
    )
    return update_object(state, updated_object)


def move_object_to_top_of_library(
    state: GameState,
    *,
    instance_id: str,
    from_zone: str,
    player_id: str,
) -> GameState:
    object_record = state.objects[instance_id]

    if from_zone == "stack":
        state = replace(state, stack=tuple(value for value in state.stack if value != instance_id))
    elif from_zone in ZONE_FIELDS:
        player = state.players[player_id]
        from_values = tuple(value for value in getattr(player, ZONE_FIELDS[from_zone]) if value != instance_id)
        state = update_player(state, replace(player, **{ZONE_FIELDS[from_zone]: from_values}))
    else:
        raise ValueError(f"unsupported from_zone: {from_zone}")

    player = state.players[player_id]
    state = update_player(
        state,
        replace(player, library=(instance_id,) + player.library),
    )
    updated_object = replace(
        object_record,
        zone="library",
        damage_marked=0,
    )
    return update_object(state, updated_object)


def update_player(state: GameState, player: PlayerState) -> GameState:
    updated_players = dict(state.players)
    updated_players[player.player_id] = player
    return replace(state, players=updated_players)


def update_object(state: GameState, card_instance: CardInstance) -> GameState:
    updated_objects = dict(state.objects)
    updated_objects[card_instance.instance_id] = card_instance
    return replace(state, objects=updated_objects)
