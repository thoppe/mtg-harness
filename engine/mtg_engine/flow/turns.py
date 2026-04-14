from __future__ import annotations

from dataclasses import dataclass, replace

import re

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    AdvanceStepAction,
    CastCreatureSpellAction,
    CastNonCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
)
from mtg_engine.actions.validation import require_active_player, require_step
from mtg_engine.cards.repository import CardRepository
from mtg_engine.events.log import EventLog
from mtg_engine.state.models import GameState, TurnState
from mtg_engine.state.zones import move_object, move_object_to_top_of_library, update_object, update_player
from mtg_engine.rules.combat import apply_combat_damage, apply_state_based_actions, tap_attackers, with_combat_state

from .priority import can_block_attacker, enumerate_legal_actions
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
    if len(card_definition.produced_mana) != 1:
        raise ValueError("only single-color basic land mana generation is implemented")
    if source.tapped:
        raise ValueError("mana source is already tapped")

    mana_symbol = card_definition.produced_mana[0]
    updated_player = replace(player, mana_pool=player.mana_pool + (mana_symbol,))
    next_state = update_player(state, updated_player)
    next_state = update_object(next_state, replace(source, tapped=True))
    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="mana_added",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "source_instance_id": action.source_instance_id,
            "mana": [mana_symbol],
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

    mana_requirements = _parse_mana_cost(card_definition.mana_cost)
    if not _can_pay_mana_cost(player.mana_pool, mana_requirements):
        raise ValueError("insufficient mana to cast creature spell")

    remaining_pool = _pay_mana_cost(player.mana_pool, mana_requirements)
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


def cast_noncreature_spell(
    session: TurnResult | GameBootstrap,
    action: CastNonCreatureSpellAction,
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
    if card_definition.is_creature or card_definition.is_land:
        raise ValueError("spell must be a supported noncreature spell")
    effect = _supported_targeted_sorcery_effect(card_definition)
    if effect is None:
        raise ValueError("unsupported noncreature spell in v0")
    _require_legal_noncreature_target(
        state,
        card_repository,
        action.target_instance_ids,
        effect=effect,
    )

    mana_requirements = _parse_mana_cost(card_definition.mana_cost)
    if not _can_pay_mana_cost(player.mana_pool, mana_requirements):
        raise ValueError("insufficient mana to cast noncreature spell")

    remaining_pool = _pay_mana_cost(player.mana_pool, mana_requirements)
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
            "target_instance_ids": list(action.target_instance_ids),
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
    event_log.append(
        event_type="spell_resolved",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "card_instance_id": action.card_instance_id,
            "oracle_id": card.oracle_id,
            "target_instance_ids": list(action.target_instance_ids),
        },
    )
    resolved_state = casting_state
    if effect in {"destroy_tapped_creature", "destroy_creature_owner_gains_4_life", "destroy_target_land"}:
        if action.target_instance_id is None:
            raise ValueError("targeted sorcery requires a target")
        target = casting_state.objects[action.target_instance_id]
        resolved_state, destroyed_count = _destroy_permanents(
            casting_state,
            event_log,
            instance_ids=(action.target_instance_id,),
            active_player=action.player_id,
            reason=f"spell_effect:{card_definition.name}",
        )
        if destroyed_count != 1:
            raise ValueError("expected exactly one permanent to be destroyed")
        if effect == "destroy_creature_owner_gains_4_life":
            target_owner = resolved_state.players[target.owner_id]
            updated_owner = replace(target_owner, life_total=target_owner.life_total + 4)
            resolved_state = update_player(resolved_state, updated_owner)
            event_log.append(
                event_type="life_total_changed",
                active_player=action.player_id,
                payload={
                    "player_id": target.owner_id,
                    "life_total": updated_owner.life_total,
                },
            )
    elif effect == "destroy_two_target_lands":
        resolved_state, destroyed_count = _destroy_permanents(
            casting_state,
            event_log,
            instance_ids=action.target_instance_ids,
            active_player=action.player_id,
            reason=f"spell_effect:{card_definition.name}",
        )
        if destroyed_count != 2:
            raise ValueError("expected exactly two permanents to be destroyed")
    elif effect == "draw_two_cards":
        for _ in range(2):
            resolved_state = _draw_one_card_for_player_if_available(
                resolved_state,
                event_log,
                player_id=action.player_id,
            )
    elif effect == "gain_4_life":
        acting_player = resolved_state.players[action.player_id]
        updated_player = replace(acting_player, life_total=acting_player.life_total + 4)
        resolved_state = update_player(resolved_state, updated_player)
        event_log.append(
            event_type="life_total_changed",
            active_player=action.player_id,
            payload={
                "player_id": action.player_id,
                "life_total": updated_player.life_total,
            },
        )
    elif effect == "put_creature_on_top_of_library":
        if action.target_instance_id is None:
            raise ValueError("targeted sorcery requires a target")
        target = casting_state.objects[action.target_instance_id]
        resolved_state = move_object_to_top_of_library(
            casting_state,
            instance_id=action.target_instance_id,
            from_zone="battlefield",
            player_id=target.owner_id,
        )
        event_log.append(
            event_type="object_moved_between_zones",
            active_player=action.player_id,
            payload={
                "player_id": target.owner_id,
                "card_instance_id": action.target_instance_id,
                "oracle_id": target.oracle_id,
                "from_zone": "battlefield",
                "to_zone": "library",
                "library_position": "top",
            },
        )
    elif effect == "return_creature_to_hand_and_draw_one":
        if action.target_instance_id is None:
            raise ValueError("targeted sorcery requires a target")
        target = casting_state.objects[action.target_instance_id]
        resolved_state = move_object(
            casting_state,
            instance_id=action.target_instance_id,
            from_zone="battlefield",
            to_zone="hand",
            player_id=target.owner_id,
        )
        event_log.append(
            event_type="object_moved_between_zones",
            active_player=action.player_id,
            payload={
                "player_id": target.owner_id,
                "card_instance_id": action.target_instance_id,
                "oracle_id": target.oracle_id,
                "from_zone": "battlefield",
                "to_zone": "hand",
            },
        )
        resolved_state = _draw_one_card_for_player_if_available(
            resolved_state,
            event_log,
            player_id=action.player_id,
        )
    elif effect == "destroy_all_lands":
        land_ids = _battlefield_permanents_matching(
            casting_state,
            card_repository,
            predicate=lambda definition: definition.is_land,
        )
        resolved_state, _ = _destroy_permanents(
            casting_state,
            event_log,
            instance_ids=land_ids,
            active_player=action.player_id,
            reason=f"spell_effect:{card_definition.name}",
        )
    elif effect == "destroy_all_creatures":
        creature_ids = _battlefield_permanents_matching(
            casting_state,
            card_repository,
            predicate=lambda definition: definition.is_creature,
        )
        resolved_state, _ = _destroy_permanents(
            casting_state,
            event_log,
            instance_ids=creature_ids,
            active_player=action.player_id,
            reason=f"spell_effect:{card_definition.name}",
        )
    elif effect in {"damage_any_target", "damage_target_player"}:
        resolved_state, damage_events = _resolve_direct_damage_sorcery(
            casting_state,
            card_repository,
            action.target_instance_id,
            effect=effect,
            active_player=action.player_id,
        )
        for damage_event in damage_events:
            event_log.append(
                event_type=damage_event["event_type"],
                active_player=damage_event["active_player"],
                payload=damage_event["payload"],
            )
    elif effect == "target_player_discards_two":
        if action.target_instance_id is None:
            raise ValueError("targeted sorcery requires a target")
        resolved_state = _discard_first_cards_in_hand_order(
            casting_state,
            event_log,
            player_id=action.target_instance_id,
            count=2,
            active_player=action.player_id,
        )
    elif effect == "destroy_all_creatures_target_opponent_you_lose_2_per_creature":
        if action.target_instance_id is None:
            raise ValueError("targeted sorcery requires a target")
        creature_ids = tuple(
            instance_id
            for instance_id in casting_state.players[action.target_instance_id].battlefield
            if card_repository.get(casting_state.objects[instance_id].oracle_id).is_creature
        )
        resolved_state, destroyed_count = _destroy_permanents(
            casting_state,
            event_log,
            instance_ids=creature_ids,
            active_player=action.player_id,
            reason=f"spell_effect:{card_definition.name}",
        )
        if destroyed_count:
            acting_player = resolved_state.players[action.player_id]
            updated_player = replace(
                acting_player,
                life_total=acting_player.life_total - (destroyed_count * 2),
            )
            resolved_state = update_player(resolved_state, updated_player)
            event_log.append(
                event_type="life_total_changed",
                active_player=action.player_id,
                payload={
                    "player_id": action.player_id,
                    "life_total": updated_player.life_total,
                },
            )
    resolved_state = move_object(
        resolved_state,
        instance_id=action.card_instance_id,
        from_zone="stack",
        to_zone="graveyard",
        player_id=action.player_id,
    )
    event_log.append(
        event_type="object_moved_between_zones",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "card_instance_id": action.card_instance_id,
            "oracle_id": card.oracle_id,
            "from_zone": "stack",
            "to_zone": "graveyard",
        },
    )
    return TurnResult(state=resolved_state, event_log=event_log.events)


def advance_step(session: TurnResult | GameBootstrap, action: AdvanceStepAction) -> TurnResult:
    state = session.state
    require_active_player(state, action.player_id)
    require_step(state, "precombat_main_step")

    if action.to_step != "begin_combat_step":
        raise ValueError(f"unsupported step advancement in v0: {action.to_step}")

    return advance_to_begin_combat(session)


def pass_priority(
    session: TurnResult | GameBootstrap,
    action: PassPriorityAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    if state.turn.priority_player != action.player_id:
        raise ValueError("player does not have priority")
    require_step(state, "precombat_main_step")

    next_priority_player = _other_player(state, action.player_id)
    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="priority_passed",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "from_step": state.turn.step,
            "to_player": next_priority_player,
        },
    )

    passed_state = replace(state, turn=replace(state.turn, priority_player=next_priority_player))
    opposing_actions = enumerate_legal_actions(passed_state, card_repository)
    if opposing_actions:
        return TurnResult(state=passed_state, event_log=event_log.events)

    event_log.append(
        event_type="priority_passed",
        active_player=next_priority_player,
        payload={
            "player_id": next_priority_player,
            "from_step": state.turn.step,
            "to_player": state.turn.active_player,
        },
    )
    restored_state = replace(passed_state, turn=replace(passed_state.turn, priority_player=state.turn.active_player))
    return advance_to_begin_combat(TurnResult(state=restored_state, event_log=event_log.events))


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
        if attacker_card.has_defender:
            raise ValueError("creature with defender cannot attack")
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
    next_state = replace(
        next_state,
        turn=replace(
            next_state.turn,
            step="declare_blockers_step",
            priority_player=defending_player,
        ),
    )

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

    assigned_blockers: set[str] = set()
    for attacker_id, blocker_ids in action.blockers.items():
        if attacker_id not in state.combat.attackers:
            raise ValueError("blocker assignment references a non-attacking creature")
        for blocker_id in blocker_ids:
            if blocker_id in assigned_blockers:
                raise ValueError("a blocker may not block more than one attacker")
            if blocker_id not in state.players[action.player_id].battlefield:
                raise ValueError("blocker must be on defending player's battlefield")
            blocker = state.objects[blocker_id]
            blocker_card = card_repository.get(blocker.oracle_id)
            if not blocker_card.is_creature:
                raise ValueError("only creatures can block")
            if blocker.tapped:
                raise ValueError("tapped creature cannot block")
            if not can_block_attacker(
                state=state,
                card_repository=card_repository,
                blocker_id=blocker_id,
                attacker_id=attacker_id,
            ):
                raise ValueError("blocker cannot block the selected attacker")
            assigned_blockers.add(blocker_id)

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
    return _draw_one_card_for_player_if_available(
        state,
        event_log,
        player_id=state.turn.active_player,
    )


def _draw_one_card_for_player_if_available(
    state: GameState,
    event_log: EventLog,
    *,
    player_id: str,
) -> GameState:
    player = state.players[player_id]
    if not player.library:
        return state

    top_instance_id = player.library[0]
    card = state.objects[top_instance_id]
    next_state = move_object(
        state,
        instance_id=top_instance_id,
        from_zone="library",
        to_zone="hand",
        player_id=player_id,
    )
    event_log.append(
        event_type="object_moved_between_zones",
        active_player=state.turn.active_player,
        payload={
            "player_id": player_id,
            "card_instance_id": top_instance_id,
            "oracle_id": card.oracle_id,
            "from_zone": "library",
            "to_zone": "hand",
        },
    )
    return next_state


def _parse_mana_cost(mana_cost: str) -> dict[str, int]:
    requirements = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "generic": 0}
    if not mana_cost:
        return requirements
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for symbol in symbols:
        if symbol in {"W", "U", "B", "R", "G"}:
            requirements[symbol] += 1
        elif symbol.isdigit():
            requirements["generic"] += int(symbol)
        else:
            raise ValueError(f"unsupported mana symbol in v0: {symbol}")
    return requirements


def _can_pay_mana_cost(mana_pool: tuple[str, ...], requirements: dict[str, int]) -> bool:
    pool_counts = {symbol: mana_pool.count(symbol) for symbol in {"W", "U", "B", "R", "G"}}
    for symbol in {"W", "U", "B", "R", "G"}:
        if pool_counts[symbol] < requirements[symbol]:
            return False
        pool_counts[symbol] -= requirements[symbol]
    return sum(pool_counts.values()) >= requirements["generic"]


def _pay_mana_cost(mana_pool: tuple[str, ...], requirements: dict[str, int]) -> tuple[str, ...]:
    if not _can_pay_mana_cost(mana_pool, requirements):
        raise ValueError("insufficient mana to pay cost")

    remaining_pool = list(mana_pool)
    for symbol in {"W", "U", "B", "R", "G"}:
        for _ in range(requirements[symbol]):
            remaining_pool.remove(symbol)
    for _ in range(requirements["generic"]):
        remaining_pool.pop(0)
    return tuple(remaining_pool)


def _require_legal_noncreature_target(
    state: GameState,
    card_repository: CardRepository,
    target_instance_ids: tuple[str, ...],
    *,
    effect: str,
) -> None:
    if effect in {"draw_two_cards", "gain_4_life", "destroy_all_lands", "destroy_all_creatures"}:
        if target_instance_ids:
            raise ValueError("sorcery does not take a target")
        return
    if not target_instance_ids:
        raise ValueError("targeted sorcery requires a target")
    if effect == "destroy_two_target_lands":
        if len(target_instance_ids) != 2:
            raise ValueError("spell requires exactly two targets")
        if len(set(target_instance_ids)) != 2:
            raise ValueError("spell requires distinct targets")
        for target_instance_id in target_instance_ids:
            if target_instance_id not in state.objects:
                raise ValueError("target must exist")
            target = state.objects[target_instance_id]
            if target.zone != "battlefield":
                raise ValueError("target must be on the battlefield")
            target_definition = card_repository.get(target.oracle_id)
            if not target_definition.is_land:
                raise ValueError("target must be a land")
        return
    if len(target_instance_ids) != 1:
        raise ValueError("spell requires exactly one target")
    target_instance_id = target_instance_ids[0]
    if effect == "damage_target_player":
        if target_instance_id not in state.players:
            raise ValueError("target must be a player")
        return
    if effect == "target_player_discards_two":
        if target_instance_id not in state.players:
            raise ValueError("target must be a player")
        return
    if effect == "destroy_all_creatures_target_opponent_you_lose_2_per_creature":
        if target_instance_id not in state.players:
            raise ValueError("target must be a player")
        if target_instance_id == state.turn.active_player:
            raise ValueError("target must be an opponent")
        return
    if effect == "destroy_target_land":
        if target_instance_id not in state.objects:
            raise ValueError("target must exist")
        target = state.objects[target_instance_id]
        if target.zone != "battlefield":
            raise ValueError("target must be on the battlefield")
        target_definition = card_repository.get(target.oracle_id)
        if not target_definition.is_land:
            raise ValueError("target must be a land")
        return
    if effect == "return_creature_to_hand_and_draw_one":
        if target_instance_id not in state.objects:
            raise ValueError("target must exist")
        target = state.objects[target_instance_id]
        if target.zone != "battlefield":
            raise ValueError("target must be on the battlefield")
        target_definition = card_repository.get(target.oracle_id)
        if not target_definition.is_creature:
            raise ValueError("target must be a creature")
        return
    if effect == "damage_any_target":
        if target_instance_id in state.players:
            return
        if target_instance_id not in state.objects:
            raise ValueError("target must exist")
        target = state.objects[target_instance_id]
        if target.zone != "battlefield":
            raise ValueError("target creature must be on the battlefield")
        target_definition = card_repository.get(target.oracle_id)
        if not target_definition.is_creature:
            raise ValueError("target must be a creature or player")
        return
    if target_instance_id not in state.objects:
        raise ValueError("target must exist")
    target = state.objects[target_instance_id]
    if target.zone != "battlefield":
        raise ValueError("target must be on the battlefield")
    target_definition = card_repository.get(target.oracle_id)
    if not target_definition.is_creature:
        raise ValueError("target must be a creature")
    if effect == "destroy_tapped_creature" and not target.tapped:
        raise ValueError("target must be tapped")


def _supported_targeted_sorcery_effect(card_definition) -> str | None:
    if not card_definition.is_sorcery:
        return None
    if card_definition.oracle_text == "Destroy target tapped creature.":
        return "destroy_tapped_creature"
    if card_definition.oracle_text == "Destroy target creature. Its owner gains 4 life.":
        return "destroy_creature_owner_gains_4_life"
    if card_definition.oracle_text == "Draw two cards.":
        return "draw_two_cards"
    if card_definition.oracle_text == "You gain 4 life.":
        return "gain_4_life"
    if card_definition.oracle_text == "Put target creature on top of its owner's library.":
        return "put_creature_on_top_of_library"
    if card_definition.oracle_text == "Volcanic Hammer deals 3 damage to any target.":
        return "damage_any_target"
    if card_definition.oracle_text == "Lava Axe deals 5 damage to target player or planeswalker.":
        return "damage_target_player"
    if card_definition.oracle_text == "Target player discards two cards.":
        return "target_player_discards_two"
    if card_definition.oracle_text == "Destroy target land.":
        return "destroy_target_land"
    if card_definition.oracle_text == "Destroy two target lands.":
        return "destroy_two_target_lands"
    if card_definition.oracle_text == "Return target creature to its owner's hand.\nDraw a card.":
        return "return_creature_to_hand_and_draw_one"
    if card_definition.oracle_text == "Destroy all lands.":
        return "destroy_all_lands"
    if card_definition.oracle_text == "Destroy all creatures. They can't be regenerated.":
        return "destroy_all_creatures"
    if (
        card_definition.oracle_text
        == "Destroy all creatures target opponent controls. You lose 2 life for each creature destroyed this way."
    ):
        return "destroy_all_creatures_target_opponent_you_lose_2_per_creature"
    return None


def _battlefield_permanents_matching(
    state: GameState,
    card_repository: CardRepository,
    *,
    predicate,
) -> tuple[str, ...]:
    instance_ids: list[str] = []
    for player in state.players.values():
        for instance_id in player.battlefield:
            definition = card_repository.get(state.objects[instance_id].oracle_id)
            if predicate(definition):
                instance_ids.append(instance_id)
    return tuple(instance_ids)


def _destroy_permanents(
    state: GameState,
    event_log: EventLog,
    *,
    instance_ids: tuple[str, ...],
    active_player: str,
    reason: str,
) -> tuple[GameState, int]:
    current_state = state
    destroyed_count = 0
    for instance_id in instance_ids:
        if instance_id not in current_state.objects:
            continue
        permanent = current_state.objects[instance_id]
        if permanent.zone != "battlefield":
            continue
        current_state = move_object(
            current_state,
            instance_id=instance_id,
            from_zone="battlefield",
            to_zone="graveyard",
            player_id=permanent.owner_id,
        )
        destroyed_count += 1
        event_log.append(
            event_type="permanent_destroyed",
            active_player=active_player,
            payload={
                "card_instance_id": instance_id,
                "oracle_id": permanent.oracle_id,
                "reason": reason,
            },
        )
        event_log.append(
            event_type="object_moved_between_zones",
            active_player=active_player,
            payload={
                "player_id": permanent.owner_id,
                "card_instance_id": instance_id,
                "oracle_id": permanent.oracle_id,
                "from_zone": "battlefield",
                "to_zone": "graveyard",
            },
        )
    return current_state, destroyed_count


def _resolve_direct_damage_sorcery(
    state: GameState,
    card_repository: CardRepository,
    target_id: str | None,
    *,
    effect: str,
    active_player: str,
) -> tuple[GameState, list[dict]]:
    if target_id is None:
        raise ValueError("targeted sorcery requires a target")

    damage_amount = 3 if effect == "damage_any_target" else 5
    if target_id in state.players:
        target_player = state.players[target_id]
        updated_player = replace(target_player, life_total=target_player.life_total - damage_amount)
        next_state = update_player(state, updated_player)
        return next_state, [
            {
                "event_type": "damage_applied",
                "active_player": active_player,
                "payload": {
                    "target_player_id": target_id,
                    "damage": damage_amount,
                },
            },
            {
                "event_type": "life_total_changed",
                "active_player": active_player,
                "payload": {
                    "player_id": target_id,
                    "life_total": updated_player.life_total,
                },
            },
        ]

    target = state.objects[target_id]
    target_definition = card_repository.get(target.oracle_id)
    next_state = update_object(state, replace(target, damage_marked=target.damage_marked + damage_amount))
    events = [
        {
            "event_type": "damage_applied",
            "active_player": active_player,
            "payload": {
                "target_instance_id": target_id,
                "oracle_id": target.oracle_id,
                "damage": damage_amount,
                "new_damage_marked": target.damage_marked + damage_amount,
                "toughness": int(target_definition.toughness or "0"),
            },
        }
    ]
    next_state, sba_events = apply_state_based_actions(next_state, card_repository, active_player=active_player)
    events.extend(sba_events)
    return next_state, events


def _discard_first_cards_in_hand_order(
    state: GameState,
    event_log: EventLog,
    *,
    player_id: str,
    count: int,
    active_player: str,
) -> GameState:
    current_state = state
    discard_ids = current_state.players[player_id].hand[:count]
    for instance_id in discard_ids:
        discarded = current_state.objects[instance_id]
        current_state = move_object(
            current_state,
            instance_id=instance_id,
            from_zone="hand",
            to_zone="graveyard",
            player_id=player_id,
        )
        event_log.append(
            event_type="object_moved_between_zones",
            active_player=active_player,
            payload={
                "player_id": player_id,
                "card_instance_id": instance_id,
                "oracle_id": discarded.oracle_id,
                "from_zone": "hand",
                "to_zone": "graveyard",
            },
        )
    return current_state


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
