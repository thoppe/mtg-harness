from __future__ import annotations

from itertools import combinations, permutations

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    ActivateAbilityAction,
    AdvanceStepAction,
    AdvanceTurnAction,
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
        return _enumerate_pending_decision_actions(state.pending_decision)
    if state.stack_entries:
        return _enumerate_instant_priority_actions(state, card_repository)
    if state.turn.step == "precombat_main_step":
        if state.turn.priority_player != state.turn.active_player:
            return _enumerate_non_active_priority_actions(state)
        return _enumerate_active_precombat_main_actions(state, card_repository)

    if state.turn.step == "declare_attackers_step":
        if state.combat is not None:
            return _enumerate_instant_priority_actions(state, card_repository)
        return _enumerate_declare_attackers_actions(state, card_repository)

    if state.turn.step == "declare_blockers_step":
        return _enumerate_declare_blockers_actions(state, card_repository)

    if state.turn.step == "combat_damage_step":
        return (
            AdvanceTurnAction(player_id=state.turn.active_player),
        )

    return ()


def _enumerate_pending_decision_actions(decision) -> tuple[ResolveChoiceAction, ...]:
    """Enumerate only the declarations permitted by a pending decision.

    This remains intentionally bounded by the named Wave 5 effects: it is a
    rules-facing action surface, not a generic power-set interface for every
    future hidden-zone effect.
    """
    if decision.kind == "draw_up_to_two":
        return tuple(
            ResolveChoiceAction(
                player_id=decision.chooser_id,
                decision_id=decision.decision_id,
                declared_count=count,
            )
            for count in range(3)
        )

    options = decision.option_ids
    lower_bound = 0 if not options else decision.min_selections
    upper_bound = min(decision.max_selections, len(options))
    actions: list[ResolveChoiceAction] = []
    selection_counts = decision.selection_counts or tuple(range(lower_bound, upper_bound + 1))
    for selection_count in selection_counts:
        if selection_count < lower_bound or selection_count > upper_bound:
            continue
        selections = (
            permutations(options, selection_count)
            if decision.selection_ordered
            else combinations(options, selection_count)
        )
        for selection in selections:
            if decision.selection_ordered:
                actions.append(
                    ResolveChoiceAction(
                        player_id=decision.chooser_id,
                        decision_id=decision.decision_id,
                        ordered_instance_ids=tuple(selection),
                    )
                )
            else:
                actions.append(
                    ResolveChoiceAction(
                        player_id=decision.chooser_id,
                        decision_id=decision.decision_id,
                        selected_instance_ids=tuple(selection),
                    )
                )
    if decision.allow_shuffle:
        actions = [
            ResolveChoiceAction(
                player_id=action.player_id,
                decision_id=action.decision_id,
                selected_instance_ids=action.selected_instance_ids,
                ordered_instance_ids=action.ordered_instance_ids,
                shuffle_library=shuffle_library,
            )
            for action in actions
            for shuffle_library in (False, True)
        ]
    return tuple(actions)


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

    actions.extend(_enumerate_activated_abilities(state, card_repository))

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
        if card_definition.is_creature or card_definition.is_land or card_definition.is_instant:
            continue
        legal_targets = _legal_noncreature_spell_targets(state, card_repository, instance_id)
        effect = _supported_targeted_sorcery_effect(card_definition)
        x_values = range(len(player.mana_pool) + 1) if effect in {"prosperity", "blaze", "earthquake"} else (None,)
        sacrifice_ids = tuple(
            permanent_id for permanent_id in player.battlefield
            if (definition := card_repository.get(state.objects[permanent_id].oracle_id)).is_creature and definition.has_color("G")
        ) if effect == "natural_order" else (
            tuple(permanent_id for permanent_id in player.battlefield if card_repository.get(state.objects[permanent_id].oracle_id).is_creature)
            if effect == "final_strike" else (None,)
        )
        for chosen_x in x_values:
            if not _can_pay_mana_cost(player.mana_pool, _parse_mana_cost(card_definition.mana_cost, chosen_x=chosen_x or 0)):
                continue
            for sacrifice_id in sacrifice_ids:
                for target_instance_ids in legal_targets:
                    allocations = _forked_lightning_allocations(target_instance_ids) if effect == "forked_lightning" else ((),)
                    for allocation in allocations:
                        actions.append(CastNonCreatureSpellAction(player_id=state.turn.active_player, card_instance_id=instance_id, target_instance_ids=target_instance_ids, chosen_x=chosen_x, additional_cost_instance_id=sacrifice_id, damage_assignments=allocation))

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
    actions.extend(_enumerate_activated_abilities(state, card_repository))
    for instance_id in player.hand:
        card = state.objects[instance_id]
        definition = card_repository.get(card.oracle_id)
        if not definition.is_instant or not instant_timing_is_legal(state, definition, player.player_id) or not _can_pay_mana_cost(player.mana_pool, _parse_mana_cost(definition.mana_cost)):
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

    forced_attack = any(
        effect.kind == "must_attack_source" and effect.player_id == state.turn.active_player
        for effect in state.delayed_turn_effects
    )

    actions = [
        DeclareAttackersAction(
            player_id=state.turn.active_player,
            attacker_ids=attacker_ids,
        )
        for attacker_ids in _ordered_subsets(tuple(legal_attackers))
        if not forced_attack or set(attacker_ids) == set(legal_attackers)
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
    if attacker.entered_battlefield_turn == state.turn.turn_number and not has_keyword(
        state, card_repository, attacker_id, "Haste"
    ):
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
    if effect == "mystic_denial":
        return tuple((entry.card_instance_id,) for entry in state.stack_entries if card_repository.get(state.objects[entry.card_instance_id].oracle_id).is_creature or card_repository.get(state.objects[entry.card_instance_id].oracle_id).is_sorcery)
    if effect in {"draw_two_cards", "gain_4_life", "gain_life_per_forest", "additional_three_land_plays", "tutor_sorcery_to_top", "tutor_creature_to_top", "destroy_all_lands", "destroy_all_creatures", "controlled_creatures_get_0_3_until_end_of_turn", "controlled_creatures_get_1_1_until_end_of_turn", "white_creatures_get_2_0_until_end_of_turn", "green_controlled_creatures_gain_forestwalk_until_end_of_turn", "black_controlled_creatures_only_blockable_by_black_until_end_of_turn", "controlled_creatures_gain_reach_until_end_of_turn", "flux", "natural_order", "ancestral_memories", "prosperity", "temporary_truce", "winds_of_change", "untamed_wilds", "gift_of_estates", "cruel_bargain", "cruel_tutor", "natures_lore", "omen", "earthquake", "devastation", "last_chance", "blessed_reversal", "deep_wood", "harsh_justice", "scorching_winds"}:
        return ((),)
    if effect is None:
        return ()
    if effect == "damage_target_player":
        return tuple((player_id,) for player_id in state.players)
    if effect == "target_player_discards_two":
        return tuple((player_id,) for player_id in state.players)
    if effect in {"false_peace", "taunt"}:
        return tuple((player_id,) for player_id in state.players)
    if effect == "destroy_all_creatures_target_opponent_you_lose_2_per_creature":
        return tuple(
            (player_id,)
            for player_id in state.players
            if player_id != state.turn.active_player
        )
    if effect in {"look_at_opponent_hand_draw_one", "balance_of_power", "withering_gaze", "mind_knives", "baleful_stare", "starlight", "cruel_fate", "exhaustion"}:
        return tuple(
            (player_id,)
            for player_id in state.players
            if player_id != state.turn.active_player
        )

    legal_targets: list[tuple[str, ...]] = []
    land_target_ids: list[str] = []
    if effect in {"damage_any_target", "blaze"}:
        legal_targets.extend((player_id,) for player_id in state.players)
    tap_target_ids: list[str] = []
    for player in state.players.values():
        for instance_id in player.battlefield:
            permanent = state.objects[instance_id]
            permanent_definition = card_repository.get(permanent.oracle_id)
            if effect in {"destroy_target_land", "destroy_two_target_lands", "fire_snake_death"}:
                if permanent_definition.is_land:
                    if effect in {"destroy_target_land", "fire_snake_death"}:
                        legal_targets.append((instance_id,))
                    else:
                        land_target_ids.append(instance_id)
                continue
            if effect in {"return_creature_to_hand_and_draw_one", "manowar_etb", "command_of_unsummoning"}:
                if permanent_definition.is_creature:
                    legal_targets.append((instance_id,))
                continue
            if effect in {
                "all_able_creatures_block_target_this_turn",
                "target_creature_gets_3_3_and_flying_until_end_of_turn",
                "target_creature_gains_flying_and_draw_one",
            }:
                if permanent_definition.is_creature:
                    legal_targets.append((instance_id,))
                continue
            if effect == "tap_up_to_three_nonflying_creatures":
                if permanent_definition.is_creature and not permanent_definition.has_flying:
                    tap_target_ids.append(instance_id)
                continue
            if not permanent_definition.is_creature:
                continue
            if effect in {"damage_any_target", "blaze", "capricious_sorcerer"}:
                legal_targets.append((instance_id,))
                continue
            if effect in {"destroy_tapped_creature", "kings_assassin"} and not permanent.tapped:
                continue
            if effect == "destroy_creature_owner_gains_4_life":
                legal_targets.append((instance_id,))
                continue
            if effect in {"destroy_nonblack_creature", "wicked_pact", "assassins_blade", "serpent_assassin_etb"} and not permanent_definition.is_black:
                legal_targets.append((instance_id,))
                continue
            if effect == "put_creature_on_top_of_library":
                legal_targets.append((instance_id,))
                continue
            if effect in {"destroy_tapped_creature", "kings_assassin"}:
                legal_targets.append((instance_id,))
            if effect in {"assassins_blade", "serpent_assassin_etb", "fire_imp_etb", "fire_dragon_etb", "defiant_stand", "stern_marshal", "seasoned_marshal_attack"}:
                legal_targets.append((instance_id,))
    if effect == "wicked_pact":
        legal_targets = list(combinations(tuple(target_id[0] for target_id in legal_targets), 2))
    if effect == "forked_lightning":
        creature_ids = tuple(target_id[0] for target_id in legal_targets)
        legal_targets = [targets for count in range(1, min(3, len(creature_ids)) + 1) for targets in combinations(creature_ids, count)]
    if effect == "destroy_two_target_lands":
        legal_targets.extend(combinations(tuple(land_target_ids), 2))
    if effect == "tap_up_to_three_nonflying_creatures":
        legal_targets.append(())
        for target_count in range(1, min(3, len(tap_target_ids)) + 1):
            legal_targets.extend(combinations(tuple(tap_target_ids), target_count))
    return tuple(legal_targets)


def _forked_lightning_allocations(target_ids: tuple[str, ...]) -> tuple[tuple[tuple[str, int], ...], ...]:
    """All positive integer allocations of four across the declared targets."""
    if not target_ids:
        return ()
    def allocations(remaining: int, count: int) -> tuple[tuple[int, ...], ...]:
        if count == 1:
            return ((remaining,),)
        return tuple((amount,) + tail for amount in range(1, remaining - count + 2) for tail in allocations(remaining - amount, count - 1))
    return tuple(tuple(zip(target_ids, amounts)) for amounts in allocations(4, len(target_ids)))


def _supported_targeted_sorcery_effect(card_definition) -> str | None:
    return effect_key_for(card_definition.oracle_id) if (card_definition.is_sorcery or card_definition.is_instant) else None


def instant_timing_is_legal(state: GameState, card_definition, player_id: str) -> bool:
    attacked_player_instants = {
        "Treetop Defense", "Assassin's Blade", "Blessed Reversal",
        "Command of Unsummoning", "Deep Wood", "Defiant Stand",
        "Harsh Justice", "Scorching Winds",
    }
    if card_definition.name in attacked_player_instants:
        return state.turn.step == "declare_attackers_step" and state.combat is not None and state.combat.defending_player == player_id and state.combat.was_attacked
    return card_definition.name == "Mystic Denial" and bool(state.stack_entries)


def _enumerate_activated_abilities(state: GameState, card_repository: CardRepository) -> tuple[ActivateAbilityAction, ...]:
    """The Wave 7 tap abilities are deliberately bounded and name-scoped."""
    if state.turn.priority_player != state.turn.active_player or state.turn.step != "precombat_main_step":
        return ()
    player = state.players[state.turn.priority_player]
    result: list[ActivateAbilityAction] = []
    for source_id in player.battlefield:
        source = state.objects[source_id]
        definition = card_repository.get(source.oracle_id)
        effect = effect_key_for(source.oracle_id)
        if effect not in {"capricious_sorcerer", "kings_assassin", "stern_marshal"} or source.tapped or source.entered_battlefield_turn == state.turn.turn_number:
            continue
        targets: list[str] = []
        for candidate_player in state.players:
            if effect == "capricious_sorcerer":
                targets.append(candidate_player)
        for candidate in (obj_id for owner in state.players.values() for obj_id in owner.battlefield):
            candidate_obj = state.objects[candidate]
            candidate_definition = card_repository.get(candidate_obj.oracle_id)
            if not candidate_definition.is_creature:
                continue
            if effect == "kings_assassin" and not candidate_obj.tapped:
                continue
            targets.append(candidate)
        result.extend(ActivateAbilityAction(player.player_id, source_id, target_instance_id=target) for target in targets)
    return tuple(result)


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


LANDWALK_KEYWORD_TO_SUBTYPE = {
    "Swampwalk": "Swamp",
    "Forestwalk": "Forest",
    "Islandwalk": "Island",
    "Mountainwalk": "Mountain",
}

BLOCKS_ONLY_FLYING_CARD_NAMES = frozenset({"Cloud Dragon", "Cloud Pirates", "Cloud Spirit"})


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
    for keyword, subtype in LANDWALK_KEYWORD_TO_SUBTYPE.items():
        if has_keyword(state, card_repository, attacker_id, keyword) and _player_controls_subtype(
            state, card_repository, player_id=blocker.controller_id, subtype=subtype
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
    if blocker_definition.name in BLOCKS_ONLY_FLYING_CARD_NAMES and not has_keyword(
        state, card_repository, attacker_id, "Flying"
    ):
        return f"{blocker_definition.name} can block only creatures with flying"
    return None


def _player_controls_subtype(state: GameState, card_repository: CardRepository, *, player_id: str, subtype: str) -> bool:
    return any(
        card_repository.get(state.objects[instance_id].oracle_id).has_subtype(subtype)
        for instance_id in state.players[player_id].battlefield
    )


def _other_player_id(state: GameState, player_id: str) -> str:
    return next(candidate for candidate in state.players if candidate != player_id)


def _parse_mana_cost(mana_cost: str, *, chosen_x: int = 0) -> dict[str, int]:
    requirements = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "generic": 0}
    if not mana_cost:
        return requirements

    symbols = mana_cost.replace("{", " ").replace("}", " ").split()
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
