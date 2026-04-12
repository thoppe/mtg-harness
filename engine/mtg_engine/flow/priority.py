from __future__ import annotations

from itertools import combinations

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    AdvanceStepAction,
    CastCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.state.models import GameState


def enumerate_legal_actions(state: GameState, card_repository: CardRepository) -> tuple[object, ...]:
    if state.turn.step == "precombat_main_step":
        if state.turn.priority_player != state.turn.active_player:
            return _enumerate_non_active_priority_actions(state)
        return _enumerate_active_precombat_main_actions(state, card_repository)

    if state.turn.step == "declare_attackers_step":
        return _enumerate_declare_attackers_actions(state, card_repository)

    if state.turn.step == "declare_blockers_step":
        return _enumerate_declare_blockers_actions(state, card_repository)

    return ()


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
        if len(card_definition.produced_mana) == 1 and not permanent.tapped:
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
        requirements = _parse_mana_cost(card_definition.mana_cost)
        if _can_pay_mana_cost(player.mana_pool, requirements):
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


def _enumerate_declare_attackers_actions(
    state: GameState,
    card_repository: CardRepository,
) -> tuple[object, ...]:
    if state.turn.priority_player != state.turn.active_player:
        return ()

    legal_attackers = []
    for instance_id in state.players[state.turn.active_player].battlefield:
        attacker = state.objects[instance_id]
        attacker_card = card_repository.get(attacker.oracle_id)
        if not attacker_card.is_creature or attacker.tapped:
            continue
        if attacker.entered_battlefield_turn == state.turn.turn_number:
            continue
        legal_attackers.append(instance_id)

    actions = [
        DeclareAttackersAction(
            player_id=state.turn.active_player,
            attacker_ids=attacker_ids,
        )
        for attacker_ids in _ordered_subsets(tuple(legal_attackers))
    ]
    return tuple(actions)


def _enumerate_declare_blockers_actions(
    state: GameState,
    card_repository: CardRepository,
) -> tuple[object, ...]:
    if state.combat is None:
        return ()
    if state.turn.priority_player != state.combat.defending_player:
        return ()

    available_blockers = []
    for instance_id in state.players[state.combat.defending_player].battlefield:
        blocker = state.objects[instance_id]
        blocker_card = card_repository.get(blocker.oracle_id)
        if blocker_card.is_creature and not blocker.tapped:
            available_blockers.append(instance_id)

    assignments = _blocker_assignments(tuple(state.combat.attackers), tuple(available_blockers))
    return tuple(
        DeclareBlockersAction(
            player_id=state.combat.defending_player,
            blockers=assignment,
        )
        for assignment in assignments
    )


def _ordered_subsets(values: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    subsets = [()]
    for subset_size in range(1, len(values) + 1):
        subsets.extend(combinations(values, subset_size))
    return tuple(subsets)


def _blocker_assignments(
    attackers: tuple[str, ...],
    blockers: tuple[str, ...],
) -> tuple[dict[str, tuple[str, ...]], ...]:
    assignments: list[dict[str, tuple[str, ...]]] = []

    def build(index: int, current: dict[str, tuple[str, ...]]) -> None:
        if index == len(blockers):
            assignments.append({attacker_id: current[attacker_id] for attacker_id in attackers if current[attacker_id]})
            return

        blocker_id = blockers[index]
        build(index + 1, current)
        for attacker_id in attackers:
            build(
                index + 1,
                {
                    **current,
                    attacker_id: current[attacker_id] + (blocker_id,),
                },
            )

    build(0, {attacker_id: () for attacker_id in attackers})
    return tuple(assignments)


def _parse_mana_cost(mana_cost: str) -> dict[str, int]:
    requirements = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "generic": 0}
    if not mana_cost:
        return requirements

    symbols = mana_cost.replace("{", " ").replace("}", " ").split()
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
