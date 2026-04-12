from __future__ import annotations

from dataclasses import dataclass, replace

import re

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    CastCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PlayLandAction,
)
from mtg_engine.actions.validation import require_active_player, require_step
from mtg_engine.cards.repository import CardRepository
from mtg_engine.events.log import EventLog
from mtg_engine.state.models import GameState, TurnState
from mtg_engine.state.zones import move_object, update_object, update_player
from mtg_engine.rules.combat import apply_combat_damage, tap_attackers, with_combat_state

from .setup import GameBootstrap

FIRST_TURN_STEP_SEQUENCE = (
    "turn_begin",
    "untap_step",
    "upkeep_step",
    "draw_step",
    "precombat_main_step",
)


@dataclass(frozen=True)
class TurnResult:
    state: GameState
    event_log: tuple


def start_first_turn(session: GameBootstrap) -> TurnResult:
    state = session.state
    if state.turn.step != "opening_hand_ready":
        raise ValueError("first turn can start only from opening_hand_ready")

    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="turn_started",
        active_player=state.turn.active_player,
        payload={
            "turn_number": state.turn.turn_number,
            "active_player": state.turn.active_player,
        },
    )

    current_state = state
    current_step = state.turn.step
    for next_step in FIRST_TURN_STEP_SEQUENCE:
        current_state = replace(
            current_state,
            turn=TurnState(
                turn_number=current_state.turn.turn_number,
                active_player=current_state.turn.active_player,
                priority_player=current_state.turn.active_player,
                step=next_step,
            ),
        )
        event_log.append(
            event_type="step_changed",
            active_player=current_state.turn.active_player,
            payload={
                "turn_number": current_state.turn.turn_number,
                "from_step": current_step,
                "to_step": next_step,
            },
        )
        current_step = next_step
        if next_step == "draw_step":
            current_state = _draw_one_card_if_available(current_state, event_log)

    return TurnResult(state=current_state, event_log=event_log.events)


def play_land(
    session: TurnResult | GameBootstrap,
    action: PlayLandAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    require_active_player(state, action.player_id)
    require_step(state, "precombat_main_step")

    player = state.players[action.player_id]
    if player.lands_played_this_turn >= 1:
        raise ValueError("player has already played a land this turn")
    if action.card_instance_id not in player.hand:
        raise ValueError("land must be in the active player's hand")

    card = state.objects[action.card_instance_id]
    card_definition = card_repository.get(card.oracle_id)
    if "Land" not in card_definition.type_line:
        raise ValueError("selected card is not a land")

    next_state = move_object(
        state,
        instance_id=action.card_instance_id,
        from_zone="hand",
        to_zone="battlefield",
        player_id=action.player_id,
    )
    updated_player = replace(
        next_state.players[action.player_id],
        lands_played_this_turn=player.lands_played_this_turn + 1,
    )
    next_state = update_player(next_state, updated_player)

    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="land_played",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "card_instance_id": action.card_instance_id,
            "oracle_id": card.oracle_id,
        },
    )
    event_log.append(
        event_type="object_moved_between_zones",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "card_instance_id": action.card_instance_id,
            "oracle_id": card.oracle_id,
            "from_zone": "hand",
            "to_zone": "battlefield",
        },
    )
    return TurnResult(state=next_state, event_log=event_log.events)


def activate_mana_ability(
    session: TurnResult | GameBootstrap,
    action: ActivateManaAbilityAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    require_active_player(state, action.player_id)
    require_step(state, "precombat_main_step")

    player = state.players[action.player_id]
    if action.source_instance_id not in player.battlefield:
        raise ValueError("mana source must be on the battlefield")

    source = state.objects[action.source_instance_id]
    card_definition = card_repository.get(source.oracle_id)
    if card_definition.name != "Plains":
        raise ValueError("only Plains mana generation is implemented")
    if source.tapped:
        raise ValueError("mana source is already tapped")

    updated_player = replace(player, mana_pool=player.mana_pool + ("W",))
    next_state = update_player(state, updated_player)
    next_state = update_object(next_state, replace(source, tapped=True))
    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="mana_added",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "source_instance_id": action.source_instance_id,
            "mana": ["W"],
        },
    )
    return TurnResult(state=next_state, event_log=event_log.events)


def cast_creature_spell(
    session: TurnResult | GameBootstrap,
    action: CastCreatureSpellAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    require_active_player(state, action.player_id)
    require_step(state, "precombat_main_step")

    player = state.players[action.player_id]
    if action.card_instance_id not in player.hand:
        raise ValueError("spell must be in the active player's hand")

    card = state.objects[action.card_instance_id]
    card_definition = card_repository.get(card.oracle_id)
    if not card_definition.is_creature:
        raise ValueError("only creature spell casting is implemented")

    required_white, required_generic = _parse_mana_cost(card_definition.mana_cost)
    mana_pool = list(player.mana_pool)
    if mana_pool.count("W") < required_white + required_generic:
        raise ValueError("insufficient mana to cast creature spell")

    remaining_pool = tuple(mana_pool[(required_white + required_generic) :])
    casting_state = update_player(state, replace(player, mana_pool=remaining_pool))
    casting_state = move_object(
        casting_state,
        instance_id=action.card_instance_id,
        from_zone="hand",
        to_zone="stack",
        player_id=action.player_id,
    )

    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="spell_cast",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "card_instance_id": action.card_instance_id,
            "oracle_id": card.oracle_id,
            "mana_cost": card_definition.mana_cost,
        },
    )
    event_log.append(
        event_type="object_moved_between_zones",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "card_instance_id": action.card_instance_id,
            "oracle_id": card.oracle_id,
            "from_zone": "hand",
            "to_zone": "stack",
        },
    )

    resolved_state = move_object(
        casting_state,
        instance_id=action.card_instance_id,
        from_zone="stack",
        to_zone="battlefield",
        player_id=action.player_id,
    )
    event_log.append(
        event_type="spell_resolved",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "card_instance_id": action.card_instance_id,
            "oracle_id": card.oracle_id,
        },
    )
    event_log.append(
        event_type="object_moved_between_zones",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "card_instance_id": action.card_instance_id,
            "oracle_id": card.oracle_id,
            "from_zone": "stack",
            "to_zone": "battlefield",
        },
    )
    return TurnResult(state=resolved_state, event_log=event_log.events)


def advance_to_begin_combat(session: TurnResult | GameBootstrap) -> TurnResult:
    state = session.state
    require_step(state, "precombat_main_step")
    event_log = EventLog.from_events(state.game_id, session.event_log)
    begin_combat_state = replace(state, turn=replace(state.turn, step="begin_combat_step"))
    event_log.append(
        event_type="step_changed",
        active_player=state.turn.active_player,
        payload={
            "turn_number": state.turn.turn_number,
            "from_step": "precombat_main_step",
            "to_step": "begin_combat_step",
        },
    )
    attackers_state = replace(begin_combat_state, turn=replace(begin_combat_state.turn, step="declare_attackers_step"))
    event_log.append(
        event_type="step_changed",
        active_player=state.turn.active_player,
        payload={
            "turn_number": state.turn.turn_number,
            "from_step": "begin_combat_step",
            "to_step": "declare_attackers_step",
        },
    )
    return TurnResult(state=attackers_state, event_log=event_log.events)


def declare_attackers(
    session: TurnResult | GameBootstrap,
    action: DeclareAttackersAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    require_active_player(state, action.player_id)
    require_step(state, "declare_attackers_step")

    defending_player = _other_player(state, action.player_id)
    for attacker_id in action.attacker_ids:
        if attacker_id not in state.players[action.player_id].battlefield:
            raise ValueError("attacker must be on the active player's battlefield")
        attacker = state.objects[attacker_id]
        attacker_card = card_repository.get(attacker.oracle_id)
        if not attacker_card.is_creature:
            raise ValueError("only creatures can attack")
        if attacker.tapped:
            raise ValueError("attacker is already tapped")
        if attacker.entered_battlefield_turn == state.turn.turn_number:
            raise ValueError("summoning-sick creature cannot attack in v0")

    next_state = tap_attackers(state, action.attacker_ids)
    next_state = with_combat_state(
        next_state,
        attacking_player=action.player_id,
        defending_player=defending_player,
        attackers=action.attacker_ids,
        blockers={},
    )
    next_state = replace(next_state, turn=replace(next_state.turn, step="declare_blockers_step"))

    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="attackers_declared",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "attacker_ids": list(action.attacker_ids),
            "defending_player": defending_player,
        },
    )
    event_log.append(
        event_type="step_changed",
        active_player=action.player_id,
        payload={
            "turn_number": state.turn.turn_number,
            "from_step": "declare_attackers_step",
            "to_step": "declare_blockers_step",
        },
    )
    return TurnResult(state=next_state, event_log=event_log.events)


def declare_blockers(
    session: TurnResult | GameBootstrap,
    action: DeclareBlockersAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    require_step(state, "declare_blockers_step")
    if state.combat is None:
        raise ValueError("blockers require an active combat")
    if action.player_id != state.combat.defending_player:
        raise ValueError("only the defending player may declare blockers")

    for attacker_id, blocker_ids in action.blockers.items():
        if attacker_id not in state.combat.attackers:
            raise ValueError("blocker assignment references a non-attacking creature")
        if len(blocker_ids) > 1:
            raise ValueError("v0 supports at most one blocker per attacker")
        for blocker_id in blocker_ids:
            if blocker_id not in state.players[action.player_id].battlefield:
                raise ValueError("blocker must be on defending player's battlefield")
            blocker = state.objects[blocker_id]
            blocker_card = card_repository.get(blocker.oracle_id)
            if not blocker_card.is_creature:
                raise ValueError("only creatures can block")
            if blocker.tapped:
                raise ValueError("tapped creature cannot block")

    next_state = with_combat_state(
        state,
        attacking_player=state.combat.attacking_player,
        defending_player=state.combat.defending_player,
        attackers=state.combat.attackers,
        blockers=action.blockers,
    )
    next_state = replace(next_state, turn=replace(next_state.turn, step="combat_damage_step"))

    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="blockers_declared",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "blockers": {key: list(value) for key, value in action.blockers.items()},
        },
    )
    event_log.append(
        event_type="step_changed",
        active_player=state.turn.active_player,
        payload={
            "turn_number": state.turn.turn_number,
            "from_step": "declare_blockers_step",
            "to_step": "combat_damage_step",
        },
    )
    return TurnResult(state=next_state, event_log=event_log.events)


def resolve_combat_damage(
    session: TurnResult | GameBootstrap,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    require_step(state, "combat_damage_step")

    next_state, combat_events = apply_combat_damage(state, card_repository)
    next_state = replace(next_state, turn=replace(next_state.turn, step="end_combat_step"))

    event_log = EventLog.from_events(state.game_id, session.event_log)
    for event in combat_events:
        event_log.append(
            event_type=event["event_type"],
            active_player=event["active_player"],
            payload=event["payload"],
        )
    event_log.append(
        event_type="step_changed",
        active_player=state.turn.active_player,
        payload={
            "turn_number": state.turn.turn_number,
            "from_step": "combat_damage_step",
            "to_step": "end_combat_step",
        },
    )
    return TurnResult(state=next_state, event_log=event_log.events)


def advance_to_cleanup(session: TurnResult | GameBootstrap) -> TurnResult:
    state = session.state
    require_step(state, "end_combat_step")

    event_log = EventLog.from_events(state.game_id, session.event_log)
    current_state = state
    current_step = "end_combat_step"
    for next_step in ("postcombat_main_step", "end_step", "cleanup_step"):
        current_state = replace(current_state, turn=replace(current_state.turn, step=next_step))
        event_log.append(
            event_type="step_changed",
            active_player=current_state.turn.active_player,
            payload={
                "turn_number": current_state.turn.turn_number,
                "from_step": current_step,
                "to_step": next_step,
            },
        )
        current_step = next_step

    current_state = _cleanup_end_of_turn_state(current_state)
    event_log.append(
        event_type="turn_ended",
        active_player=current_state.turn.active_player,
        payload={
            "turn_number": current_state.turn.turn_number,
            "active_player": current_state.turn.active_player,
        },
    )
    return TurnResult(state=current_state, event_log=event_log.events)


def start_next_turn(session: TurnResult | GameBootstrap) -> TurnResult:
    state = session.state
    require_step(state, "cleanup_step")

    next_active_player = _other_player(state, state.turn.active_player)
    next_turn_number = state.turn.turn_number + 1
    current_state = replace(
        state,
        turn=TurnState(
            turn_number=next_turn_number,
            active_player=next_active_player,
            priority_player=next_active_player,
            step="turn_begin",
        ),
    )
    current_state = _untap_player_battlefield(current_state, next_active_player)

    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="turn_started",
        active_player=next_active_player,
        payload={
            "turn_number": next_turn_number,
            "active_player": next_active_player,
        },
    )

    current_step = "turn_begin"
    for next_step in ("untap_step", "upkeep_step", "draw_step", "precombat_main_step"):
        current_state = replace(current_state, turn=replace(current_state.turn, step=next_step))
        event_log.append(
            event_type="step_changed",
            active_player=next_active_player,
            payload={
                "turn_number": next_turn_number,
                "from_step": current_step,
                "to_step": next_step,
            },
        )
        current_step = next_step
        if next_step == "draw_step":
            current_state = _draw_one_card_if_available(current_state, event_log)

    return TurnResult(state=current_state, event_log=event_log.events)


def _draw_one_card_if_available(state: GameState, event_log: EventLog) -> GameState:
    player = state.players[state.turn.active_player]
    if not player.library:
        return state

    top_instance_id = player.library[0]
    card = state.objects[top_instance_id]
    next_state = move_object(
        state,
        instance_id=top_instance_id,
        from_zone="library",
        to_zone="hand",
        player_id=state.turn.active_player,
    )
    event_log.append(
        event_type="object_moved_between_zones",
        active_player=state.turn.active_player,
        payload={
            "player_id": state.turn.active_player,
            "card_instance_id": top_instance_id,
            "oracle_id": card.oracle_id,
            "from_zone": "library",
            "to_zone": "hand",
        },
    )
    return next_state


def _parse_mana_cost(mana_cost: str) -> tuple[int, int]:
    if not mana_cost:
        return 0, 0
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    required_white = 0
    required_generic = 0
    for symbol in symbols:
        if symbol == "W":
            required_white += 1
        elif symbol.isdigit():
            required_generic += int(symbol)
        else:
            raise ValueError(f"unsupported mana symbol in v0: {symbol}")
    return required_white, required_generic


def _other_player(state: GameState, player_id: str) -> str:
    for candidate in state.players:
        if candidate != player_id:
            return candidate
    raise ValueError("game state does not contain an opposing player")


def _cleanup_end_of_turn_state(state: GameState) -> GameState:
    updated_players = {
        player_id: replace(player, mana_pool=(), lands_played_this_turn=0)
        for player_id, player in state.players.items()
    }
    updated_objects = {
        instance_id: replace(card, damage_marked=0)
        for instance_id, card in state.objects.items()
    }
    return replace(state, players=updated_players, objects=updated_objects)


def _untap_player_battlefield(state: GameState, player_id: str) -> GameState:
    current_state = state
    for instance_id in current_state.players[player_id].battlefield:
        card = current_state.objects[instance_id]
        if card.tapped:
            current_state = update_object(current_state, replace(card, tapped=False))
    return current_state
