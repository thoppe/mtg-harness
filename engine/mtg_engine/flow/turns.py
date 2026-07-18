from __future__ import annotations

from dataclasses import dataclass, replace

import random

import re

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    ActivateAbilityAction,
    AdvanceStepAction,
    CastCreatureSpellAction,
    CastNonCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
    ResolveChoiceAction,
)
from mtg_engine.actions.validation import require_active_player, require_step
from mtg_engine.cards.repository import CardRepository
from mtg_engine.cards.implementations import effect_key_for
from mtg_engine.events.log import EventLog
from mtg_engine.state.models import DelayedTurnEffect, ExtraTurn, GameOutcome, GameState, PendingDecision, StackEntry, TurnState
from mtg_engine.state.models import TemporaryEffect
from mtg_engine.state.zones import move_object, move_object_to_top_of_library, update_object, update_player, zone_change_identity_payload
from mtg_engine.rules.combat import apply_combat_damage, apply_state_based_actions, queue_death_triggers, tap_attackers, with_combat_state
from mtg_engine.rules.characteristics import effective_power

from .priority import attacker_attack_rejection_reason, blocker_attack_rejection_reason, enumerate_legal_actions, instant_timing_is_legal
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
        # In a normal two-player game, the starting player skips their first
        # draw step.  We still expose the step in the trace so turn structure
        # remains explicit and deterministic.
        if next_step == "draw_step" and current_state.turn.turn_number != 1:
            current_state = _draw_one_card_if_available(current_state, event_log)

    return TurnResult(state=current_state, event_log=event_log.events)


def play_land(
    session: TurnResult | GameBootstrap,
    action: PlayLandAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    if state.turn.priority_player != action.player_id:
        raise ValueError("player does not have priority")

    player = state.players[action.player_id]
    if player.lands_played_this_turn >= player.land_play_limit_this_turn:
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
            **zone_change_identity_payload(next_state, action.card_instance_id),
        },
    )
    return TurnResult(state=next_state, event_log=event_log.events)


def activate_mana_ability(
    session: TurnResult | GameBootstrap,
    action: ActivateManaAbilityAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    if state.turn.priority_player != action.player_id:
        raise ValueError("player does not have priority")
    if state.turn.step not in {"precombat_main_step", "declare_attackers_step"}:
        raise ValueError("priority is not available in this step")

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
    next_state = replace(next_state, consecutive_passes=0)
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


def activate_ability(
    session: TurnResult | GameBootstrap,
    action: ActivateAbilityAction,
    card_repository: CardRepository,
) -> TurnResult:
    """Pay and stack the three bounded Wave 7 nonmana abilities."""
    state = session.state
    if state.turn.priority_player != action.player_id or state.turn.active_player != action.player_id or state.turn.step != "precombat_main_step":
        raise ValueError("activated ability requires your precombat-main priority")
    player = state.players[action.player_id]
    if action.source_instance_id not in player.battlefield:
        raise ValueError("ability source must be controlled on the battlefield")
    source = state.objects[action.source_instance_id]
    effect = effect_key_for(source.oracle_id)
    if effect not in {"capricious_sorcerer", "kings_assassin", "stern_marshal"}:
        raise ValueError("unsupported activated ability")
    if source.tapped or source.entered_battlefield_turn == state.turn.turn_number:
        raise ValueError("source must be untapped and controlled since turn start")
    _require_legal_noncreature_target(state, card_repository, action.target_instance_ids, effect=effect)
    next_state = update_object(state, replace(source, tapped=True))
    entry = StackEntry(card_instance_id=action.source_instance_id, controller_id=action.player_id,
                       target_ids=action.target_instance_ids, entry_kind="activated_ability",
                       source_object_id=source.object_id, source_oracle_id=source.oracle_id,
                       target_object_ids=tuple(next_state.objects[target].object_id for target in action.target_instance_ids if target in next_state.objects))
    next_state = replace(next_state, stack_entries=next_state.stack_entries + (entry,), consecutive_passes=0)
    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(event_type="activated_ability_activated", active_player=action.player_id,
                     payload={"player_id": action.player_id, "source_instance_id": action.source_instance_id,
                              "oracle_id": source.oracle_id, "target_instance_ids": list(action.target_instance_ids)})
    return TurnResult(state=next_state, event_log=event_log.events)


def cast_creature_spell(
    session: TurnResult | GameBootstrap,
    action: CastCreatureSpellAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    require_active_player(state, action.player_id)
    require_step(state, "precombat_main_step")
    if state.stack_entries:
        raise ValueError("creature spell requires an empty stack")

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
            **zone_change_identity_payload(casting_state, action.card_instance_id),
        },
    )

    stacked_state = _put_spell_on_stack(
        casting_state,
        card_instance_id=action.card_instance_id,
        controller_id=action.player_id,
    )
    return TurnResult(state=stacked_state, event_log=event_log.events)


def cast_noncreature_spell(
    session: TurnResult | GameBootstrap,
    action: CastNonCreatureSpellAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    if state.turn.priority_player != action.player_id:
        raise ValueError("player does not have priority")

    player = state.players[action.player_id]
    if action.card_instance_id not in player.hand:
        raise ValueError("spell must be in the active player's hand")

    card = state.objects[action.card_instance_id]
    card_definition = card_repository.get(card.oracle_id)
    if card_definition.is_creature or card_definition.is_land:
        raise ValueError("spell must be a supported noncreature spell")
    if card_definition.is_sorcery:
        require_active_player(state, action.player_id)
        require_step(state, "precombat_main_step")
        if state.stack_entries:
            raise ValueError("sorcery requires an empty stack")
    elif card_definition.is_instant:
        if not instant_timing_is_legal(state, card_definition, action.player_id):
            raise ValueError("instant timing is not legal")
    else:
        raise ValueError("spell must be a supported noncreature spell")
    effect = _supported_targeted_sorcery_effect(card_definition)
    if effect is None:
        raise ValueError("unsupported noncreature spell in v0")
    if effect == "mystic_denial":
        if len(action.target_instance_ids) != 1 or action.target_instance_ids[0] not in {entry.card_instance_id for entry in state.stack_entries}:
            raise ValueError("Mystic Denial requires a creature or sorcery spell on the stack")
        target_definition = card_repository.get(state.objects[action.target_instance_ids[0]].oracle_id)
        if not (target_definition.is_creature or target_definition.is_sorcery):
            raise ValueError("Mystic Denial targets a creature or sorcery spell")
    else:
        _require_legal_noncreature_target(
            state,
            card_repository,
            action.target_instance_ids,
            effect=effect,
        )
    if effect == "forked_lightning":
        _validate_forked_lightning_assignments(action)
    elif action.damage_assignments:
        raise ValueError("spell does not use damage assignments")

    if effect in {"prosperity", "blaze", "earthquake"} and action.chosen_x is None:
        raise ValueError("spell requires an explicit X declaration")
    if effect not in {"prosperity", "blaze", "earthquake"} and action.chosen_x not in (None, 0):
        raise ValueError("spell has no supported X declaration")
    mana_requirements = _parse_mana_cost(card_definition.mana_cost, chosen_x=action.chosen_x or 0)
    if not _can_pay_mana_cost(player.mana_pool, mana_requirements):
        raise ValueError("insufficient mana to cast noncreature spell")

    if effect in {"natural_order", "final_strike"}:
        sacrifice_id = action.additional_cost_instance_id
        if sacrifice_id is None or sacrifice_id not in player.battlefield:
            raise ValueError("spell requires sacrificing a creature")
        sacrifice = state.objects[sacrifice_id]
        sacrifice_definition = card_repository.get(sacrifice.oracle_id)
        if not sacrifice_definition.is_creature or (effect == "natural_order" and not sacrifice_definition.has_color("G")):
            raise ValueError("Natural Order requires sacrificing a green creature")
    elif action.additional_cost_instance_id is not None:
        raise ValueError("spell has no supported additional cost")

    remaining_pool = _pay_mana_cost(player.mana_pool, mana_requirements)
    casting_state = update_player(state, replace(player, mana_pool=remaining_pool))
    if effect in {"natural_order", "final_strike"}:
        sacrifice = casting_state.objects[action.additional_cost_instance_id]
        casting_state = move_object(
            casting_state,
            instance_id=action.additional_cost_instance_id,
            from_zone="battlefield",
            to_zone="graveyard",
            player_id=sacrifice.owner_id,
        )
    casting_state = move_object(
        casting_state,
        instance_id=action.card_instance_id,
        from_zone="hand",
        to_zone="stack",
        player_id=action.player_id,
    )

    event_log = EventLog.from_events(state.game_id, session.event_log)
    if effect in {"natural_order", "final_strike"}:
        event_log.append(
            event_type="object_moved_between_zones",
            active_player=action.player_id,
            payload={
                "player_id": action.player_id,
                "card_instance_id": action.additional_cost_instance_id,
                "oracle_id": sacrifice.oracle_id,
                "from_zone": "battlefield",
                "to_zone": "graveyard",
                "reason": f"additional_cost:{card_definition.name}",
                **zone_change_identity_payload(casting_state, action.additional_cost_instance_id),
            },
        )
    event_log.append(
        event_type="spell_cast",
        active_player=action.player_id,
        payload={
            "player_id": action.player_id,
            "card_instance_id": action.card_instance_id,
            "oracle_id": card.oracle_id,
            "mana_cost": card_definition.mana_cost,
            "target_instance_ids": list(action.target_instance_ids),
            "chosen_x": action.chosen_x,
            "damage_assignments": list(action.damage_assignments),
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
            **zone_change_identity_payload(casting_state, action.card_instance_id),
        },
    )
    stacked_state = _put_spell_on_stack(
        casting_state,
        card_instance_id=action.card_instance_id,
        controller_id=action.player_id,
        target_ids=action.target_instance_ids,
        chosen_x=action.chosen_x or 0,
        additional_cost_instance_id=action.additional_cost_instance_id,
        additional_cost_value=(effective_power(state, card_repository, action.additional_cost_instance_id) if effect == "final_strike" else None),
        damage_assignments=action.damage_assignments,
    )
    if effect in {"natural_order", "final_strike"}:
        stacked_state, trigger_events = queue_death_triggers(
            stacked_state,
            [{"card_instance_id": sacrifice.instance_id, "source_object_id": sacrifice.object_id, "owner_id": sacrifice.owner_id, "controller_id": sacrifice.controller_id, "oracle_id": sacrifice.oracle_id}],
            active_player=action.player_id,
        )
        for event in trigger_events:
            event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
    return TurnResult(state=stacked_state, event_log=event_log.events)


def _resolve_noncreature_spell(
    session: TurnResult,
    entry: StackEntry,
    card_repository: CardRepository,
) -> TurnResult:
    """Apply an already-cast sorcery's effect.

    Casting and resolution deliberately use separate transitions: target
    declarations live in the StackEntry until priority passes complete.
    """
    state = session.state
    card = state.objects[entry.card_instance_id]
    card_definition = card_repository.get(card.oracle_id)
    effect = _supported_targeted_sorcery_effect(card_definition)
    if effect is None:
        raise ValueError("unsupported noncreature spell in v0")
    action = CastNonCreatureSpellAction(
        player_id=entry.controller_id,
        card_instance_id=entry.card_instance_id,
        target_instance_ids=entry.target_ids,
        chosen_x=entry.chosen_x,
        additional_cost_instance_id=entry.additional_cost_instance_id,
        damage_assignments=entry.damage_assignments,
    )
    casting_state = state
    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="spell_resolved",
        active_player=entry.controller_id,
        payload={
            "player_id": entry.controller_id,
            "card_instance_id": entry.card_instance_id,
            "oracle_id": card.oracle_id,
            "target_instance_ids": list(entry.target_ids),
        },
    )
    resolved_state = casting_state
    # Wave 7 instants deliberately reuse the spell stack and the existing
    # temporary/damage helpers.  Their timing predicate is enforced at cast.
    if effect == "blessed_reversal":
        count = len(casting_state.combat.attackers) if casting_state.combat and casting_state.combat.defending_player == action.player_id else 0
        player = resolved_state.players[action.player_id]
        resolved_state = update_player(resolved_state, replace(player, life_total=player.life_total + 3 * count))
        event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": player.life_total + 3 * count})
    elif effect == "defiant_stand":
        target = resolved_state.objects[action.target_instance_id]
        resolved_state = update_object(resolved_state, replace(target, tapped=False))
        resolved_state = _add_temporary_effect(resolved_state, source_object_id=card.object_id, target_ids=(action.target_instance_id,), power_delta=1, toughness_delta=3)
    elif effect == "command_of_unsummoning":
        for target_id in action.target_instance_ids:
            if target_id in resolved_state.objects and resolved_state.objects[target_id].zone == "battlefield":
                target = resolved_state.objects[target_id]
                resolved_state = _move_with_event(resolved_state, event_log, instance_id=target_id, from_zone="battlefield", to_zone="hand", player_id=target.owner_id, active_player=action.player_id)
    elif effect == "scorching_winds":
        ids = tuple(casting_state.combat.attackers) if casting_state.combat and casting_state.combat.defending_player == action.player_id else ()
        resolved_state, events = _damage_creatures_once(resolved_state, card_repository, ids, 1, action.player_id)
        for event in events: event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
    elif effect == "deep_wood":
        resolved_state = replace(resolved_state, delayed_turn_effects=resolved_state.delayed_turn_effects + (DelayedTurnEffect(kind="prevent_attacking_damage", player_id=action.player_id, turn_number=resolved_state.turn.turn_number, source_player_id=action.player_id),))
    elif effect == "harsh_justice":
        resolved_state = replace(resolved_state, delayed_turn_effects=resolved_state.delayed_turn_effects + (DelayedTurnEffect(kind="retaliate_attacking_damage", player_id=action.player_id, turn_number=resolved_state.turn.turn_number, source_player_id=action.player_id),))
    elif effect == "assassins_blade":
        resolved_state, _ = _destroy_permanents(resolved_state, event_log, instance_ids=action.target_instance_ids, active_player=action.player_id, reason="spell_effect:Assassin's Blade")
    elif effect == "mystic_denial":
        target_id = action.target_instance_id
        target_entry = next((item for item in resolved_state.stack_entries if item.card_instance_id == target_id), None)
        if target_entry is not None:
            target = resolved_state.objects[target_id]
            resolved_state = move_object(resolved_state, instance_id=target_id, from_zone="stack", to_zone="graveyard", player_id=target.owner_id)
            resolved_state = replace(resolved_state, stack_entries=tuple(item for item in resolved_state.stack_entries if item is not target_entry))
            event_log.append(event_type="spell_countered", active_player=action.player_id, payload={"card_instance_id": target_id, "oracle_id": target.oracle_id, "reason": "Mystic Denial"})
    if effect in {
        "destroy_tapped_creature",
        "destroy_creature_owner_gains_4_life",
        "destroy_nonblack_creature",
        "destroy_target_land",
        "destroy_target_creature_or_land",
    }:
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
    elif effect in {"destroy_two_target_lands", "wicked_pact"}:
        resolved_state, destroyed_count = _destroy_permanents(
            casting_state,
            event_log,
            instance_ids=action.target_instance_ids,
            active_player=action.player_id,
            reason=f"spell_effect:{card_definition.name}",
        )
        if destroyed_count != (1 if effect == "wicked_pact" else 2):
            raise ValueError("expected exactly two permanents to be destroyed")
        if effect == "wicked_pact":
            player = resolved_state.players[action.player_id]
            resolved_state = update_player(resolved_state, replace(player, life_total=player.life_total - 5))
            event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": player.life_total - 5})
            resolved_state, sba_events = apply_state_based_actions(resolved_state, card_repository, active_player=action.player_id)
            for item in sba_events: event_log.append(event_type=item["event_type"], active_player=item["active_player"], payload=item["payload"])
    elif effect == "draw_two_cards":
        for _ in range(2):
            resolved_state = _draw_one_card_for_player_if_available(
                resolved_state,
                event_log,
                player_id=action.player_id,
            )
    elif effect == "look_at_opponent_hand_draw_one":
        target_player_id = action.target_instance_id
        event_log.append(
            event_type="hand_looked_at",
            active_player=action.player_id,
            payload={"viewer_id": action.player_id, "player_id": target_player_id, "count": len(resolved_state.players[target_player_id].hand)},
        )
        resolved_state = _draw_one_card_for_player_if_available(resolved_state, event_log, player_id=action.player_id)
    elif effect in {"baleful_stare", "withering_gaze"}:
        target_player_id = action.target_instance_id
        hand = resolved_state.players[target_player_id].hand
        event_log.append(
            event_type="hand_revealed",
            active_player=action.player_id,
            payload={"player_id": target_player_id, "card_instance_ids": list(hand), "oracle_ids": [resolved_state.objects[instance_id].oracle_id for instance_id in hand]},
        )
        subtype, color = ("Mountain", "R") if effect == "baleful_stare" else ("Forest", "G")
        draw_count = sum(
            int((definition := card_repository.get(resolved_state.objects[instance_id].oracle_id)).has_subtype(subtype))
            + int(definition.has_color(color))
            for instance_id in hand
        )
        for _ in range(draw_count):
            resolved_state = _draw_one_card_for_player_if_available(resolved_state, event_log, player_id=action.player_id)
    elif effect == "balance_of_power":
        target_player_id = action.target_instance_id
        draw_count = max(0, len(resolved_state.players[target_player_id].hand) - len(resolved_state.players[action.player_id].hand))
        for _ in range(draw_count):
            resolved_state = _draw_one_card_for_player_if_available(resolved_state, event_log, player_id=action.player_id)
    elif effect == "starlight":
        target_player_id = action.target_instance_id
        black_creatures = sum(
            1 for instance_id in resolved_state.players[target_player_id].battlefield
            if (definition := card_repository.get(resolved_state.objects[instance_id].oracle_id)).is_creature and definition.has_color("B")
        )
        player = resolved_state.players[action.player_id]
        updated = replace(player, life_total=player.life_total + black_creatures * 3)
        resolved_state = update_player(resolved_state, updated)
        event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": updated.life_total})
    elif effect == "cruel_bargain":
        for _ in range(4):
            resolved_state = _draw_one_card_for_player_if_available(resolved_state, event_log, player_id=action.player_id)
        player = resolved_state.players[action.player_id]
        updated = replace(player, life_total=player.life_total - ((player.life_total + 1) // 2))
        resolved_state = update_player(resolved_state, updated)
        event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": updated.life_total})
        resolved_state, sba_events = apply_state_based_actions(resolved_state, card_repository, active_player=action.player_id)
        for event in sba_events:
            event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
    elif effect == "prosperity":
        for player_id in _resolution_player_order(resolved_state):
            for _ in range(action.chosen_x):
                resolved_state = _draw_one_card_for_player_if_available(resolved_state, event_log, player_id=player_id)
    elif effect in {"exhaustion", "false_peace", "taunt"}:
        target_player_id = action.target_instance_id
        kind = {"exhaustion": "prevent_untap", "false_peace": "skip_combat", "taunt": "must_attack_source"}[effect]
        delayed = DelayedTurnEffect(kind=kind, player_id=target_player_id, turn_number=resolved_state.turn.turn_number + 1, source_player_id=action.player_id)
        resolved_state = replace(resolved_state, delayed_turn_effects=resolved_state.delayed_turn_effects + (delayed,))
        event_log.append(event_type="delayed_turn_effect_created", active_player=action.player_id, payload={"kind": kind, "player_id": target_player_id, "source_player_id": action.player_id})
    elif effect == "last_chance":
        resolved_state = replace(resolved_state, extra_turns=resolved_state.extra_turns + (ExtraTurn(player_id=action.player_id, lose_at_end_step=True),))
        event_log.append(event_type="extra_turn_scheduled", active_player=action.player_id, payload={"player_id": action.player_id, "lose_at_end_step": True})
    elif effect == "mind_knives":
        target_player_id = action.target_instance_id
        hand = resolved_state.players[target_player_id].hand
        if hand:
            selected_id = random.Random(resolved_state.rng_seed + resolved_state.rng_cursor).choice(hand)
            resolved_state = _discard_specific_cards(resolved_state, event_log, player_id=target_player_id, instance_ids=(selected_id,), active_player=action.player_id)
            resolved_state = replace(resolved_state, rng_cursor=resolved_state.rng_cursor + 1)
            event_log.append(event_type="random_choice_resolved", active_player=action.player_id, payload={"player_id": target_player_id, "algorithm": "python_random_mt19937_v1", "rng_cursor_before": resolved_state.rng_cursor - 1, "rng_cursor_after": resolved_state.rng_cursor})
    elif effect == "flux":
        players = _resolution_player_order(resolved_state)
        resolved_state = _queue_wave5_decision(resolved_state, event_log, chooser_id=players[0], source_object_id=card.object_id, kind="discard_any_number", option_ids=resolved_state.players[players[0]].hand, min_selections=0, max_selections=len(resolved_state.players[players[0]].hand), continuation_kind="wave5_discard_then_draw", continuation=(("remaining_players", players[1:]), ("draw_counts", ()), ("caster_id", action.player_id)))
    elif effect == "temporary_truce":
        players = _resolution_player_order(resolved_state)
        resolved_state = _queue_wave5_decision(resolved_state, event_log, chooser_id=players[0], source_object_id=card.object_id, kind="draw_up_to_two", option_ids=(), min_selections=0, max_selections=0, continuation_kind="wave5_truce", continuation=(("remaining_players", players[1:]),))
    elif effect == "ancestral_memories":
        options = resolved_state.players[action.player_id].library[:7]
        count = min(2, len(options))
        resolved_state = _queue_wave5_decision(resolved_state, event_log, chooser_id=action.player_id, source_object_id=card.object_id, kind="choose_two_from_library_prefix", option_ids=options, min_selections=count, max_selections=count, continuation_kind="wave5_ancestral_memories")
    elif effect == "omen":
        options = resolved_state.players[action.player_id].library[:3]
        resolved_state = _queue_wave5_decision(resolved_state, event_log, chooser_id=action.player_id, source_object_id=card.object_id, kind="order_library_prefix_and_may_shuffle", option_ids=options, min_selections=len(options), max_selections=len(options), selection_ordered=True, allow_shuffle=True, continuation_kind="wave5_order_library", continuation=(("draw_after", True),))
    elif effect == "cruel_fate":
        target_player_id = action.target_instance_id
        options = resolved_state.players[target_player_id].library[:5]
        if options:
            resolved_state = _queue_wave5_decision(resolved_state, event_log, chooser_id=action.player_id, source_object_id=card.object_id, kind="choose_library_card_for_graveyard", option_ids=options, min_selections=1, max_selections=1, continuation_kind="wave5_cruel_fate_select", continuation=(("target_player_id", target_player_id),))
    elif effect in {"natural_order", "untamed_wilds", "natures_lore", "gift_of_estates", "cruel_tutor"}:
        predicate = {
            "natural_order": lambda definition: definition.is_creature and definition.has_color("G"),
            "untamed_wilds": lambda definition: definition.is_land and "Basic" in definition.type_line,
            "natures_lore": lambda definition: definition.is_land and definition.has_subtype("Forest"),
            "gift_of_estates": lambda definition: definition.is_land and definition.has_subtype("Plains"),
            "cruel_tutor": lambda definition: True,
        }[effect]
        gift_condition_is_met = any(
            sum(1 for instance_id in player.battlefield if card_repository.get(resolved_state.objects[instance_id].oracle_id).is_land)
            > sum(1 for instance_id in resolved_state.players[action.player_id].battlefield if card_repository.get(resolved_state.objects[instance_id].oracle_id).is_land)
            for player_id, player in resolved_state.players.items() if player_id != action.player_id
        )
        if effect != "gift_of_estates" or gift_condition_is_met:
            options = tuple(instance_id for instance_id in resolved_state.players[action.player_id].library if predicate(card_repository.get(resolved_state.objects[instance_id].oracle_id)))
            max_count = 3 if effect == "gift_of_estates" else 1
            min_count = 0 if effect != "cruel_tutor" or not options else 1
            destination = "hand" if effect == "gift_of_estates" else ("battlefield" if effect != "cruel_tutor" else "library")
            resolved_state = _queue_wave5_decision(resolved_state, event_log, chooser_id=action.player_id, source_object_id=card.object_id, kind=f"search_{effect}", option_ids=options, min_selections=min_count, max_selections=min(max_count, len(options)), continuation_kind=f"wave5_search_{effect}", continuation=(("destination", destination), ("shuffle", True), ("top_after_shuffle", effect == "cruel_tutor"), ("lose_life", 2 if effect == "cruel_tutor" else 0), ("reveal_selection", effect == "gift_of_estates")))
    elif effect == "winds_of_change":
        draw_counts = tuple((player_id, len(resolved_state.players[player_id].hand)) for player_id in _resolution_player_order(resolved_state))
        for player_id, _ in draw_counts:
            player = resolved_state.players[player_id]
            for instance_id in tuple(player.hand):
                resolved_state = _move_with_event(resolved_state, event_log, instance_id=instance_id, from_zone="hand", to_zone="library", player_id=player_id, active_player=action.player_id)
            resolved_state = _shuffle_library(resolved_state, event_log, player_id=player_id)
        for player_id, count in draw_counts:
            for _ in range(count):
                resolved_state = _draw_one_card_for_player_if_available(resolved_state, event_log, player_id=player_id)
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
    elif effect == "target_player_gains_8_life":
        target_player = resolved_state.players[action.target_instance_id]
        updated_player = replace(target_player, life_total=target_player.life_total + 8)
        resolved_state = update_player(resolved_state, updated_player)
        event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.target_instance_id, "life_total": updated_player.life_total})
    elif effect in {"return_target_creature_card_from_your_graveyard", "return_target_card_from_your_graveyard", "return_target_sorcery_card_from_your_graveyard"}:
        target = casting_state.objects[action.target_instance_id]
        resolved_state = move_object(casting_state, instance_id=action.target_instance_id, from_zone="graveyard", to_zone="hand", player_id=action.player_id)
        event_log.append(event_type="object_moved_between_zones", active_player=action.player_id, payload={"player_id": action.player_id, "card_instance_id": action.target_instance_id, "oracle_id": target.oracle_id, "from_zone": "graveyard", "to_zone": "hand", **zone_change_identity_payload(resolved_state, action.target_instance_id)})
    elif effect == "return_target_creature_card_from_your_graveyard_to_battlefield":
        target = casting_state.objects[action.target_instance_id]
        resolved_state = move_object(
            casting_state,
            instance_id=action.target_instance_id,
            from_zone="graveyard",
            to_zone="battlefield",
            player_id=action.player_id,
        )
        event_log.append(
            event_type="object_moved_between_zones",
            active_player=action.player_id,
            payload={
                "player_id": action.player_id,
                "card_instance_id": action.target_instance_id,
                "oracle_id": target.oracle_id,
                "from_zone": "graveyard",
                "to_zone": "battlefield",
                **zone_change_identity_payload(resolved_state, action.target_instance_id),
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
                **zone_change_identity_payload(resolved_state, action.target_instance_id),
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
                **zone_change_identity_payload(resolved_state, action.target_instance_id),
            },
        )
        resolved_state = _draw_one_card_for_player_if_available(
            resolved_state,
            event_log,
            player_id=action.player_id,
        )
    elif effect == "tap_up_to_three_nonflying_creatures":
        for target_instance_id in action.target_instance_ids:
            target = resolved_state.objects[target_instance_id]
            if target.tapped:
                continue
            resolved_state = update_object(resolved_state, replace(target, tapped=True))
            event_log.append(
                event_type="permanent_tapped",
                active_player=action.player_id,
                payload={
                    "player_id": target.controller_id,
                    "card_instance_id": target_instance_id,
                    "oracle_id": target.oracle_id,
                    "source_instance_id": action.card_instance_id,
                    "reason": f"spell_effect:{card_definition.name}",
                },
            )
    elif effect == "devastation":
        ids = _battlefield_permanents_matching(casting_state, card_repository, predicate=lambda definition: definition.is_creature or definition.is_land)
        resolved_state, _ = _destroy_permanents(casting_state, event_log, instance_ids=ids, active_player=action.player_id, reason=f"spell_effect:{card_definition.name}")
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
    elif effect in {"destroy_all_green_creatures", "destroy_all_white_creatures", "destroy_all_islands", "destroy_all_plains"}:
        if effect in {"destroy_all_green_creatures", "destroy_all_white_creatures"}:
            color = "G" if effect == "destroy_all_green_creatures" else "W"
            predicate = lambda definition: definition.is_creature and definition.has_color(color)
        else:
            subtype = "Island" if effect == "destroy_all_islands" else "Plains"
            predicate = lambda definition: definition.is_land and definition.has_subtype(subtype)
        ids = _battlefield_permanents_matching(casting_state, card_repository, predicate=predicate)
        resolved_state, _ = _destroy_permanents(casting_state, event_log, instance_ids=ids, active_player=action.player_id, reason=f"spell_effect:{card_definition.name}")
    elif effect in {"damage_any_target", "damage_target_player", "damage_any_target_1", "damage_any_target_2", "blaze"}:
        resolved_state, damage_events = _resolve_direct_damage_sorcery(
            casting_state,
            card_repository,
            action.target_instance_id,
            effect="damage_any_target_variable" if effect == "blaze" else effect,
            active_player=action.player_id,
            damage_override=action.chosen_x if effect == "blaze" else None,
        )
        for damage_event in damage_events:
            event_log.append(
                event_type=damage_event["event_type"],
                active_player=damage_event["active_player"],
                payload=damage_event["payload"],
            )
    elif effect == "damage_nonblack_creature_3_gain_3":
        resolved_state, events = _resolve_direct_damage_sorcery(casting_state, card_repository, action.target_instance_id, effect="damage_nonblack_creature_3", active_player=action.player_id)
        for event in events: event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
        player = resolved_state.players[action.player_id]; resolved_state = update_player(resolved_state, replace(player, life_total=player.life_total + 3)); event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": player.life_total + 3})
    elif effect == "final_strike":
        resolved_state, events = _resolve_direct_damage_sorcery(casting_state, card_repository, action.target_instance_id, effect="damage_any_target_variable", active_player=action.player_id, damage_override=entry.additional_cost_value or 0)
        for event in events: event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
    elif effect == "forked_lightning":
        resolved_state, events = _damage_assignments_once(casting_state, card_repository, action.damage_assignments, action.player_id)
        for event in events: event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
    elif effect == "earthquake":
        ids = _battlefield_permanents_matching(casting_state, card_repository, predicate=lambda definition: definition.is_creature and not definition.has_flying)
        resolved_state, events = _damage_creatures_once(casting_state, card_repository, ids, action.chosen_x, action.player_id, check_sbas=False)
        for player_id, player in resolved_state.players.items():
            updated = replace(player, life_total=player.life_total - action.chosen_x)
            resolved_state = update_player(resolved_state, updated)
            events.append({"event_type": "life_total_changed", "active_player": action.player_id, "payload": {"player_id": player_id, "life_total": updated.life_total}})
        resolved_state, sba_events = apply_state_based_actions(resolved_state, card_repository, active_player=action.player_id)
        events.extend(sba_events)
        for event in events: event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
    elif effect == "damage_target_opponent_2_gain_2":
        resolved_state, events = _resolve_direct_damage_sorcery(casting_state, card_repository, action.target_instance_id, effect="damage_target_opponent_2", active_player=action.player_id)
        for event in events: event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
        player = resolved_state.players[action.player_id]; resolved_state = update_player(resolved_state, replace(player, life_total=player.life_total + 2)); event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": player.life_total + 2})
    elif effect == "damage_target_creature_per_mountain":
        damage = _controlled_land_subtype_count(casting_state, card_repository, action.player_id, "Mountain")
        resolved_state, events = _resolve_direct_damage_sorcery(
            casting_state,
            card_repository,
            action.target_instance_id,
            effect="damage_target_creature_variable",
            active_player=action.player_id,
            damage_override=damage,
        )
        for event in events: event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
    elif effect == "gain_life_per_forest":
        player = resolved_state.players[action.player_id]
        forest_count = _battlefield_land_subtype_count(resolved_state, card_repository, "Forest")
        total = player.life_total + forest_count
        resolved_state = update_player(resolved_state, replace(player, life_total=total))
        event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": total})
    elif effect == "gain_life_per_opponent_mountain":
        target_player_id = action.target_instance_id
        mountain_count = _controlled_land_subtype_count(
            resolved_state,
            card_repository,
            target_player_id,
            "Mountain",
        )
        player = resolved_state.players[action.player_id]
        total = player.life_total + (mountain_count * 2)
        resolved_state = update_player(resolved_state, replace(player, life_total=total))
        event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": total})
    elif effect == "draw_per_tapped_creature_target_opponent_controls":
        target_player_id = action.target_instance_id
        draw_count = sum(
            1
            for instance_id in resolved_state.players[target_player_id].battlefield
            if (
                (definition := card_repository.get(resolved_state.objects[instance_id].oracle_id)).is_creature
                and resolved_state.objects[instance_id].tapped
            )
        )
        for _ in range(draw_count):
            resolved_state = _draw_one_card_for_player_if_available(
                resolved_state,
                event_log,
                player_id=action.player_id,
            )
    elif effect == "damage_any_target_4_gain_4":
        resolved_state, events = _resolve_direct_damage_sorcery(
            casting_state,
            card_repository,
            action.target_instance_id,
            effect="damage_any_target_variable",
            active_player=action.player_id,
            damage_override=4,
        )
        for event in events:
            event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
        player = resolved_state.players[action.player_id]
        total = player.life_total + 4
        resolved_state = update_player(resolved_state, replace(player, life_total=total))
        event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": total})
    elif effect in {"tutor_sorcery_to_top", "tutor_creature_to_top"}:
        selected_card_type = "sorcery" if effect == "tutor_sorcery_to_top" else "creature"
        options = tuple(
            instance_id
            for instance_id in resolved_state.players[action.player_id].library
            if getattr(card_repository.get(resolved_state.objects[instance_id].oracle_id), f"is_{selected_card_type}")
        )
        resolved_state = replace(
            resolved_state,
            pending_decision=PendingDecision(
                decision_id=f"{card.object_id}:tutor",
                chooser_id=action.player_id,
                kind="tutor_to_top_after_shuffle",
                source_object_id=card.object_id,
                option_ids=options,
                selected_card_type=selected_card_type,
                min_selections=0 if not options else 1,
            ),
        )
        event_log.append(
            event_type="choice_requested",
            active_player=action.player_id,
            payload={"decision_id": f"{card.object_id}:tutor", "chooser_id": action.player_id, "kind": "tutor_to_top_after_shuffle", "option_count": len(options)},
        )
    elif effect == "additional_three_land_plays":
        player = resolved_state.players[action.player_id]
        resolved_state = update_player(
            resolved_state,
            replace(player, land_play_limit_this_turn=player.land_play_limit_this_turn + 3),
        )
        event_log.append(event_type="land_play_allowance_changed", active_player=action.player_id, payload={"player_id": action.player_id, "land_play_limit_this_turn": player.land_play_limit_this_turn + 3})
    elif effect == "all_able_creatures_block_target_this_turn":
        target = resolved_state.objects[action.target_instance_id]
        resolved_state = replace(resolved_state, forced_block_target_object_id=target.object_id)
        event_log.append(event_type="combat_requirement_created", active_player=action.player_id, payload={"target_object_id": target.object_id, "requirement": "all_able_creatures_block"})
    elif effect == "target_creature_gets_3_3_and_flying_until_end_of_turn":
        resolved_state = _add_temporary_effect(resolved_state, source_object_id=card.object_id, target_ids=(action.target_instance_id,), power_delta=3, toughness_delta=3, keywords=("Flying",))
    elif effect == "target_creature_gains_flying_and_draw_one":
        resolved_state = _add_temporary_effect(resolved_state, source_object_id=card.object_id, target_ids=(action.target_instance_id,), keywords=("Flying",))
        resolved_state = _draw_one_card_for_player_if_available(resolved_state, event_log, player_id=action.player_id)
    elif effect in {"controlled_creatures_get_0_3_until_end_of_turn", "controlled_creatures_get_1_1_until_end_of_turn", "white_creatures_get_2_0_until_end_of_turn", "green_controlled_creatures_gain_forestwalk_until_end_of_turn", "black_controlled_creatures_only_blockable_by_black_until_end_of_turn", "controlled_creatures_gain_reach_until_end_of_turn"}:
        candidate_ids = (
            tuple(
                instance_id
                for player in resolved_state.players.values()
                for instance_id in player.battlefield
            )
            if effect == "white_creatures_get_2_0_until_end_of_turn"
            else resolved_state.players[action.player_id].battlefield
        )
        affected_ids = tuple(
            instance_id for instance_id in candidate_ids
            if card_repository.get(resolved_state.objects[instance_id].oracle_id).is_creature
            and (effect != "white_creatures_get_2_0_until_end_of_turn" or card_repository.get(resolved_state.objects[instance_id].oracle_id).has_color("W"))
            and (effect != "green_controlled_creatures_gain_forestwalk_until_end_of_turn" or card_repository.get(resolved_state.objects[instance_id].oracle_id).has_color("G"))
            and (effect != "black_controlled_creatures_only_blockable_by_black_until_end_of_turn" or card_repository.get(resolved_state.objects[instance_id].oracle_id).has_color("B"))
        )
        modifiers = {
            "controlled_creatures_get_0_3_until_end_of_turn": (0, 3, (), ()),
            "controlled_creatures_get_1_1_until_end_of_turn": (1, 1, (), ()),
            "white_creatures_get_2_0_until_end_of_turn": (2, 0, (), ()),
            "green_controlled_creatures_gain_forestwalk_until_end_of_turn": (0, 0, ("Forestwalk",), ()),
            "black_controlled_creatures_only_blockable_by_black_until_end_of_turn": (0, 0, (), ("B",)),
            "controlled_creatures_gain_reach_until_end_of_turn": (0, 0, ("Reach",), ()),
        }
        power, toughness, keywords, colors = modifiers[effect]
        resolved_state = _add_temporary_effect(resolved_state, source_object_id=card.object_id, target_ids=affected_ids, power_delta=power, toughness_delta=toughness, keywords=keywords, only_blockable_by_colors=colors)
    elif effect == "target_creature_gets_4_power_until_end_of_turn":
        target = resolved_state.objects[action.target_instance_id]
        resolved_state = update_object(resolved_state, replace(target, temporary_power_bonus=target.temporary_power_bonus + 4))
    elif effect == "target_creature_gets_4_4_until_end_of_turn":
        target = resolved_state.objects[action.target_instance_id]
        resolved_state = update_object(resolved_state, replace(target, temporary_power_bonus=target.temporary_power_bonus + 4, temporary_toughness_bonus=target.temporary_toughness_bonus + 4))
    elif effect == "target_creature_gets_2_power_and_takes_2":
        target = resolved_state.objects[action.target_instance_id]
        resolved_state = update_object(resolved_state, replace(target, temporary_power_bonus=target.temporary_power_bonus + 2, damage_marked=target.damage_marked + 2))
        resolved_state, sba_events = apply_state_based_actions(resolved_state, card_repository, active_player=action.player_id)
        for event in sba_events: event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
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
    elif effect in {"untap_all_creatures_you_control", "tap_all_nonwhite_creatures"}:
        for player_id, player in resolved_state.players.items():
            for instance_id in player.battlefield:
                obj = resolved_state.objects[instance_id]
                definition = card_repository.get(obj.oracle_id)
                applies = definition.is_creature and (
                    (effect == "untap_all_creatures_you_control" and player_id == action.player_id)
                    or (effect == "tap_all_nonwhite_creatures" and not definition.has_color("W"))
                )
                if not applies:
                    continue
                desired_tapped = effect == "tap_all_nonwhite_creatures"
                if obj.tapped == desired_tapped:
                    continue
                resolved_state = update_object(resolved_state, replace(obj, tapped=desired_tapped))
                event_log.append(event_type="permanent_tapped" if desired_tapped else "permanent_untapped", active_player=action.player_id, payload={"card_instance_id": instance_id, "oracle_id": obj.oracle_id, "reason": f"spell_effect:{card_definition.name}"})
    elif effect in {"damage_all_creatures_2", "damage_all_flying_creatures_4"}:
        damage = 2 if effect == "damage_all_creatures_2" else 4
        targets = _battlefield_permanents_matching(casting_state, card_repository, predicate=lambda definition: definition.is_creature and (effect == "damage_all_creatures_2" or definition.has_flying))
        resolved_state, damage_events = _damage_creatures_once(casting_state, card_repository, targets, damage, action.player_id)
        for damage_event in damage_events:
            event_log.append(event_type=damage_event["event_type"], active_player=damage_event["active_player"], payload=damage_event["payload"])
    elif effect in {"damage_all_creatures_and_players_1", "damage_all_creatures_and_players_6", "damage_all_flying_creatures_and_players_x"}:
        damage = action.chosen_x if effect.endswith("_x") else (1 if effect.endswith("_1") else 6)
        targets = _battlefield_permanents_matching(casting_state, card_repository, predicate=lambda definition: definition.is_creature and (effect != "damage_all_flying_creatures_and_players_x" or definition.has_flying))
        resolved_state, events = _damage_creatures_once(casting_state, card_repository, targets, damage, action.player_id, check_sbas=False)
        for player_id, player in resolved_state.players.items():
            updated = replace(player, life_total=player.life_total - damage)
            resolved_state = update_player(resolved_state, updated)
            events.append({"event_type": "life_total_changed", "active_player": action.player_id, "payload": {"player_id": player_id, "life_total": updated.life_total}})
        resolved_state, sba_events = apply_state_based_actions(resolved_state, card_repository, active_player=action.player_id)
        events.extend(sba_events)
        for event in events:
            event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
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
            **zone_change_identity_payload(resolved_state, action.card_instance_id),
        },
    )
    return TurnResult(state=resolved_state, event_log=event_log.events)


def resolve_pending_choice(
    session: TurnResult,
    action: ResolveChoiceAction,
    card_repository: CardRepository,
) -> TurnResult:
    state = session.state
    decision = state.pending_decision
    if decision is None:
        raise ValueError("no pending decision")
    if action.player_id != decision.chooser_id or action.decision_id != decision.decision_id:
        raise ValueError("choice does not match pending decision")
    selected_ids = action.ordered_instance_ids if decision.selection_ordered else action.selected_instance_ids
    if len(selected_ids) < decision.min_selections or len(selected_ids) > decision.max_selections:
        raise ValueError("selection count is outside the declared bounds")
    if any(instance_id not in decision.option_ids for instance_id in selected_ids):
        raise ValueError("selected card is not a legal option")
    if len(set(selected_ids)) != len(selected_ids):
        raise ValueError("selected cards must be distinct")
    if decision.selection_ordered and len(selected_ids) != len(decision.option_ids):
        raise ValueError("ordered choice must arrange every offered card")
    if decision.allow_shuffle and action.shuffle_library is None:
        raise ValueError("shuffle choice must be explicit")
    if not decision.allow_shuffle and action.shuffle_library is not None:
        raise ValueError("shuffle declaration is not legal for this choice")

    event_log = EventLog.from_events(state.game_id, session.event_log)
    next_state = replace(state, pending_decision=None)
    choice_payload = {
        "decision_id": decision.decision_id,
        "selected_count": len(action.selected_instance_ids),
        "ordered_count": len(action.ordered_instance_ids),
        "declared_count": action.declared_count,
        "choice_boolean": action.choice_boolean,
        "shuffle_library": action.shuffle_library,
    }
    if decision.continuation_kind is None:
        choice_payload["selected_instance_id"] = action.selected_instance_id
    event_log.append(event_type="choice_resolved", active_player=action.player_id, payload=choice_payload)
    context = dict(decision.continuation)

    expected_zone = "hand" if decision.continuation_kind == "wave5_discard_then_draw" else "library"
    if decision.continuation_kind not in {None, "wave5_truce"}:
        for instance_id in selected_ids:
            if state.objects[instance_id].zone != expected_zone:
                raise ValueError("selected card is no longer a legal option")

    if decision.continuation_kind is None:
        # Wave 3's original tutor choice remains replay-compatible.
        selected_id = action.selected_instance_id
        player = next_state.players[action.player_id]
        next_state = _shuffle_library(next_state, event_log, player_id=action.player_id)
        if selected_id is not None:
            shuffled_player = next_state.players[action.player_id]
            library = [instance_id for instance_id in shuffled_player.library if instance_id != selected_id]
            library.insert(0, selected_id)
            next_state = update_player(next_state, replace(shuffled_player, library=tuple(library)))
            selected = next_state.objects[selected_id]
            event_log.append(event_type="card_revealed", active_player=action.player_id, payload={"player_id": action.player_id, "card_instance_id": selected_id, "oracle_id": selected.oracle_id, "reason": "tutor"})
        return TurnResult(state=next_state, event_log=event_log.events)

    kind = decision.continuation_kind
    if kind == "wave5_discard_then_draw":
        next_state = _discard_specific_cards(next_state, event_log, player_id=action.player_id, instance_ids=selected_ids, active_player=action.player_id)
        remaining = tuple(context["remaining_players"])
        counts = tuple(context.get("draw_counts", ())) + ((action.player_id, len(selected_ids)),)
        if remaining:
            next_state = _queue_wave5_decision(next_state, event_log, chooser_id=remaining[0], source_object_id=decision.source_object_id, kind="discard_any_number", option_ids=next_state.players[remaining[0]].hand, min_selections=0, max_selections=len(next_state.players[remaining[0]].hand), continuation_kind=kind, continuation=(("remaining_players", remaining[1:]), ("draw_counts", counts), ("caster_id", context["caster_id"])))
        else:
            for player_id, count in counts:
                for _ in range(count):
                    next_state = _draw_one_card_for_player_if_available(next_state, event_log, player_id=player_id)
            next_state = _draw_one_card_for_player_if_available(next_state, event_log, player_id=context["caster_id"])
    elif kind == "wave5_truce":
        count = action.declared_count
        if count is None or count > 2:
            raise ValueError("Temporary Truce requires an explicit count from zero to two")
        for _ in range(count):
            next_state = _draw_one_card_for_player_if_available(next_state, event_log, player_id=action.player_id)
        player = next_state.players[action.player_id]
        updated = replace(player, life_total=player.life_total + (2 - count) * 2)
        next_state = update_player(next_state, updated)
        event_log.append(event_type="life_total_changed", active_player=action.player_id, payload={"player_id": action.player_id, "life_total": updated.life_total})
        remaining = tuple(context["remaining_players"])
        if remaining:
            next_state = _queue_wave5_decision(next_state, event_log, chooser_id=remaining[0], source_object_id=decision.source_object_id, kind="draw_up_to_two", option_ids=(), min_selections=0, max_selections=0, continuation_kind=kind, continuation=(("remaining_players", remaining[1:]),))
    elif kind == "wave5_ancestral_memories":
        selected = set(selected_ids)
        for instance_id in decision.option_ids:
            destination = "hand" if instance_id in selected else "graveyard"
            next_state = _move_with_event(next_state, event_log, instance_id=instance_id, from_zone="library", to_zone=destination, player_id=action.player_id, active_player=action.player_id)
    elif kind == "wave5_order_library":
        player = next_state.players[action.player_id]
        remaining = tuple(instance_id for instance_id in player.library if instance_id not in decision.option_ids)
        next_state = update_player(next_state, replace(player, library=tuple(selected_ids) + remaining))
        if action.shuffle_library:
            next_state = _shuffle_library(next_state, event_log, player_id=action.player_id)
        if context.get("draw_after"):
            next_state = _draw_one_card_for_player_if_available(next_state, event_log, player_id=action.player_id)
    elif kind == "wave5_cruel_fate_select":
        selected_id = selected_ids[0]
        target_player_id = context["target_player_id"]
        next_state = _move_with_event(next_state, event_log, instance_id=selected_id, from_zone="library", to_zone="graveyard", player_id=target_player_id, active_player=action.player_id)
        remaining = tuple(instance_id for instance_id in decision.option_ids if instance_id != selected_id)
        next_state = _queue_wave5_decision(next_state, event_log, chooser_id=action.player_id, source_object_id=decision.source_object_id, kind="order_remaining_library_cards", option_ids=remaining, min_selections=len(remaining), max_selections=len(remaining), selection_ordered=True, continuation_kind="wave5_cruel_fate_order", continuation=(("target_player_id", target_player_id),))
    elif kind == "wave5_cruel_fate_order":
        target_player_id = context["target_player_id"]
        player = next_state.players[target_player_id]
        remaining = tuple(instance_id for instance_id in player.library if instance_id not in decision.option_ids)
        next_state = update_player(next_state, replace(player, library=tuple(selected_ids) + remaining))
    elif kind.startswith("wave5_search_"):
        player_id = action.player_id
        selected_id = selected_ids[0] if selected_ids else None
        destination = context["destination"]
        if destination != "library":
            for instance_id in selected_ids:
                next_state = _move_with_event(next_state, event_log, instance_id=instance_id, from_zone="library", to_zone=destination, player_id=player_id, active_player=player_id)
                if context.get("reveal_selection"):
                    event_log.append(event_type="card_revealed", active_player=player_id, payload={"player_id": player_id, "card_instance_id": instance_id, "oracle_id": next_state.objects[instance_id].oracle_id, "reason": "search"})
        if context.get("shuffle", True):
            next_state = _shuffle_library(next_state, event_log, player_id=player_id)
        if context.get("top_after_shuffle") and selected_id is not None:
            player = next_state.players[player_id]
            library = tuple(instance_id for instance_id in player.library if instance_id != selected_id)
            next_state = update_player(next_state, replace(player, library=(selected_id,) + library))
        if context.get("lose_life"):
            player = next_state.players[player_id]
            updated = replace(player, life_total=player.life_total - context["lose_life"])
            next_state = update_player(next_state, updated)
            event_log.append(event_type="life_total_changed", active_player=player_id, payload={"player_id": player_id, "life_total": updated.life_total})
            next_state, sba_events = apply_state_based_actions(next_state, card_repository, active_player=player_id)
            for event in sba_events:
                event_log.append(event_type=event["event_type"], active_player=event["active_player"], payload=event["payload"])
    else:
        raise ValueError("unsupported pending-decision continuation")
    return TurnResult(state=next_state, event_log=event_log.events)


def _put_spell_on_stack(
    state: GameState,
    *,
    card_instance_id: str,
    controller_id: str,
    target_ids: tuple[str, ...] = (),
    chosen_x: int = 0,
    additional_cost_instance_id: str | None = None,
    additional_cost_value: int | None = None,
    damage_assignments: tuple[tuple[str, int], ...] = (),
) -> GameState:
    """Record a cast spell and retain priority for its controller."""
    return replace(
        state,
        stack_entries=state.stack_entries
        + (StackEntry(card_instance_id=card_instance_id, controller_id=controller_id, target_ids=target_ids, chosen_x=chosen_x, additional_cost_instance_id=additional_cost_instance_id, additional_cost_value=additional_cost_value, damage_assignments=damage_assignments, target_object_ids=tuple(state.objects[target_id].object_id for target_id in target_ids if target_id in state.objects)),),
        turn=replace(state.turn, priority_player=controller_id),
        consecutive_passes=0,
    )


def _resolve_top_stack_entry(session: TurnResult, card_repository: CardRepository) -> TurnResult:
    state = session.state
    entry = state.stack_entries[-1]
    event_log = EventLog.from_events(state.game_id, session.event_log)

    if entry.entry_kind == "alabaster_dragon_death_trigger":
        result = _resolve_alabaster_dragon_death_trigger(
            TurnResult(state=state, event_log=event_log.events), entry
        )
    elif entry.entry_kind == "wave7_trigger":
        result = _resolve_wave7_trigger(TurnResult(state=state, event_log=event_log.events), entry, card_repository)
    elif entry.entry_kind == "wave7_retaliation":
        target_id = entry.target_ids[0]
        target = state.players[target_id]
        resolved_state = update_player(state, replace(target, life_total=target.life_total - (entry.additional_cost_value or 0)))
        event_log.append(event_type="damage_applied", active_player=entry.controller_id, payload={"target_player_id": target_id, "damage": entry.additional_cost_value or 0, "reason": "Harsh Justice"})
        result = TurnResult(resolved_state, event_log.events)
    elif entry.entry_kind == "activated_ability":
        result = _resolve_wave7_activated_ability(TurnResult(state=state, event_log=event_log.events), entry, card_repository)
    else:
        spell = state.objects[entry.card_instance_id]
        definition = card_repository.get(spell.oracle_id)
        if definition.is_creature:
            resolved_state = move_object(
                state,
                instance_id=entry.card_instance_id,
                from_zone="stack",
                to_zone="battlefield",
                player_id=entry.controller_id,
            )
            event_log.append(
                event_type="spell_resolved",
                active_player=entry.controller_id,
                payload={"player_id": entry.controller_id, "card_instance_id": entry.card_instance_id, "oracle_id": spell.oracle_id},
            )
            event_log.append(
                event_type="object_moved_between_zones",
                active_player=entry.controller_id,
                payload={"player_id": entry.controller_id, "card_instance_id": entry.card_instance_id, "oracle_id": spell.oracle_id, "from_zone": "stack", "to_zone": "battlefield", **zone_change_identity_payload(resolved_state, entry.card_instance_id)},
            )
            result = TurnResult(state=resolved_state, event_log=event_log.events)
            result = _queue_wave7_enter_trigger(result, entry, card_repository)
        elif _stack_entry_targets_are_legal(state, entry, card_repository):
            result = _resolve_noncreature_spell(
                TurnResult(state=state, event_log=event_log.events), entry, card_repository
            )
        else:
            countered_state = move_object(
                state,
                instance_id=entry.card_instance_id,
                from_zone="stack",
                to_zone="graveyard",
                player_id=entry.controller_id,
            )
            event_log.append(
                event_type="spell_countered_on_resolution",
                active_player=entry.controller_id,
                payload={"player_id": entry.controller_id, "card_instance_id": entry.card_instance_id, "oracle_id": spell.oracle_id, "target_instance_ids": list(entry.target_ids)},
            )
            event_log.append(
                event_type="object_moved_between_zones",
                active_player=entry.controller_id,
                payload={"player_id": entry.controller_id, "card_instance_id": entry.card_instance_id, "oracle_id": spell.oracle_id, "from_zone": "stack", "to_zone": "graveyard", **zone_change_identity_payload(countered_state, entry.card_instance_id)},
            )
            result = TurnResult(state=countered_state, event_log=event_log.events)

    # Resolution can put triggered abilities above this entry.  Remove the
    # entry that was selected at the start, while retaining those new entries.
    original_entry_index = len(state.stack_entries) - 1
    remaining_entries = (
        result.state.stack_entries[:original_entry_index]
        + result.state.stack_entries[original_entry_index + 1 :]
    )
    final_state = replace(
        result.state,
        stack_entries=remaining_entries,
        consecutive_passes=0,
        turn=replace(result.state.turn, priority_player=result.state.turn.active_player),
    )
    return TurnResult(state=final_state, event_log=result.event_log)


def _queue_wave7_enter_trigger(session: TurnResult, entry: StackEntry, card_repository: CardRepository) -> TurnResult:
    state = session.state
    effect = effect_key_for(state.objects[entry.card_instance_id].oracle_id)
    if effect is None or not effect.endswith("_etb"):
        return session
    trigger = StackEntry(card_instance_id=entry.card_instance_id, controller_id=entry.controller_id,
                         entry_kind="wave7_trigger", source_object_id=state.objects[entry.card_instance_id].object_id,
                         source_oracle_id=state.objects[entry.card_instance_id].oracle_id)
    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(event_type="triggered_ability_put_on_stack", active_player=state.turn.active_player,
                     payload={"ability_key": effect, "card_instance_id": entry.card_instance_id, "oracle_id": trigger.source_oracle_id})
    return TurnResult(replace(state, stack_entries=state.stack_entries + (trigger,), consecutive_passes=0), event_log.events)


def _resolve_wave7_activated_ability(session: TurnResult, entry: StackEntry, card_repository: CardRepository) -> TurnResult:
    state = session.state; event_log = EventLog.from_events(state.game_id, session.event_log)
    effect = effect_key_for(entry.source_oracle_id or state.objects[entry.card_instance_id].oracle_id)
    target = entry.target_ids[0] if entry.target_ids else None
    resolved = state
    if target is not None and _stack_entry_targets_are_legal(state, entry, card_repository):
        if effect == "capricious_sorcerer":
            resolved, events = _resolve_direct_damage_sorcery(state, card_repository, target, effect="damage_any_target_variable", active_player=entry.controller_id, damage_override=1)
            for item in events: event_log.append(event_type=item["event_type"], active_player=item["active_player"], payload=item["payload"])
        elif effect == "kings_assassin":
            resolved, _ = _destroy_permanents(state, event_log, instance_ids=(target,), active_player=entry.controller_id, reason="ability:King's Assassin")
        elif effect == "stern_marshal":
            resolved = _add_temporary_effect(state, source_object_id=entry.source_object_id or "", target_ids=(target,), power_delta=2, toughness_delta=2)
    event_log.append(event_type="activated_ability_resolved", active_player=entry.controller_id, payload={"source_instance_id": entry.card_instance_id, "effect": effect})
    return TurnResult(resolved, event_log.events)


def _resolve_wave7_trigger(session: TurnResult, entry: StackEntry, card_repository: CardRepository) -> TurnResult:
    """Resolve the registered Wave 7 trigger schemas; no text parsing occurs."""
    state = session.state; event_log = EventLog.from_events(state.game_id, session.event_log)
    effect = effect_key_for(entry.source_oracle_id or state.objects[entry.card_instance_id].oracle_id)
    resolved = state; source = state.objects[entry.card_instance_id]
    life_delta = {"dread_reaper_etb": -5, "serpent_warrior_etb": -3, "spiritual_guardian_etb": 4, "venerable_monk_etb": 2}.get(effect)
    if life_delta is not None:
        player = resolved.players[entry.controller_id]; resolved = update_player(resolved, replace(player, life_total=player.life_total + life_delta))
        event_log.append(event_type="life_total_changed", active_player=entry.controller_id, payload={"player_id": entry.controller_id, "life_total": player.life_total + life_delta})
    elif effect in {"charging_bandits_attack", "charging_paladin_attack"}:
        if source.zone == "battlefield" and source.object_id == entry.source_object_id:
            power, toughness = (2, 0) if effect == "charging_bandits_attack" else (0, 3)
            resolved = _add_temporary_effect(resolved, source_object_id=entry.source_object_id or "", target_ids=(source.instance_id,), power_delta=power, toughness_delta=toughness)
    elif effect == "thundermare_etb":
        for player in resolved.players.values():
            for instance_id in player.battlefield:
                if instance_id != entry.card_instance_id and card_repository.get(resolved.objects[instance_id].oracle_id).is_creature:
                    resolved = update_object(resolved, replace(resolved.objects[instance_id], tapped=True))
    elif effect == "owl_familiar_etb":
        resolved = _draw_one_card_for_player_if_available(resolved, event_log, player_id=entry.controller_id)
        hand = resolved.players[entry.controller_id].hand
        if hand: resolved = _discard_specific_cards(resolved, event_log, player_id=entry.controller_id, instance_ids=(hand[0],), active_player=entry.controller_id)
    elif effect == "ebon_dragon_etb":
        opponent = next((pid for pid in resolved.players if pid != entry.controller_id), None)
        if opponent is not None: resolved = _discard_first_cards_in_hand_order(resolved, event_log, player_id=opponent, count=1, active_player=entry.controller_id)
    elif effect == "gravedigger_etb":
        choices = tuple(i for i in resolved.players[entry.controller_id].graveyard if card_repository.get(resolved.objects[i].oracle_id).is_creature and i != entry.card_instance_id)
        if choices: resolved = _move_with_event(resolved, event_log, instance_id=choices[0], from_zone="graveyard", to_zone="hand", player_id=entry.controller_id, active_player=entry.controller_id)
    elif effect == "wood_elves_etb":
        choices = tuple(i for i in resolved.players[entry.controller_id].library if card_repository.get(resolved.objects[i].oracle_id).has_subtype("Forest"))
        if choices: resolved = _move_with_event(resolved, event_log, instance_id=choices[0], from_zone="library", to_zone="battlefield", player_id=entry.controller_id, active_player=entry.controller_id)
        resolved = _shuffle_library(resolved, event_log, player_id=entry.controller_id)
    elif effect == "endless_cockroaches_death" and source.zone == "graveyard" and source.object_id == entry.expected_graveyard_object_id:
        resolved = _move_with_event(resolved, event_log, instance_id=source.instance_id, from_zone="graveyard", to_zone="hand", player_id=source.owner_id, active_player=entry.controller_id)
    elif effect == "undying_beast_death" and source.zone == "graveyard" and source.object_id == entry.expected_graveyard_object_id:
        resolved = move_object_to_top_of_library(resolved, instance_id=source.instance_id, from_zone="graveyard", player_id=source.owner_id)
    elif effect == "noxious_toad_death":
        for player_id in resolved.players:
            if player_id != entry.controller_id:
                resolved = _discard_first_cards_in_hand_order(resolved, event_log, player_id=player_id, count=1, active_player=entry.controller_id)
    elif effect in {"fire_imp_etb", "fire_dragon_etb", "serpent_assassin_etb", "manowar_etb", "fire_snake_death", "seasoned_marshal_attack"}:
        # Trigger targets are intentionally not inferred from card text.  This
        # bounded fallback keeps direct StackEntry/replay callers deterministic
        # while normal UI selection may supply the declared target identity.
        candidates = tuple(i for player in resolved.players.values() for i in player.battlefield if card_repository.get(resolved.objects[i].oracle_id).is_creature)
        target = entry.target_ids[0] if entry.target_ids else (candidates[0] if candidates else None)
        if effect == "fire_snake_death":
            lands = tuple(i for player in resolved.players.values() for i in player.battlefield if card_repository.get(resolved.objects[i].oracle_id).is_land)
            target = entry.target_ids[0] if entry.target_ids else (lands[0] if lands else None)
        if target is not None:
            if effect == "fire_imp_etb":
                resolved, events = _resolve_direct_damage_sorcery(resolved, card_repository, target, effect="damage_any_target_variable", active_player=entry.controller_id, damage_override=2)
                for item in events: event_log.append(event_type=item["event_type"], active_player=item["active_player"], payload=item["payload"])
            elif effect == "fire_dragon_etb":
                damage = _controlled_land_subtype_count(resolved, card_repository, entry.controller_id, "Mountain")
                resolved, events = _resolve_direct_damage_sorcery(resolved, card_repository, target, effect="damage_any_target_variable", active_player=entry.controller_id, damage_override=damage)
                for item in events: event_log.append(event_type=item["event_type"], active_player=item["active_player"], payload=item["payload"])
            elif effect in {"serpent_assassin_etb", "fire_snake_death"}:
                resolved, _ = _destroy_permanents(resolved, event_log, instance_ids=(target,), active_player=entry.controller_id, reason=f"trigger:{effect}")
            elif effect == "manowar_etb":
                target_obj = resolved.objects[target]; resolved = _move_with_event(resolved, event_log, instance_id=target, from_zone="battlefield", to_zone="hand", player_id=target_obj.owner_id, active_player=entry.controller_id)
            else:
                resolved = update_object(resolved, replace(resolved.objects[target], tapped=True))
    elif effect in {"mercenary_knight_etb", "pillaging_horde_etb", "plant_elemental_etb", "primeval_force_etb", "thundering_wurm_etb", "thing_from_the_deep_attack"}:
        # A mandatory 'unless' payment is deliberately conservative: choose the first
        # qualifying deterministic option; if none exists, sacrifice the source.
        qualifying = ()
        if effect in {"mercenary_knight_etb", "thundering_wurm_etb"}:
            qualifier = "creature" if effect == "mercenary_knight_etb" else "land"
            qualifying = tuple(i for i in resolved.players[entry.controller_id].hand if getattr(card_repository.get(resolved.objects[i].oracle_id), f"is_{qualifier}"))
        elif effect in {"plant_elemental_etb", "primeval_force_etb", "thing_from_the_deep_attack"}:
            subtype = "Forest" if effect != "thing_from_the_deep_attack" else "Island"; count = 3 if effect == "primeval_force_etb" else 1
            qualifying = tuple(i for i in resolved.players[entry.controller_id].battlefield if card_repository.get(resolved.objects[i].oracle_id).is_land and card_repository.get(resolved.objects[i].oracle_id).has_subtype(subtype))
            qualifying = qualifying if len(qualifying) >= count else ()
        if effect == "pillaging_horde_etb": qualifying = resolved.players[entry.controller_id].hand
        if qualifying:
            if effect == "pillaging_horde_etb":
                selected = random.Random(resolved.rng_seed + resolved.rng_cursor).choice(qualifying); resolved = replace(resolved, rng_cursor=resolved.rng_cursor + 1)
            else: selected = qualifying[0]
            if selected in resolved.players[entry.controller_id].hand: resolved = _discard_specific_cards(resolved, event_log, player_id=entry.controller_id, instance_ids=(selected,), active_player=entry.controller_id)
            else: resolved, _ = _destroy_permanents(resolved, event_log, instance_ids=(selected,), active_player=entry.controller_id, reason="trigger_payment")
        elif source.zone == "battlefield":
            resolved, _ = _destroy_permanents(resolved, event_log, instance_ids=(source.instance_id,), active_player=entry.controller_id, reason="unpaid_trigger_cost")
    event_log.append(event_type="triggered_ability_resolved", active_player=entry.controller_id, payload={"ability_key": effect, "card_instance_id": entry.card_instance_id})
    return TurnResult(resolved, event_log.events)


def _resolve_alabaster_dragon_death_trigger(session: TurnResult, entry: StackEntry) -> TurnResult:
    state = session.state
    event_log = EventLog.from_events(state.game_id, session.event_log)
    owner_id = entry.owner_id or entry.controller_id
    source = state.objects[entry.card_instance_id]
    moved = (
        source.zone == "graveyard"
        and source.owner_id == owner_id
        and source.object_id == entry.expected_graveyard_object_id
    )
    resolved_state = state
    if moved:
        resolved_state = move_object(
            state,
            instance_id=entry.card_instance_id,
            from_zone="graveyard",
            to_zone="library",
            player_id=owner_id,
        )
        event_log.append(
            event_type="object_moved_between_zones",
            active_player=owner_id,
            payload={"player_id": owner_id, "card_instance_id": entry.card_instance_id, "oracle_id": source.oracle_id, "from_zone": "graveyard", "to_zone": "library", **zone_change_identity_payload(resolved_state, entry.card_instance_id)},
        )
        player = resolved_state.players[owner_id]
        shuffled = list(player.library)
        random.Random(resolved_state.rng_seed + resolved_state.rng_cursor).shuffle(shuffled)
        resolved_state = update_player(resolved_state, replace(player, library=tuple(shuffled)))
        next_cursor = resolved_state.rng_cursor + 1
        resolved_state = replace(resolved_state, rng_cursor=next_cursor)
        event_log.append(
            event_type="library_shuffled",
            active_player=owner_id,
            payload={"player_id": owner_id, "algorithm": "python_random_mt19937_v1", "rng_cursor_before": state.rng_cursor, "rng_cursor_after": next_cursor, "count": len(shuffled)},
        )
    event_log.append(
        event_type="triggered_ability_resolved",
        active_player=owner_id,
        payload={"ability_key": "alabaster_dragon_death_trigger", "card_instance_id": entry.card_instance_id, "oracle_id": entry.source_oracle_id, "owner_id": owner_id, "moved_to_library": moved},
    )
    return TurnResult(state=resolved_state, event_log=event_log.events)


def _stack_entry_targets_are_legal(
    state: GameState,
    entry: StackEntry,
    card_repository: CardRepository,
) -> bool:
    if not entry.target_ids:
        return True
    definition = card_repository.get(state.objects[entry.card_instance_id].oracle_id)
    effect = _supported_targeted_sorcery_effect(definition)
    if effect is None:
        return False
    try:
        _require_legal_noncreature_target(state, card_repository, entry.target_ids, effect=effect)
    except ValueError:
        return False
    return True


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
    if state.turn.step not in {"precombat_main_step", "declare_attackers_step", "combat_damage_step"}:
        raise ValueError("priority is not available in this step")

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

    passed_state = replace(
        state,
        turn=replace(state.turn, priority_player=next_priority_player),
        consecutive_passes=state.consecutive_passes + 1,
    )
    if state.stack_entries:
        if passed_state.consecutive_passes < 2:
            return TurnResult(state=passed_state, event_log=event_log.events)
        return _resolve_top_stack_entry(
            TurnResult(state=passed_state, event_log=event_log.events),
            card_repository,
        )

    if state.turn.step == "precombat_main_step":
        opposing_actions = enumerate_legal_actions(passed_state, card_repository)
        if any(not isinstance(candidate, PassPriorityAction) for candidate in opposing_actions):
            return TurnResult(state=passed_state, event_log=event_log.events)
    elif passed_state.consecutive_passes < 2:
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
    restored_state = replace(
        passed_state,
        turn=replace(passed_state.turn, priority_player=state.turn.active_player),
        consecutive_passes=0,
    )
    if state.turn.step == "declare_attackers_step" and state.combat is not None:
        next_state = replace(restored_state, turn=replace(restored_state.turn, step="declare_blockers_step", priority_player=state.combat.defending_player))
        event_log.append(event_type="step_changed", active_player=state.turn.active_player, payload={"turn_number": state.turn.turn_number, "from_step": "declare_attackers_step", "to_step": "declare_blockers_step"})
        return TurnResult(state=next_state, event_log=event_log.events)
    if state.turn.step == "combat_damage_step":
        next_state = replace(restored_state, turn=replace(restored_state.turn, step="end_combat_step"))
        event_log.append(event_type="step_changed", active_player=state.turn.active_player, payload={"turn_number": state.turn.turn_number, "from_step": "combat_damage_step", "to_step": "end_combat_step"})
        return TurnResult(state=next_state, event_log=event_log.events)
    return advance_to_begin_combat(TurnResult(state=restored_state, event_log=event_log.events))


def advance_to_begin_combat(session: TurnResult | GameBootstrap) -> TurnResult:
    state = session.state
    require_step(state, "precombat_main_step")
    event_log = EventLog.from_events(state.game_id, session.event_log)
    if any(effect.kind == "skip_combat" and effect.player_id == state.turn.active_player for effect in state.delayed_turn_effects):
        remaining = tuple(effect for effect in state.delayed_turn_effects if not (effect.kind == "skip_combat" and effect.player_id == state.turn.active_player))
        skipped_state = replace(state, delayed_turn_effects=remaining, turn=replace(state.turn, step="end_combat_step"))
        event_log.append(event_type="combat_phase_skipped", active_player=state.turn.active_player, payload={"player_id": state.turn.active_player})
        event_log.append(event_type="step_changed", active_player=state.turn.active_player, payload={"turn_number": state.turn.turn_number, "from_step": "precombat_main_step", "to_step": "end_combat_step"})
        return TurnResult(state=skipped_state, event_log=event_log.events)
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
        rejection_reason = attacker_attack_rejection_reason(
            state=state,
            card_repository=card_repository,
            attacker_id=attacker_id,
        )
        if rejection_reason is not None:
            raise ValueError(rejection_reason)

    requirement = next((effect for effect in state.delayed_turn_effects if effect.kind == "must_attack_source" and effect.player_id == action.player_id), None)
    if requirement is not None:
        required_ids = tuple(instance_id for instance_id in state.players[action.player_id].battlefield if attacker_attack_rejection_reason(state=state, card_repository=card_repository, attacker_id=instance_id) is None)
        if any(instance_id not in action.attacker_ids for instance_id in required_ids):
            raise ValueError("creatures must attack if able")

    next_state = tap_attackers(state, action.attacker_ids, card_repository)
    next_state = with_combat_state(
        next_state,
        attacking_player=action.player_id,
        defending_player=defending_player,
        attackers=action.attacker_ids,
        blockers={},
    )
    next_state = replace(next_state, turn=replace(next_state.turn, priority_player=action.player_id))
    if requirement is not None:
        next_state = replace(
            next_state,
            delayed_turn_effects=tuple(
                effect for effect in next_state.delayed_turn_effects
                if effect is not requirement
            ),
        )

    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(event_type="attackers_declared", active_player=action.player_id, payload={"player_id": action.player_id, "attacker_ids": list(action.attacker_ids), "defending_player": defending_player})
    trigger_entries = []
    for attacker_id in action.attacker_ids:
        attacker = next_state.objects[attacker_id]
        effect = effect_key_for(attacker.oracle_id)
        if effect in {"charging_bandits_attack", "charging_paladin_attack", "seasoned_marshal_attack", "thing_from_the_deep_attack"}:
            trigger_entries.append(StackEntry(card_instance_id=attacker_id, controller_id=attacker.controller_id, entry_kind="wave7_trigger", source_object_id=attacker.object_id, source_oracle_id=attacker.oracle_id))
            event_log.append(event_type="triggered_ability_put_on_stack", active_player=action.player_id, payload={"ability_key": effect, "card_instance_id": attacker_id, "oracle_id": attacker.oracle_id})
    if trigger_entries:
        next_state = replace(next_state, stack_entries=next_state.stack_entries + tuple(trigger_entries), consecutive_passes=0)
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
            rejection_reason = blocker_attack_rejection_reason(
                state=state,
                card_repository=card_repository,
                blocker_id=blocker_id,
                attacker_id=attacker_id,
            )
            if rejection_reason is not None:
                raise ValueError(rejection_reason)
            assigned_blockers.add(blocker_id)
        if card_repository.get(state.objects[attacker_id].oracle_id).name in {"Charging Rhino", "Stalking Tiger"} and len(blocker_ids) > 1:
            raise ValueError("attacker cannot be blocked by more than one creature")

    forced_target = state.forced_block_target_object_id
    if forced_target is not None:
        target_id = next((instance_id for instance_id in state.combat.attackers if state.objects[instance_id].object_id == forced_target), None)
        if target_id is not None:
            for blocker_id in state.players[action.player_id].battlefield:
                if blocker_attack_rejection_reason(state=state, card_repository=card_repository, blocker_id=blocker_id, attacker_id=target_id) is None and blocker_id not in action.blockers.get(target_id, ()):
                    raise ValueError("creature able to block the required target must do so")

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
    next_step = "combat_damage_step" if next_state.stack_entries else "end_combat_step"
    next_state = replace(
        next_state,
        turn=replace(next_state.turn, step=next_step, priority_player=state.turn.active_player),
        consecutive_passes=0,
    )

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
            "to_step": next_step,
        },
    )
    return TurnResult(state=next_state, event_log=event_log.events)


def advance_to_cleanup(session: TurnResult | GameBootstrap) -> TurnResult:
    state = session.state
    require_step(state, "end_combat_step")
    if state.stack_entries:
        raise ValueError("cleanup requires an empty stack")

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

        if next_step == "end_step" and any(effect.kind == "lose_at_end_step" and effect.player_id == current_state.turn.active_player and effect.turn_number == current_state.turn.turn_number for effect in current_state.delayed_turn_effects):
            loser_id = current_state.turn.active_player
            winner_id = _other_player(current_state, loser_id)
            current_state = replace(current_state, outcome=GameOutcome(status="completed", winner_id=winner_id, loser_ids=(loser_id,), reason="last_chance"), delayed_turn_effects=tuple(effect for effect in current_state.delayed_turn_effects if not (effect.kind == "lose_at_end_step" and effect.player_id == loser_id)))
            event_log.append(event_type="game_ended", active_player=loser_id, payload={"winner_id": winner_id, "loser_ids": [loser_id], "reason": "last_chance"})
            return TurnResult(state=current_state, event_log=event_log.events)

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

    scheduled_extra = state.extra_turns[0] if state.extra_turns else None
    next_active_player = scheduled_extra.player_id if scheduled_extra else _other_player(state, state.turn.active_player)
    next_turn_number = state.turn.turn_number + 1
    current_state = replace(
        state,
        extra_turns=state.extra_turns[1:] if scheduled_extra else state.extra_turns,
        turn=TurnState(
            turn_number=next_turn_number,
            active_player=next_active_player,
            priority_player=next_active_player,
            step="turn_begin",
        ),
    )
    prevent_untap = any(effect.kind == "prevent_untap" and effect.player_id == next_active_player for effect in current_state.delayed_turn_effects)
    current_state = _untap_player_battlefield(current_state, next_active_player, card_repository=None, prevent_creatures_and_lands=prevent_untap)
    current_state = replace(current_state, delayed_turn_effects=tuple(effect for effect in current_state.delayed_turn_effects if not (effect.kind == "prevent_untap" and effect.player_id == next_active_player)))
    if scheduled_extra and scheduled_extra.lose_at_end_step:
        current_state = replace(current_state, delayed_turn_effects=current_state.delayed_turn_effects + (DelayedTurnEffect(kind="lose_at_end_step", player_id=next_active_player, turn_number=next_turn_number),))

    event_log = EventLog.from_events(state.game_id, session.event_log)
    event_log.append(
        event_type="turn_started",
        active_player=next_active_player,
        payload={
            "turn_number": next_turn_number,
            "active_player": next_active_player,
        },
    )
    if scheduled_extra:
        event_log.append(event_type="extra_turn_started", active_player=next_active_player, payload={"player_id": next_active_player, "turn_number": next_turn_number})
    if prevent_untap:
        event_log.append(event_type="untap_prevented", active_player=next_active_player, payload={"player_id": next_active_player})

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
        winner_id = _other_player(state, player_id)
        next_state = replace(
            state,
            outcome=GameOutcome(
                status="completed",
                winner_id=winner_id,
                loser_ids=(player_id,),
                reason="draw_from_empty_library",
            ),
        )
        event_log.append(
            event_type="game_ended",
            active_player=state.turn.active_player,
            payload={"winner_id": winner_id, "loser_ids": [player_id], "reason": "draw_from_empty_library"},
        )
        return next_state

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
            **zone_change_identity_payload(next_state, top_instance_id),
        },
    )
    return next_state


def _parse_mana_cost(mana_cost: str, *, chosen_x: int = 0) -> dict[str, int]:
    requirements = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "generic": 0}
    if not mana_cost:
        return requirements
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for symbol in symbols:
        if symbol in {"W", "U", "B", "R", "G"}:
            requirements[symbol] += 1
        elif symbol.isdigit():
            requirements["generic"] += int(symbol)
        elif symbol == "X":
            requirements["generic"] += chosen_x
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
    if effect in {"draw_two_cards", "gain_4_life", "gain_life_per_forest", "additional_three_land_plays", "tutor_sorcery_to_top", "tutor_creature_to_top", "destroy_all_lands", "destroy_all_creatures", "destroy_all_green_creatures", "destroy_all_white_creatures", "destroy_all_islands", "destroy_all_plains", "untap_all_creatures_you_control", "tap_all_nonwhite_creatures", "damage_all_creatures_2", "damage_all_flying_creatures_4", "damage_all_creatures_and_players_1", "damage_all_creatures_and_players_6", "damage_all_flying_creatures_and_players_x", "controlled_creatures_get_0_3_until_end_of_turn", "controlled_creatures_get_1_1_until_end_of_turn", "white_creatures_get_2_0_until_end_of_turn", "green_controlled_creatures_gain_forestwalk_until_end_of_turn", "black_controlled_creatures_only_blockable_by_black_until_end_of_turn", "controlled_creatures_gain_reach_until_end_of_turn", "flux", "natural_order", "ancestral_memories", "prosperity", "temporary_truce", "winds_of_change", "untamed_wilds", "gift_of_estates", "cruel_bargain", "cruel_tutor", "natures_lore", "omen", "earthquake", "devastation", "last_chance", "blessed_reversal", "deep_wood", "harsh_justice", "scorching_winds", "owl_familiar_etb", "thundermare_etb", "dread_reaper_etb", "serpent_warrior_etb", "spiritual_guardian_etb", "venerable_monk_etb"}:
        if target_instance_ids:
            raise ValueError("sorcery does not take a target")
        return
    if effect == "tap_up_to_three_nonflying_creatures":
        if len(target_instance_ids) > 3:
            raise ValueError("spell targets up to three creatures")
        if len(set(target_instance_ids)) != len(target_instance_ids):
            raise ValueError("spell requires distinct targets")
        for target_instance_id in target_instance_ids:
            if target_instance_id not in state.objects:
                raise ValueError("target must exist")
            target = state.objects[target_instance_id]
            if target.zone != "battlefield":
                raise ValueError("target must be on the battlefield")
            target_definition = card_repository.get(target.oracle_id)
            if not target_definition.is_creature:
                raise ValueError("target must be a creature")
            if target_definition.has_flying:
                raise ValueError("target must be a creature without flying")
        return
    if not target_instance_ids:
        raise ValueError("targeted sorcery requires a target")
    if effect in {"destroy_two_target_lands", "wicked_pact"}:
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
            if effect == "destroy_two_target_lands" and not target_definition.is_land:
                raise ValueError("target must be a land")
            if effect == "wicked_pact" and (not target_definition.is_creature or target_definition.is_black):
                raise ValueError("target must be a nonblack creature")
        return
    if effect == "forked_lightning":
        if not 1 <= len(target_instance_ids) <= 3 or len(set(target_instance_ids)) != len(target_instance_ids):
            raise ValueError("Forked Lightning requires one to three distinct creature targets")
        for target_id in target_instance_ids:
            if target_id not in state.objects or state.objects[target_id].zone != "battlefield" or not card_repository.get(state.objects[target_id].oracle_id).is_creature:
                raise ValueError("Forked Lightning targets must be creatures")
        return
    if len(target_instance_ids) != 1:
        raise ValueError("spell requires exactly one target")
    target_instance_id = target_instance_ids[0]
    if effect == "damage_target_player":
        if target_instance_id not in state.players:
            raise ValueError("target must be a player")
        return
    if effect in {"target_player_gains_8_life", "gain_life_per_opponent_mountain", "draw_per_tapped_creature_target_opponent_controls", "look_at_opponent_hand_draw_one", "balance_of_power", "withering_gaze", "mind_knives", "baleful_stare", "starlight", "cruel_fate", "exhaustion"}:
        if target_instance_id not in state.players:
            raise ValueError("target must be a player")
        if effect != "target_player_gains_8_life" and target_instance_id == state.turn.active_player:
            raise ValueError("target must be an opponent")
        return
    if effect in {"false_peace", "taunt"}:
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
    if effect in {"destroy_target_land", "fire_snake_death"}:
        if target_instance_id not in state.objects:
            raise ValueError("target must exist")
        target = state.objects[target_instance_id]
        if target.zone != "battlefield":
            raise ValueError("target must be on the battlefield")
        target_definition = card_repository.get(target.oracle_id)
        if not target_definition.is_land:
            raise ValueError("target must be a land")
        return
    if effect == "destroy_target_creature_or_land":
        if target_instance_id not in state.objects:
            raise ValueError("target must exist")
        target = state.objects[target_instance_id]
        if target.zone != "battlefield":
            raise ValueError("target must be on the battlefield")
        definition = card_repository.get(target.oracle_id)
        if not (definition.is_creature or definition.is_land):
            raise ValueError("target must be a creature or land")
        return
    if effect in {"damage_target_opponent_2_gain_2", "final_strike"}:
        if target_instance_id not in state.players or target_instance_id == state.turn.active_player: raise ValueError("target must be an opponent")
        return
    if effect == "damage_nonblack_creature_3_gain_3":
        if target_instance_id not in state.objects: raise ValueError("target must exist")
        target = state.objects[target_instance_id]; definition = card_repository.get(target.oracle_id)
        if target.zone != "battlefield" or not definition.is_creature or definition.is_black: raise ValueError("target must be nonblack creature")
        return
    if effect in {"target_creature_gets_4_power_until_end_of_turn", "target_creature_gets_4_4_until_end_of_turn", "target_creature_gets_2_power_and_takes_2", "damage_target_creature_per_mountain", "all_able_creatures_block_target_this_turn", "target_creature_gets_3_3_and_flying_until_end_of_turn", "target_creature_gains_flying_and_draw_one", "fire_imp_etb", "fire_dragon_etb", "defiant_stand", "stern_marshal", "seasoned_marshal_attack", "manowar_etb", "command_of_unsummoning"}:
        if target_instance_id not in state.objects: raise ValueError("target must exist")
        target = state.objects[target_instance_id]
        if target.zone != "battlefield" or not card_repository.get(target.oracle_id).is_creature: raise ValueError("target must be a creature")
        return
    if effect in {"return_target_creature_card_from_your_graveyard", "return_target_creature_card_from_your_graveyard_to_battlefield", "return_target_card_from_your_graveyard", "return_target_sorcery_card_from_your_graveyard"}:
        if target_instance_id not in state.objects:
            raise ValueError("target must exist")
        target = state.objects[target_instance_id]
        if target.zone != "graveyard" or target.owner_id != state.turn.active_player:
            raise ValueError("target must be in your graveyard")
        target_definition = card_repository.get(target.oracle_id)
        if effect in {"return_target_creature_card_from_your_graveyard", "return_target_creature_card_from_your_graveyard_to_battlefield"} and not target_definition.is_creature:
            raise ValueError("target must be a creature card")
        if effect == "return_target_sorcery_card_from_your_graveyard" and not target_definition.is_sorcery:
            raise ValueError("target must be a sorcery card")
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
    if effect in {"damage_any_target", "damage_any_target_1", "damage_any_target_2", "damage_any_target_4_gain_4", "blaze", "capricious_sorcerer"}:
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
    if effect in {"destroy_tapped_creature", "kings_assassin"} and not target.tapped:
        raise ValueError("target must be tapped")
    if effect in {"destroy_nonblack_creature", "assassins_blade", "serpent_assassin_etb"} and target_definition.is_black:
        raise ValueError("target must be nonblack creature")


def _supported_targeted_sorcery_effect(card_definition) -> str | None:
    return effect_key_for(card_definition.oracle_id) if (card_definition.is_sorcery or card_definition.is_instant) else None



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


def _controlled_land_subtype_count(
    state: GameState,
    card_repository: CardRepository,
    player_id: str,
    subtype: str,
) -> int:
    return sum(
        1
        for instance_id in state.players[player_id].battlefield
        if (
            (definition := card_repository.get(state.objects[instance_id].oracle_id)).is_land
            and definition.has_subtype(subtype)
        )
    )


def _battlefield_land_subtype_count(
    state: GameState,
    card_repository: CardRepository,
    subtype: str,
) -> int:
    return len(
        _battlefield_permanents_matching(
            state,
            card_repository,
            predicate=lambda definition: definition.is_land and definition.has_subtype(subtype),
        )
    )


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
    destroyed_objects: list[dict] = []
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
        destroyed_objects.append(
            {
                "card_instance_id": instance_id,
                "source_object_id": permanent.object_id,
                "owner_id": permanent.owner_id,
                "controller_id": permanent.controller_id,
                "oracle_id": permanent.oracle_id,
            }
        )
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
                **zone_change_identity_payload(current_state, instance_id),
            },
        )
    current_state, trigger_events = queue_death_triggers(
        current_state,
        destroyed_objects,
        active_player=active_player,
    )
    for event in trigger_events:
        event_log.append(
            event_type=event["event_type"],
            active_player=event["active_player"],
            payload=event["payload"],
        )
    return current_state, destroyed_count


def _resolve_direct_damage_sorcery(
    state: GameState,
    card_repository: CardRepository,
    target_id: str | None,
    *,
    effect: str,
    active_player: str,
    damage_override: int | None = None,
) -> tuple[GameState, list[dict]]:
    if target_id is None:
        raise ValueError("targeted sorcery requires a target")

    damage_amount = damage_override if damage_override is not None else {
        "damage_any_target": 3,
        "damage_target_player": 5,
        "damage_any_target_1": 1,
        "damage_any_target_2": 2,
        "damage_nonblack_creature_3": 3,
        "damage_target_opponent_2": 2,
    }[effect]
    if target_id in state.players:
        target_player = state.players[target_id]
        updated_player = replace(target_player, life_total=target_player.life_total - damage_amount)
        next_state = update_player(state, updated_player)
        events = [
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
        next_state, sba_events = apply_state_based_actions(next_state, card_repository, active_player=active_player)
        events.extend(sba_events)
        return next_state, events

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


def _damage_creatures_once(state: GameState, card_repository: CardRepository, target_ids: tuple[str, ...], damage: int, active_player: str, *, check_sbas: bool = True) -> tuple[GameState, list[dict]]:
    current_state = state
    events: list[dict] = []
    for target_id in target_ids:
        target = current_state.objects[target_id]
        definition = card_repository.get(target.oracle_id)
        current_state = update_object(current_state, replace(target, damage_marked=target.damage_marked + damage))
        events.append({"event_type": "damage_applied", "active_player": active_player, "payload": {"target_instance_id": target_id, "oracle_id": target.oracle_id, "damage": damage, "new_damage_marked": target.damage_marked + damage, "toughness": int(definition.toughness or "0")}})
    if check_sbas:
        current_state, sba_events = apply_state_based_actions(current_state, card_repository, active_player=active_player)
        events.extend(sba_events)
    return current_state, events


def _validate_forked_lightning_assignments(action: CastNonCreatureSpellAction) -> None:
    assignments = action.damage_assignments
    if tuple(target_id for target_id, _ in assignments) != action.target_instance_ids:
        raise ValueError("Forked Lightning assignments must match targets in order")
    if len(assignments) not in {1, 2, 3} or any(amount <= 0 for _, amount in assignments) or sum(amount for _, amount in assignments) != 4:
        raise ValueError("Forked Lightning must divide four positive damage among its targets")


def _damage_assignments_once(state: GameState, card_repository: CardRepository, assignments: tuple[tuple[str, int], ...], active_player: str) -> tuple[GameState, list[dict]]:
    current_state = state
    events: list[dict] = []
    for target_id, damage in assignments:
        target = current_state.objects[target_id]
        definition = card_repository.get(target.oracle_id)
        current_state = update_object(current_state, replace(target, damage_marked=target.damage_marked + damage))
        events.append({"event_type": "damage_applied", "active_player": active_player, "payload": {"target_instance_id": target_id, "oracle_id": target.oracle_id, "damage": damage, "new_damage_marked": target.damage_marked + damage, "toughness": int(definition.toughness or "0")}})
    current_state, sba_events = apply_state_based_actions(current_state, card_repository, active_player=active_player)
    events.extend(sba_events)
    return current_state, events


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
                **zone_change_identity_payload(current_state, instance_id),
            },
        )
    return current_state


def _resolution_player_order(state: GameState) -> tuple[str, ...]:
    """Return active-player-first order without relying on mapping insertion."""
    return (state.turn.active_player,) + tuple(
        player_id for player_id in state.players if player_id != state.turn.active_player
    )


def _move_with_event(
    state: GameState,
    event_log: EventLog,
    *,
    instance_id: str,
    from_zone: str,
    to_zone: str,
    player_id: str,
    active_player: str,
) -> GameState:
    card = state.objects[instance_id]
    next_state = move_object(state, instance_id=instance_id, from_zone=from_zone, to_zone=to_zone, player_id=player_id)
    event_log.append(event_type="object_moved_between_zones", active_player=active_player, payload={"player_id": player_id, "card_instance_id": instance_id, "oracle_id": card.oracle_id, "from_zone": from_zone, "to_zone": to_zone, **zone_change_identity_payload(next_state, instance_id)})
    return next_state


def _discard_specific_cards(
    state: GameState,
    event_log: EventLog,
    *,
    player_id: str,
    instance_ids: tuple[str, ...],
    active_player: str,
) -> GameState:
    current_state = state
    for instance_id in instance_ids:
        if instance_id not in current_state.players[player_id].hand:
            raise ValueError("discarded card must remain in that player's hand")
        current_state = _move_with_event(current_state, event_log, instance_id=instance_id, from_zone="hand", to_zone="graveyard", player_id=player_id, active_player=active_player)
    return current_state


def _shuffle_library(state: GameState, event_log: EventLog, *, player_id: str) -> GameState:
    player = state.players[player_id]
    shuffled = list(player.library)
    cursor_before = state.rng_cursor
    random.Random(state.rng_seed + cursor_before).shuffle(shuffled)
    next_state = update_player(state, replace(player, library=tuple(shuffled)))
    next_state = replace(next_state, rng_cursor=cursor_before + 1)
    event_log.append(event_type="library_shuffled", active_player=player_id, payload={"player_id": player_id, "algorithm": "python_random_mt19937_v1", "rng_cursor_before": cursor_before, "rng_cursor_after": next_state.rng_cursor, "count": len(shuffled)})
    return next_state


def _queue_wave5_decision(
    state: GameState,
    event_log: EventLog,
    *,
    chooser_id: str,
    source_object_id: str,
    kind: str,
    option_ids: tuple[str, ...],
    min_selections: int,
    max_selections: int,
    selection_ordered: bool = False,
    allow_shuffle: bool = False,
    continuation_kind: str,
    continuation: tuple[tuple[str, object], ...] = (),
) -> GameState:
    decision_id = f"{source_object_id}:{kind}:{chooser_id}:{len(event_log.events)}"
    next_state = replace(state, pending_decision=PendingDecision(decision_id=decision_id, chooser_id=chooser_id, kind=kind, source_object_id=source_object_id, option_ids=tuple(option_ids), min_selections=min_selections, max_selections=max_selections, selection_ordered=selection_ordered, allow_shuffle=allow_shuffle, continuation_kind=continuation_kind, continuation=continuation))
    event_log.append(event_type="choice_requested", active_player=chooser_id, payload={"decision_id": decision_id, "chooser_id": chooser_id, "kind": kind, "option_count": len(option_ids)})
    return next_state


def _other_player(state: GameState, player_id: str) -> str:
    for candidate in state.players:
        if candidate != player_id:
            return candidate
    raise ValueError("game state does not contain an opposing player")


def _cleanup_end_of_turn_state(state: GameState) -> GameState:
    updated_players = {
        player_id: replace(player, mana_pool=(), lands_played_this_turn=0, land_play_limit_this_turn=1)
        for player_id, player in state.players.items()
    }
    updated_objects = {
        instance_id: replace(card, damage_marked=0, temporary_power_bonus=0, temporary_toughness_bonus=0)
        for instance_id, card in state.objects.items()
    }
    return replace(state, players=updated_players, objects=updated_objects, forced_block_target_object_id=None, temporary_effects=())


def _add_temporary_effect(
    state: GameState,
    *,
    source_object_id: str,
    target_ids: tuple[str | None, ...],
    power_delta: int = 0,
    toughness_delta: int = 0,
    keywords: tuple[str, ...] = (),
    only_blockable_by_colors: tuple[str, ...] = (),
) -> GameState:
    target_object_ids = tuple(state.objects[instance_id].object_id for instance_id in target_ids if instance_id is not None)
    return replace(state, temporary_effects=state.temporary_effects + (TemporaryEffect(source_object_id=source_object_id, target_object_ids=target_object_ids, power_delta=power_delta, toughness_delta=toughness_delta, granted_keywords=keywords, only_blockable_by_colors=only_blockable_by_colors),))


def _untap_player_battlefield(state: GameState, player_id: str, *, card_repository: CardRepository | None = None, prevent_creatures_and_lands: bool = False) -> GameState:
    current_state = state
    for instance_id in current_state.players[player_id].battlefield:
        card = current_state.objects[instance_id]
        if not card.tapped:
            continue
        if prevent_creatures_and_lands:
            # v0 currently has only creature and land permanents; retain the
            # optional repository hook for a later artifact expansion.
            if card_repository is None:
                continue
            definition = card_repository.get(card.oracle_id)
            if definition.is_creature or definition.is_land:
                continue
        current_state = update_object(current_state, replace(card, tapped=False))
    return current_state
