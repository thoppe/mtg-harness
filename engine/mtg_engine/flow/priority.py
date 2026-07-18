from __future__ import annotations

from itertools import combinations
from dataclasses import replace

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    AdvanceStepAction,
    CastCreatureSpellAction,
    CastNonCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
    ResolveChoiceAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.cards.implementations import effect_key_for
from mtg_engine.state.models import GameState
from mtg_engine.rules.characteristics import effective_power, has_keyword, only_blockable_by_colors


def enumerate_legal_actions(state: GameState, card_repository: CardRepository) -> tuple[object, ...]:
    if state.pending_decision is not None:
        return tuple(
            ResolveChoiceAction(
                player_id=state.pending_decision.chooser_id,
                decision_id=state.pending_decision.decision_id,
                selected_instance_id=option_id,
            )
            for option_id in state.pending_decision.option_ids
        ) + (
            ResolveChoiceAction(
                player_id=state.pending_decision.chooser_id,
                decision_id=state.pending_decision.decision_id,
                selected_instance_id=None,
            ),
        )
    if state.stack_entries:
        return _enumerate_instant_priority_actions(state, card_repository)
    if state.turn.step == "precombat_main_step":
        if state.turn.priority_player != state.turn.active_player:
            return _enumerate_non_active_priority_actions(state)
        return _enumerate_active_precombat_main_actions(state, card_repository)

    if state.turn.step == "declare_attackers_step":
        if state.combat is not None:
            if not _any_instant_available(state, card_repository):
                blockers_state = replace(state, turn=replace(state.turn, step="declare_blockers_step", priority_player=state.combat.defending_player))
                return _enumerate_declare_blockers_actions(blockers_state, card_repository)
            return _enumerate_instant_priority_actions(state, card_repository)
        return _enumerate_declare_attackers_actions(state, card_repository)

    if state.turn.step == "declare_blockers_step":
        return _enumerate_declare_blockers_actions(state, card_repository)

    return ()


def _any_instant_available(state: GameState, card_repository: CardRepository) -> bool:
    return any(
        card_repository.get(state.objects[instance_id].oracle_id).is_instant
        for player in state.players.values()
        for instance_id in player.hand
    )


def _enumerate_active_precombat_main_actions(
    state: GameState,
    card_repository: CardRepository,
) -> tuple[object, ...]:
    player = state.players[state.turn.active_player]
    actions: list[object] = []

    if player.lands_played_this_turn < player.land_play_limit_this_turn:
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
        if legal_targets == ((),):
            actions.append(
                CastNonCreatureSpellAction(
                    player_id=state.turn.active_player,
                    card_instance_id=instance_id,
                    target_instance_ids=(),
                )
            )
            continue
        for target_instance_ids in legal_targets:
            actions.append(
                CastNonCreatureSpellAction(
                    player_id=state.turn.active_player,
                    card_instance_id=instance_id,
                    target_instance_ids=target_instance_ids,
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
    # The v0 slice has no instant-speed spells or abilities yet, but the
    # non-active player must still be able to pass so that a spell can leave
    # the stack after both players pass consecutively.
    return (PassPriorityAction(player_id=state.turn.priority_player),)


def _enumerate_instant_priority_actions(state: GameState, card_repository: CardRepository) -> tuple[object, ...]:
    player = state.players[state.turn.priority_player]
    actions: list[object] = []
    for instance_id in player.battlefield:
        permanent = state.objects[instance_id]
        definition = card_repository.get(permanent.oracle_id)
        if len(definition.produced_mana) == 1 and not permanent.tapped:
            actions.append(ActivateManaAbilityAction(player_id=player.player_id, source_instance_id=instance_id))
    for instance_id in player.hand:
        card = state.objects[instance_id]
        definition = card_repository.get(card.oracle_id)
        if not definition.is_instant or not _can_pay_mana_cost(player.mana_pool, _parse_mana_cost(definition.mana_cost)):
            continue
        for target_ids in _legal_noncreature_spell_targets(state, card_repository, instance_id):
            actions.append(CastNonCreatureSpellAction(player_id=player.player_id, card_instance_id=instance_id, target_instance_ids=target_ids))
    actions.append(PassPriorityAction(player_id=player.player_id))
    return tuple(actions)


def _enumerate_declare_attackers_actions(
    state: GameState,
    card_repository: CardRepository,
) -> tuple[object, ...]:
    if state.turn.priority_player != state.turn.active_player:
        return ()

    legal_attackers = []
    for instance_id in state.players[state.turn.active_player].battlefield:
        if attacker_attack_rejection_reason(
            state=state,
            card_repository=card_repository,
            attacker_id=instance_id,
        ) is not None:
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
            assignment = {attacker_id: current[attacker_id] for attacker_id in attackers if current[attacker_id]}
            if any(
                card_repository.get(state.objects[attacker_id].oracle_id).name in {"Charging Rhino", "Stalking Tiger"}
                and len(blocker_ids) > 1
                for attacker_id, blocker_ids in assignment.items()
            ):
                return
            forced_target = state.forced_block_target_object_id
            target_id = next((instance_id for instance_id in attackers if state.objects[instance_id].object_id == forced_target), None)
            if target_id is not None:
                for blocker_id in blockers:
                    if blocker_attack_rejection_reason(state=state, card_repository=card_repository, blocker_id=blocker_id, attacker_id=target_id) is None and blocker_id not in assignment.get(target_id, ()):
                        return
            assignments.append(assignment)
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


def attacker_attack_rejection_reason(
    *,
    state: GameState,
    card_repository: CardRepository,
    attacker_id: str,
) -> str | None:
    if attacker_id not in state.players[state.turn.active_player].battlefield:
        return "attacker must be on the active player's battlefield"
    attacker = state.objects[attacker_id]
    attacker_card = card_repository.get(attacker.oracle_id)
    if not attacker_card.is_creature:
        return "only creatures can attack"
    if has_keyword(state, card_repository, attacker_id, "Defender"):
        return "creature with defender cannot attack"
    if attacker.tapped:
        return "attacker is already tapped"
    if attacker.entered_battlefield_turn == state.turn.turn_number:
        return "summoning-sick creature cannot attack in v0"
    if attacker_card.name == "Deep-Sea Serpent" and not any(
        card_repository.get(state.objects[land_id].oracle_id).has_subtype("Island")
        for land_id in state.players[_other_player_id(state, state.turn.active_player)].battlefield
    ):
        return "Deep-Sea Serpent cannot attack unless defending player controls an Island"
    return None


def _legal_noncreature_spell_targets(
    state: GameState,
    card_repository: CardRepository,
    spell_instance_id: str,
) -> tuple[tuple[str, ...], ...]:
    spell = state.objects[spell_instance_id]
    card_definition = card_repository.get(spell.oracle_id)
    effect = _supported_targeted_sorcery_effect(card_definition)
    if effect in {"draw_two_cards", "gain_4_life", "gain_life_per_forest", "additional_three_land_plays", "tutor_sorcery_to_top", "tutor_creature_to_top", "destroy_all_lands", "destroy_all_creatures", "controlled_creatures_get_0_3_until_end_of_turn", "controlled_creatures_get_1_1_until_end_of_turn", "white_controlled_creatures_get_2_0_until_end_of_turn", "green_controlled_creatures_gain_forestwalk_until_end_of_turn", "black_controlled_creatures_only_blockable_by_black_until_end_of_turn", "controlled_creatures_gain_reach_until_end_of_turn"}:
        return ((),)
    if effect is None:
        return ()
    if effect == "damage_target_player":
        return tuple((player_id,) for player_id in state.players)
    if effect == "target_player_discards_two":
        return tuple((player_id,) for player_id in state.players)
    if effect == "destroy_all_creatures_target_opponent_you_lose_2_per_creature":
        return tuple(
            (player_id,)
            for player_id in state.players
            if player_id != state.turn.active_player
        )

    legal_targets: list[tuple[str, ...]] = []
    land_target_ids: list[str] = []
    if effect == "damage_any_target":
        legal_targets.extend((player_id,) for player_id in state.players)
    tap_target_ids: list[str] = []
    for player in state.players.values():
        for instance_id in player.battlefield:
            permanent = state.objects[instance_id]
            permanent_definition = card_repository.get(permanent.oracle_id)
            if effect in {"destroy_target_land", "destroy_two_target_lands"}:
                if permanent_definition.is_land:
                    if effect == "destroy_target_land":
                        legal_targets.append((instance_id,))
                    else:
                        land_target_ids.append(instance_id)
                continue
            if effect == "return_creature_to_hand_and_draw_one":
                if permanent_definition.is_creature:
                    legal_targets.append((instance_id,))
                continue
            if effect == "tap_up_to_three_nonflying_creatures":
                if permanent_definition.is_creature and not permanent_definition.has_flying:
                    tap_target_ids.append(instance_id)
                continue
            if not permanent_definition.is_creature:
                continue
            if effect == "damage_any_target":
                legal_targets.append((instance_id,))
                continue
            if effect == "destroy_tapped_creature" and not permanent.tapped:
                continue
            if effect == "destroy_creature_owner_gains_4_life":
                legal_targets.append((instance_id,))
                continue
            if effect == "destroy_nonblack_creature" and not permanent_definition.is_black:
                legal_targets.append((instance_id,))
                continue
            if effect == "put_creature_on_top_of_library":
                legal_targets.append((instance_id,))
                continue
            if effect == "destroy_tapped_creature":
                legal_targets.append((instance_id,))
    if effect == "destroy_two_target_lands":
        legal_targets.extend(combinations(tuple(land_target_ids), 2))
    if effect == "tap_up_to_three_nonflying_creatures":
        legal_targets.append(())
        for target_count in range(1, min(3, len(tap_target_ids)) + 1):
            legal_targets.extend(combinations(tuple(tap_target_ids), target_count))
    return tuple(legal_targets)


def _supported_targeted_sorcery_effect(card_definition) -> str | None:
    return effect_key_for(card_definition.oracle_id) if (card_definition.is_sorcery or card_definition.is_instant) else None


def can_block_attacker(
    *,
    state: GameState,
    card_repository: CardRepository,
    blocker_id: str,
    attacker_id: str,
) -> bool:
    return blocker_attack_rejection_reason(
        state=state,
        card_repository=card_repository,
        blocker_id=blocker_id,
        attacker_id=attacker_id,
    ) is None


def blocker_attack_rejection_reason(
    *,
    state: GameState,
    card_repository: CardRepository,
    blocker_id: str,
    attacker_id: str,
) -> str | None:
    blocker = state.objects[blocker_id]
    attacker = state.objects[attacker_id]
    blocker_definition = card_repository.get(blocker.oracle_id)
    attacker_definition = card_repository.get(attacker.oracle_id)

    if not blocker_definition.is_creature:
        return "only creatures can block"
    if blocker.tapped:
        return "tapped creature cannot block"
    if has_keyword(state, card_repository, attacker_id, "Swampwalk") and _player_controls_swamp(
        state,
        card_repository,
        player_id=blocker.owner_id,
    ):
        return "blocker cannot block the selected attacker"
    if has_keyword(state, card_repository, attacker_id, "Forestwalk") and _player_controls_subtype(
        state, card_repository, player_id=blocker.controller_id, subtype="Forest"
    ):
        return "blocker cannot block the selected attacker"
    if has_keyword(state, card_repository, attacker_id, "Flying") and not (
        has_keyword(state, card_repository, blocker_id, "Flying") or has_keyword(state, card_repository, blocker_id, "Reach")
    ):
        return "blocker cannot block the selected attacker"
    allowed_colors = only_blockable_by_colors(state, attacker_id)
    if allowed_colors and not any(blocker_definition.has_color(color) for color in allowed_colors):
        return "blocker cannot block the selected attacker"
    if attacker_definition.name in {"Phantom Warrior"}:
        return "blocker cannot block the selected attacker"
    if attacker_definition.name in {"Sacred Knight"} and (blocker_definition.has_color("B") or blocker_definition.has_color("R")):
        return "blocker cannot block the selected attacker"
    if attacker_definition.name == "Fleet-Footed Monk" and effective_power(state, card_repository, blocker_id) >= 2:
        return "blocker cannot block the selected attacker"
    if blocker_definition.name in {"Craven Giant", "Craven Knight", "Hulking Cyclops", "Hulking Goblin", "Jungle Lion"}:
        return "creature cannot block"
    if blocker_definition.name == "Cloud Dragon" and not has_keyword(state, card_repository, attacker_id, "Flying"):
        return "Cloud Dragon can block only creatures with flying"
    return None


def _player_controls_swamp(
    state: GameState,
    card_repository: CardRepository,
    *,
    player_id: str,
) -> bool:
    return any(
        card_repository.get(state.objects[instance_id].oracle_id).name == "Swamp"
        for instance_id in state.players[player_id].battlefield
    )


def _player_controls_subtype(state: GameState, card_repository: CardRepository, *, player_id: str, subtype: str) -> bool:
    return any(
        card_repository.get(state.objects[instance_id].oracle_id).has_subtype(subtype)
        for instance_id in state.players[player_id].battlefield
    )


def _other_player_id(state: GameState, player_id: str) -> str:
    return next(candidate for candidate in state.players if candidate != player_id)


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
