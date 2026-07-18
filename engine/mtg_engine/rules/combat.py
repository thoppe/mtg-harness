from __future__ import annotations

from dataclasses import replace

from mtg_engine.cards.repository import CardRepository
from mtg_engine.state.models import CombatState, GameOutcome, GameState, StackEntry
from mtg_engine.state.zones import move_object, update_object, update_player, zone_change_identity_payload
from mtg_engine.rules.characteristics import effective_power, effective_toughness, has_keyword


def tap_attackers(
    state: GameState,
    attacker_ids: tuple[str, ...],
    card_repository: CardRepository,
) -> GameState:
    current_state = state
    for attacker_id in attacker_ids:
        attacker = current_state.objects[attacker_id]
        if has_keyword(current_state, card_repository, attacker_id, "Vigilance"):
            continue
        current_state = update_object(current_state, replace(attacker, tapped=True))
    return current_state


def with_combat_state(
    state: GameState,
    *,
    attacking_player: str,
    defending_player: str,
    attackers: tuple[str, ...],
    blockers: dict[str, tuple[str, ...]],
) -> GameState:
    return replace(
        state,
        combat=CombatState(
            attacking_player=attacking_player,
            defending_player=defending_player,
            attackers=attackers,
            blockers=blockers,
            was_attacked=bool(attackers),
        ),
    )


def clear_combat_state(state: GameState) -> GameState:
    return replace(state, combat=None)


def apply_combat_damage(state: GameState, card_repository: CardRepository) -> tuple[GameState, list[dict]]:
    if state.combat is None:
        raise ValueError("combat damage requires an active combat state")

    current_state = state
    events: list[dict] = []
    combat = state.combat

    for attacker_id in combat.attackers:
        blockers = combat.blockers.get(attacker_id, ())
        attacker = current_state.objects[attacker_id]
        attacker_power = effective_power(current_state, card_repository, attacker_id)

        if not blockers:
            defending_player = current_state.players[combat.defending_player]
            updated_player = replace(defending_player, life_total=defending_player.life_total - attacker_power)
            current_state = update_player(current_state, updated_player)
            events.append(
                {
                    "event_type": "combat_damage_applied",
                    "active_player": combat.attacking_player,
                    "payload": {
                        "source_instance_id": attacker_id,
                        "target_player_id": combat.defending_player,
                        "damage": attacker_power,
                    },
                }
            )
            events.append(
                {
                    "event_type": "life_total_changed",
                    "active_player": combat.attacking_player,
                    "payload": {
                        "player_id": combat.defending_player,
                        "life_total": updated_player.life_total,
                    },
                }
            )
            continue

        blocker_damage_assignments: list[dict] = []
        remaining_attacker_damage = attacker_power
        total_blocker_damage = 0

        for blocker_id in blockers:
            blocker = current_state.objects[blocker_id]
            blocker_card = card_repository.get(blocker.oracle_id)
            blocker_power = effective_power(current_state, card_repository, blocker_id)
            blocker_toughness = effective_toughness(current_state, card_repository, blocker_id)
            lethal_damage = max(0, blocker_toughness - blocker.damage_marked)
            attacker_damage_to_blocker = min(remaining_attacker_damage, lethal_damage)
            remaining_attacker_damage -= attacker_damage_to_blocker
            total_blocker_damage += blocker_power
            blocker_damage_assignments.append(
                {
                    "blocker_id": blocker_id,
                    "attacker_damage": attacker_damage_to_blocker,
                    "blocker_damage": blocker_power,
                }
            )
            current_state = update_object(
                current_state,
                replace(blocker, damage_marked=blocker.damage_marked + attacker_damage_to_blocker),
            )

        current_state = update_object(
            current_state,
            replace(attacker, damage_marked=attacker.damage_marked + total_blocker_damage),
        )
        events.append(
            {
                "event_type": "combat_damage_assigned",
                "active_player": combat.attacking_player,
                "payload": {
                    "attacker_id": attacker_id,
                    "assignments": blocker_damage_assignments,
                },
            }
        )
        events.append(
            {
                "event_type": "combat_damage_applied",
                "active_player": combat.attacking_player,
                "payload": {
                    "attacker_id": attacker_id,
                    "assignments": blocker_damage_assignments,
                },
            }
        )

    current_state, sba_events = apply_state_based_actions(current_state, card_repository, active_player=combat.attacking_player)
    events.extend(sba_events)
    return clear_combat_state(current_state), events


def apply_state_based_actions(
    state: GameState,
    card_repository: CardRepository,
    *,
    active_player: str,
) -> tuple[GameState, list[dict]]:
    destroyed_objects: list[dict] = []
    losing_players = tuple(player.player_id for player in state.players.values() if player.life_total <= 0)
    for instance_id in _battlefield_object_ids(state):
        obj = state.objects[instance_id]
        card = card_repository.get(obj.oracle_id)
        if not card.is_creature:
            continue
        toughness = effective_toughness(state, card_repository, instance_id)
        if obj.damage_marked >= toughness:
            destroyed_objects.append(
                {
                    "card_instance_id": instance_id,
                    "source_object_id": obj.object_id,
                    "owner_id": obj.owner_id,
                    "controller_id": obj.controller_id,
                    "oracle_id": obj.oracle_id,
                    "reason": "lethal_damage",
                    "damage_marked": obj.damage_marked,
                    "toughness": toughness,
                }
            )

    events = [
        {
            "event_type": "state_based_actions_checked",
            "active_player": active_player,
            "payload": {
                "destroyed_ids": [item["card_instance_id"] for item in destroyed_objects],
                "destroyed": destroyed_objects,
            },
        }
    ]
    current_state = state
    if losing_players:
        surviving_players = tuple(player_id for player_id in state.players if player_id not in losing_players)
        winner_id = surviving_players[0] if len(surviving_players) == 1 else None
        current_state = replace(
            current_state,
            outcome=GameOutcome(
                status="completed",
                winner_id=winner_id,
                loser_ids=losing_players,
                reason="life_total_zero_or_less",
            ),
        )
        events.append(
            {
                "event_type": "game_ended",
                "active_player": active_player,
                "payload": {"winner_id": winner_id, "loser_ids": list(losing_players), "reason": "life_total_zero_or_less"},
            }
        )
    for destroyed in destroyed_objects:
        destroyed_id = destroyed["card_instance_id"]
        destroyed_object = current_state.objects[destroyed_id]
        current_state = move_object(
            current_state,
            instance_id=destroyed_id,
            from_zone="battlefield",
            to_zone="graveyard",
            player_id=destroyed_object.owner_id,
        )
        events.append(
            {
                "event_type": "permanent_destroyed",
                "active_player": active_player,
                "payload": {
                    "card_instance_id": destroyed_id,
                    "oracle_id": destroyed_object.oracle_id,
                    "reason": destroyed["reason"],
                    "damage_marked": destroyed["damage_marked"],
                    "toughness": destroyed["toughness"],
                },
            }
        )
        events.append(
            {
                "event_type": "object_moved_between_zones",
                "active_player": active_player,
                "payload": {
                    "player_id": destroyed_object.owner_id,
                    "card_instance_id": destroyed_id,
                    "oracle_id": destroyed_object.oracle_id,
                    "from_zone": "battlefield",
                    "to_zone": "graveyard",
                    **zone_change_identity_payload(current_state, destroyed_id),
                },
            }
        )
    if current_state.outcome.status != "completed":
        current_state, trigger_events = queue_death_triggers(
            current_state,
            destroyed_objects,
            active_player=active_player,
        )
        events.extend(trigger_events)
    return current_state, events


ALABASTER_DRAGON_ORACLE_ID = "2392a41a-59d3-4749-be94-4d9df0af9c4c"


def queue_death_triggers(
    state: GameState,
    destroyed_objects: list[dict],
    *,
    active_player: str,
) -> tuple[GameState, list[dict]]:
    """Put the currently supported dies triggers onto the stack.

    This deliberately records the object's pre-zone-change identity, because
    the source has already become a new object in its owner's graveyard when
    the trigger is placed on the stack.
    """
    trigger_entries: list[StackEntry] = []
    events: list[dict] = []
    player_order = (active_player,) + tuple(
        player_id for player_id in state.players if player_id != active_player
    )
    ordered_destroyed = sorted(
        destroyed_objects,
        key=lambda destroyed: player_order.index(destroyed["controller_id"]),
    )
    for destroyed in ordered_destroyed:
        if destroyed["oracle_id"] != ALABASTER_DRAGON_ORACLE_ID:
            continue
        trigger_entries.append(
            StackEntry(
                card_instance_id=destroyed["card_instance_id"],
                controller_id=destroyed["controller_id"],
                entry_kind="alabaster_dragon_death_trigger",
                source_object_id=destroyed["source_object_id"],
                source_oracle_id=destroyed["oracle_id"],
                owner_id=destroyed["owner_id"],
                expected_graveyard_object_id=state.objects[destroyed["card_instance_id"]].object_id,
            )
        )
        events.append(
            {
                "event_type": "triggered_ability_put_on_stack",
                "active_player": active_player,
                "payload": {
                    "ability_key": "alabaster_dragon_death_trigger",
                    "card_instance_id": destroyed["card_instance_id"],
                    "oracle_id": destroyed["oracle_id"],
                    "owner_id": destroyed["owner_id"],
                    "controller_id": destroyed["controller_id"],
                    "source_object_id": destroyed["source_object_id"],
                    "expected_graveyard_object_id": state.objects[destroyed["card_instance_id"]].object_id,
                },
            }
        )
    if not trigger_entries:
        return state, events
    return (
        replace(
            state,
            stack_entries=state.stack_entries + tuple(trigger_entries),
            consecutive_passes=0,
            turn=replace(state.turn, priority_player=active_player),
        ),
        events,
    )


def _battlefield_object_ids(state: GameState) -> tuple[str, ...]:
    all_ids: list[str] = []
    for player in state.players.values():
        all_ids.extend(player.battlefield)
    return tuple(all_ids)
