from __future__ import annotations

from itertools import combinations

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

    for instance_id in player.hand:
        card = state.objects[instance_id]
        card_definition = card_repository.get(card.oracle_id)
        if card_definition.is_creature or card_definition.is_land:
            continue
        requirements = _parse_mana_cost(card_definition.mana_cost)
        if not _can_pay_mana_cost(player.mana_pool, requirements):
            continue
        legal_targets = _legal_noncreature_spell_targets(state, card_repository, instance_id)
        if legal_targets == (None,):
            actions.append(
                CastNonCreatureSpellAction(
                    player_id=state.turn.active_player,
                    card_instance_id=instance_id,
                    target_instance_id=None,
                )
            )
            continue
        for target_instance_id in legal_targets:
            actions.append(
                CastNonCreatureSpellAction(
                    player_id=state.turn.active_player,
                    card_instance_id=instance_id,
                    target_instance_id=target_instance_id,
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
        if attacker_card.has_defender:
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

    assignments = _blocker_assignments(
        tuple(state.combat.attackers),
        tuple(available_blockers),
        state=state,
        card_repository=card_repository,
    )
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
    *,
    state: GameState,
    card_repository: CardRepository,
) -> tuple[dict[str, tuple[str, ...]], ...]:
    assignments: list[dict[str, tuple[str, ...]]] = []

    def build(index: int, current: dict[str, tuple[str, ...]]) -> None:
        if index == len(blockers):
            assignments.append({attacker_id: current[attacker_id] for attacker_id in attackers if current[attacker_id]})
            return

        blocker_id = blockers[index]
        build(index + 1, current)
        for attacker_id in attackers:
            if not can_block_attacker(
                state=state,
                card_repository=card_repository,
                blocker_id=blocker_id,
                attacker_id=attacker_id,
            ):
                continue
            build(
                index + 1,
                {
                    **current,
                    attacker_id: current[attacker_id] + (blocker_id,),
                },
            )

    build(0, {attacker_id: () for attacker_id in attackers})
    return tuple(assignments)


def _legal_noncreature_spell_targets(
    state: GameState,
    card_repository: CardRepository,
    spell_instance_id: str,
) -> tuple[str, ...]:
    spell = state.objects[spell_instance_id]
    card_definition = card_repository.get(spell.oracle_id)
    effect = _supported_targeted_sorcery_effect(card_definition)
    if effect == "draw_two_cards":
        return (None,)
    if effect is None:
        return ()

    legal_targets: list[str] = []
    for player in state.players.values():
        for instance_id in player.battlefield:
            permanent = state.objects[instance_id]
            permanent_definition = card_repository.get(permanent.oracle_id)
            if not permanent_definition.is_creature:
                continue
            if effect == "destroy_tapped_creature" and not permanent.tapped:
                continue
            if effect == "destroy_creature_owner_gains_4_life":
                legal_targets.append(instance_id)
                continue
            if effect == "put_creature_on_top_of_library":
                legal_targets.append(instance_id)
                continue
            if effect == "destroy_tapped_creature":
                legal_targets.append(instance_id)
    return tuple(legal_targets)


def _supported_targeted_sorcery_effect(card_definition) -> str | None:
    if not card_definition.is_sorcery:
        return None
    if card_definition.oracle_text == "Destroy target tapped creature.":
        return "destroy_tapped_creature"
    if card_definition.oracle_text == "Destroy target creature. Its owner gains 4 life.":
        return "destroy_creature_owner_gains_4_life"
    if card_definition.oracle_text == "Draw two cards.":
        return "draw_two_cards"
    if card_definition.oracle_text == "Put target creature on top of its owner's library.":
        return "put_creature_on_top_of_library"
    return None


def can_block_attacker(
    *,
    state: GameState,
    card_repository: CardRepository,
    blocker_id: str,
    attacker_id: str,
) -> bool:
    blocker = state.objects[blocker_id]
    attacker = state.objects[attacker_id]
    blocker_definition = card_repository.get(blocker.oracle_id)
    attacker_definition = card_repository.get(attacker.oracle_id)

    if attacker_definition.has_flying and not blocker_definition.has_flying:
        return False
    return True


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
