from __future__ import annotations

from dataclasses import replace

from mtg_engine.cards.repository import CardRepository
from mtg_engine.state.models import CombatState, GameState
from mtg_engine.state.zones import move_object, update_object, update_player


def tap_attackers(state: GameState, attacker_ids: tuple[str, ...]) -> GameState:
    current_state = state
    for attacker_id in attacker_ids:
        attacker = current_state.objects[attacker_id]
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
        attacker_card = card_repository.get(attacker.oracle_id)
        attacker_power = int(attacker_card.power or "0")
        attacker_toughness = int(attacker_card.toughness or "0")

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

        blocker_id = blockers[0]
        blocker = current_state.objects[blocker_id]
        blocker_card = card_repository.get(blocker.oracle_id)
        blocker_power = int(blocker_card.power or "0")
        blocker_toughness = int(blocker_card.toughness or "0")

        events.append(
            {
                "event_type": "combat_damage_assigned",
                "active_player": combat.attacking_player,
                "payload": {
                    "attacker_id": attacker_id,
                    "blocker_id": blocker_id,
                    "attacker_damage": attacker_power,
                    "blocker_damage": blocker_power,
                },
            }
        )
        events.append(
            {
                "event_type": "combat_damage_applied",
                "active_player": combat.attacking_player,
                "payload": {
                    "attacker_id": attacker_id,
                    "blocker_id": blocker_id,
                    "attacker_damage": attacker_power,
                    "blocker_damage": blocker_power,
                },
            }
        )

        destroyed_ids: list[str] = []
        if attacker_power >= blocker_toughness:
            destroyed_ids.append(blocker_id)
        if blocker_power >= attacker_toughness:
            destroyed_ids.append(attacker_id)

        if destroyed_ids:
            events.append(
                {
                    "event_type": "state_based_actions_checked",
                    "active_player": combat.attacking_player,
                    "payload": {
                        "destroyed_ids": list(destroyed_ids),
                    },
                }
            )

        for destroyed_id in destroyed_ids:
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
                    "active_player": combat.attacking_player,
                    "payload": {
                        "card_instance_id": destroyed_id,
                        "oracle_id": destroyed_object.oracle_id,
                    },
                }
            )
            events.append(
                {
                    "event_type": "object_moved_between_zones",
                    "active_player": combat.attacking_player,
                    "payload": {
                        "player_id": destroyed_object.owner_id,
                        "card_instance_id": destroyed_id,
                        "oracle_id": destroyed_object.oracle_id,
                        "from_zone": "battlefield",
                        "to_zone": "graveyard",
                    },
                }
            )

    return clear_combat_state(current_state), events
