from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.priority import blocker_attack_rejection_reason
from mtg_engine.flow.turns import TurnResult, _add_temporary_effect, _battlefield_land_subtype_count, _cleanup_end_of_turn_state, _controlled_land_subtype_count, _damage_creatures_once, _require_legal_noncreature_target, _resolve_direct_damage_sorcery, _resolve_noncreature_spell, play_land, resolve_pending_choice
from mtg_engine.rules.characteristics import effective_keywords, effective_power, effective_toughness
from mtg_engine.state.models import StackEntry, TurnState
from mtg_engine.state.zones import move_object
from mtg_engine.actions.models import CastNonCreatureSpellAction, PlayLandAction, ResolveChoiceAction


INFO = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
RAIN = "72cecab3-519e-4a23-9623-b423a5c5a251"
LAVA_FLOW = "91c0a76e-3992-437f-b85a-97b0b4adbb84"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
RENEWING_DAWN = "54ea46ea-7c83-44a9-85b0-eff9745c6ffa"
THEFT_OF_DREAMS = "008011e2-7b82-4962-af6e-be627112f37f"
VAMPIRIC_FEAST = "1980ca2e-a415-4de1-ac30-7055507e82a2"
BREATH_OF_LIFE = "30d9e200-b944-43ff-89b8-a550a788ae03"
DEJA_VU = "7408b9c5-7266-4627-be4e-b691cf5c622c"
PERSONAL_TUTOR = "90f54959-2c9b-4b8a-84c9-d6893eb43553"
SYLVAN_TUTOR = "935e0cac-51ee-4cb7-a209-f085e0f099ed"
SUMMER_BLOOM = "e5df4597-1647-4ac2-bdb3-a517598d1431"


class PortalExpansionWaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = CardRepository.from_information_directory(INFO)
        self.state = initialize_game(
            SetupInput("wave", ("alice", "bob"), "alice", {"alice": (RAIN,), "bob": (PLAINS,)}, {"alice": (RAIN,), "bob": (PLAINS,)}, 1), self.repo
        ).state

    def test_lava_flow_rejects_a_player_but_accepts_a_battlefield_land(self) -> None:
        with self.assertRaisesRegex(ValueError, "target must exist"):
            _require_legal_noncreature_target(self.state, self.repo, ("bob",), effect="destroy_target_creature_or_land")
        state = move_object(self.state, instance_id="bob:1", from_zone="hand", to_zone="battlefield", player_id="bob")
        _require_legal_noncreature_target(state, self.repo, ("bob:1",), effect="destroy_target_creature_or_land")

    def test_one_damage_to_a_player_runs_terminal_sbas(self) -> None:
        state = replace(self.state, players={**self.state.players, "bob": replace(self.state.players["bob"], life_total=1)})
        result, events = _resolve_direct_damage_sorcery(state, self.repo, "bob", effect="damage_any_target_1", active_player="alice")
        self.assertEqual(result.outcome.winner_id, "alice")
        self.assertIn("game_ended", [event["event_type"] for event in events])

    def test_graveyard_return_requires_own_graveyard_and_creature_when_required(self) -> None:
        graveyard_state = move_object(self.state, instance_id="alice:1", from_zone="hand", to_zone="graveyard", player_id="alice")
        with self.assertRaisesRegex(ValueError, "creature card"):
            _require_legal_noncreature_target(graveyard_state, self.repo, ("alice:1",), effect="return_target_creature_card_from_your_graveyard")
        _require_legal_noncreature_target(graveyard_state, self.repo, ("alice:1",), effect="return_target_card_from_your_graveyard")

    def test_mass_damage_marks_all_targets_before_one_sba_checkpoint(self) -> None:
        state = initialize_game(SetupInput("mass", ("alice", "bob"), "alice", {"alice": (MUCK_RATS,), "bob": (MUCK_RATS,)}, {"alice": (MUCK_RATS,), "bob": (MUCK_RATS,)}, 2), self.repo).state
        state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
        state = move_object(state, instance_id="bob:1", from_zone="hand", to_zone="battlefield", player_id="bob")
        result, events = _damage_creatures_once(state, self.repo, ("alice:1", "bob:1"), 2, "alice")
        self.assertEqual(result.players["alice"].graveyard, ("alice:1",))
        self.assertEqual(result.players["bob"].graveyard, ("bob:1",))
        self.assertEqual([event["event_type"] for event in events].count("state_based_actions_checked"), 1)

    def test_temporary_power_bonus_expires_at_cleanup_and_zone_change(self) -> None:
        state = move_object(self.state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
        boosted = replace(state, objects={**state.objects, "alice:1": replace(state.objects["alice:1"], temporary_power_bonus=4)})
        self.assertEqual(_cleanup_end_of_turn_state(boosted).objects["alice:1"].temporary_power_bonus, 0)
        moved = move_object(boosted, instance_id="alice:1", from_zone="battlefield", to_zone="graveyard", player_id="alice")
        self.assertEqual(moved.objects["alice:1"].temporary_power_bonus, 0)

    def test_temporary_toughness_bonus_also_expires_and_resets(self) -> None:
        state = move_object(self.state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
        boosted = replace(state, objects={**state.objects, "alice:1": replace(state.objects["alice:1"], temporary_toughness_bonus=4)})
        self.assertEqual(_cleanup_end_of_turn_state(boosted).objects["alice:1"].temporary_toughness_bonus, 0)
        self.assertEqual(move_object(boosted, instance_id="alice:1", from_zone="battlefield", to_zone="graveyard", player_id="alice").objects["alice:1"].temporary_toughness_bonus, 0)

    def test_object_bound_effect_changes_characteristics_and_dies_on_zone_change(self) -> None:
        state = move_object(self.state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
        affected = _add_temporary_effect(state, source_object_id="source@0", target_ids=("alice:1",), power_delta=3, toughness_delta=3, keywords=("Flying",))
        self.assertEqual(effective_power(affected, self.repo, "alice:1"), 3)
        self.assertEqual(effective_toughness(affected, self.repo, "alice:1"), 3)
        self.assertIn("Flying", effective_keywords(affected, self.repo, "alice:1"))
        moved = move_object(affected, instance_id="alice:1", from_zone="battlefield", to_zone="graveyard", player_id="alice")
        self.assertEqual(moved.temporary_effects, ())

    def test_wave_two_sources_load_from_active_slice(self) -> None:
        self.assertTrue(self.repo.get("f215d0f9-a53e-431a-a70d-9dc4e3caa41e").is_instant)
        self.assertEqual(self.repo.get("23745133-e5e2-4ce3-b94a-73d0d3d8a013").name, "Phantom Warrior")

    def test_phantom_warrior_uses_shared_blocker_legality(self) -> None:
        state = move_object(self.state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
        state = move_object(state, instance_id="bob:1", from_zone="hand", to_zone="battlefield", player_id="bob")
        state = replace(
            state,
            objects={
                **state.objects,
                "alice:1": replace(state.objects["alice:1"], oracle_id="23745133-e5e2-4ce3-b94a-73d0d3d8a013"),
                "bob:1": replace(state.objects["bob:1"], oracle_id=MUCK_RATS),
            },
            turn=TurnState(1, "alice", "bob", "declare_blockers_step"),
        )
        self.assertEqual(
            blocker_attack_rejection_reason(state=state, card_repository=self.repo, blocker_id="bob:1", attacker_id="alice:1"),
            "blocker cannot block the selected attacker",
        )

    def test_temporary_creature_effects_require_battlefield_creatures(self) -> None:
        with self.assertRaisesRegex(ValueError, "target must be a creature"):
            _require_legal_noncreature_target(self.state, self.repo, ("alice:1",), effect="target_creature_gets_4_4_until_end_of_turn")

    def test_chosen_x_is_nonnegative_and_part_of_the_action(self) -> None:
        self.assertEqual(CastNonCreatureSpellAction(player_id="alice", card_instance_id="alice:1", chosen_x=3).chosen_x, 3)
        with self.assertRaisesRegex(ValueError, "must not be negative"):
            CastNonCreatureSpellAction(player_id="alice", card_instance_id="alice:1", chosen_x=-1)

    def test_spitting_earth_counts_only_its_controller_mountains_and_requires_a_creature(self) -> None:
        state = initialize_game(
            SetupInput("spitting", ("alice", "bob"), "alice", {"alice": (MOUNTAIN, MOUNTAIN), "bob": (MOUNTAIN, MUCK_RATS)}, {"alice": (MOUNTAIN, MOUNTAIN), "bob": (MOUNTAIN, MUCK_RATS)}, 3),
            self.repo,
        ).state
        for instance_id in ("alice:1", "alice:2", "bob:1", "bob:2"):
            owner_id = instance_id.split(":")[0]
            state = move_object(state, instance_id=instance_id, from_zone="hand", to_zone="battlefield", player_id=owner_id)
        self.assertEqual(_controlled_land_subtype_count(state, self.repo, "alice", "Mountain"), 2)
        _require_legal_noncreature_target(state, self.repo, ("bob:2",), effect="damage_target_creature_per_mountain")
        with self.assertRaisesRegex(ValueError, "target must be a creature"):
            _require_legal_noncreature_target(state, self.repo, ("bob:1",), effect="damage_target_creature_per_mountain")
        result, events = _resolve_direct_damage_sorcery(state, self.repo, "bob:2", effect="damage_target_creature_variable", active_player="alice", damage_override=2)
        self.assertEqual(result.objects["bob:2"].zone, "graveyard")
        self.assertIn("permanent_destroyed", [event["event_type"] for event in events])

    def test_fruition_counts_forests_on_both_sides(self) -> None:
        state = initialize_game(
            SetupInput("fruition", ("alice", "bob"), "alice", {"alice": (FOREST,), "bob": (FOREST, FOREST)}, {"alice": (FOREST,), "bob": (FOREST, FOREST)}, 4),
            self.repo,
        ).state
        for instance_id in ("alice:1", "bob:1", "bob:2"):
            owner_id = instance_id.split(":")[0]
            state = move_object(state, instance_id=instance_id, from_zone="hand", to_zone="battlefield", player_id=owner_id)
        self.assertEqual(_battlefield_land_subtype_count(state, self.repo, "Forest"), 3)
        _require_legal_noncreature_target(state, self.repo, (), effect="gain_life_per_forest")

    def test_renewing_dawn_counts_only_target_opponents_mountains(self) -> None:
        state = initialize_game(
            SetupInput("dawn", ("alice", "bob"), "alice", {"alice": (RENEWING_DAWN, MOUNTAIN), "bob": (MOUNTAIN, MOUNTAIN)}, {"alice": (RENEWING_DAWN, MOUNTAIN), "bob": (MOUNTAIN, MOUNTAIN)}, 5), self.repo
        ).state
        for instance_id in ("alice:2", "bob:1", "bob:2"):
            state = move_object(state, instance_id=instance_id, from_zone="hand", to_zone="battlefield", player_id=instance_id.split(":")[0])
        state = replace(state, turn=replace(state.turn, step="precombat_main_step"))
        state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")
        result = _resolve_noncreature_spell(TurnResult(state, ()), StackEntry("alice:1", "alice", ("bob",)), self.repo)
        self.assertEqual(result.state.players["alice"].life_total, 24)
        self.assertEqual(result.state.objects["alice:1"].zone, "graveyard")

    def test_theft_of_dreams_draws_once_per_tapped_creature_and_feast_hits_any_target(self) -> None:
        state = initialize_game(
            SetupInput("theft", ("alice", "bob"), "alice", {"alice": (THEFT_OF_DREAMS, PLAINS), "bob": (MUCK_RATS, MUCK_RATS, PLAINS)}, {"alice": (THEFT_OF_DREAMS,), "bob": (MUCK_RATS, MUCK_RATS, PLAINS)}, 6), self.repo
        ).state
        state = move_object(state, instance_id="bob:1", from_zone="library", to_zone="battlefield", player_id="bob")
        state = move_object(state, instance_id="bob:2", from_zone="library", to_zone="battlefield", player_id="bob")
        state = replace(state, objects={**state.objects, "bob:1": replace(state.objects["bob:1"], tapped=True), "bob:2": replace(state.objects["bob:2"], tapped=True)})
        state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")
        result = _resolve_noncreature_spell(TurnResult(state, ()), StackEntry("alice:1", "alice", ("bob",)), self.repo)
        self.assertEqual(len(result.state.players["alice"].hand), 1)
        feast_state = initialize_game(SetupInput("feast", ("alice", "bob"), "alice", {"alice": (VAMPIRIC_FEAST,), "bob": (PLAINS,)}, {"alice": (VAMPIRIC_FEAST,), "bob": (PLAINS,)}, 7), self.repo).state
        feast_state = move_object(feast_state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")
        feast_result = _resolve_noncreature_spell(TurnResult(feast_state, ()), StackEntry("alice:1", "alice", ("bob",)), self.repo)
        self.assertEqual(feast_result.state.players["alice"].life_total, 24)
        self.assertEqual(feast_result.state.players["bob"].life_total, 16)

    def test_breath_of_life_reanimates_only_a_creature_and_deja_vu_only_returns_a_sorcery(self) -> None:
        state = initialize_game(
            SetupInput("graveyard-types", ("alice", "bob"), "alice", {"alice": (BREATH_OF_LIFE, MUCK_RATS, DEJA_VU, PLAINS), "bob": (PLAINS,)}, {"alice": (BREATH_OF_LIFE, MUCK_RATS, DEJA_VU), "bob": (PLAINS,)}, 8), self.repo
        ).state
        state = move_object(state, instance_id="alice:2", from_zone="hand", to_zone="graveyard", player_id="alice")
        state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")
        result = _resolve_noncreature_spell(TurnResult(state, ()), StackEntry("alice:1", "alice", ("alice:2",)), self.repo)
        self.assertEqual(result.state.objects["alice:2"].zone, "battlefield")
        self.assertNotEqual(result.state.objects["alice:2"].object_id, state.objects["alice:2"].object_id)
        deja_state = move_object(result.state, instance_id="alice:3", from_zone="hand", to_zone="stack", player_id="alice")
        deja_result = _resolve_noncreature_spell(TurnResult(deja_state, ()), StackEntry("alice:3", "alice", ("alice:1",)), self.repo)
        self.assertEqual(deja_result.state.objects["alice:1"].zone, "hand")
        creature_graveyard_state = move_object(result.state, instance_id="alice:2", from_zone="battlefield", to_zone="graveyard", player_id="alice")
        with self.assertRaisesRegex(ValueError, "sorcery card"):
            _require_legal_noncreature_target(creature_graveyard_state, self.repo, ("alice:2",), effect="return_target_sorcery_card_from_your_graveyard")

    def test_tutors_require_a_matching_hidden_choice_then_reveal_shuffle_and_topdeck(self) -> None:
        state = initialize_game(SetupInput("tutors", ("alice", "bob"), "alice", {"alice": (PERSONAL_TUTOR, SYLVAN_TUTOR, RAIN, MUCK_RATS), "bob": (PLAINS,)}, {"alice": (PERSONAL_TUTOR, SYLVAN_TUTOR), "bob": (PLAINS,)}, 9), self.repo).state
        state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")
        pending = _resolve_noncreature_spell(TurnResult(state, ()), StackEntry("alice:1", "alice"), self.repo)
        decision = pending.state.pending_decision
        self.assertEqual(decision.option_ids, ("alice:3",))
        with self.assertRaisesRegex(ValueError, "legal option"):
            resolve_pending_choice(pending, ResolveChoiceAction("alice", decision.decision_id, "alice:4"), self.repo)
        personal = resolve_pending_choice(pending, ResolveChoiceAction("alice", decision.decision_id, "alice:3"), self.repo)
        self.assertEqual(personal.state.players["alice"].library[0], "alice:3")
        self.assertEqual(personal.state.rng_cursor, 1)
        self.assertIsNone(personal.state.pending_decision)
        sylvan_state = move_object(personal.state, instance_id="alice:2", from_zone="hand", to_zone="stack", player_id="alice")
        sylvan_pending = _resolve_noncreature_spell(TurnResult(sylvan_state, personal.event_log), StackEntry("alice:2", "alice"), self.repo)
        sylvan_decision = sylvan_pending.state.pending_decision
        self.assertEqual(sylvan_decision.option_ids, ("alice:4",))
        sylvan = resolve_pending_choice(sylvan_pending, ResolveChoiceAction("alice", sylvan_decision.decision_id, "alice:4"), self.repo)
        self.assertEqual(sylvan.state.players["alice"].library[0], "alice:4")

    def test_summer_bloom_allows_exactly_three_additional_land_plays_then_resets(self) -> None:
        state = initialize_game(SetupInput("bloom", ("alice", "bob"), "alice", {"alice": (SUMMER_BLOOM, PLAINS, PLAINS, PLAINS, PLAINS), "bob": (PLAINS,)}, {"alice": (SUMMER_BLOOM, PLAINS, PLAINS, PLAINS, PLAINS), "bob": (PLAINS,)}, 10), self.repo).state
        state = replace(state, turn=replace(state.turn, step="precombat_main_step"))
        state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")
        resolved = _resolve_noncreature_spell(TurnResult(state, ()), StackEntry("alice:1", "alice"), self.repo)
        self.assertEqual(resolved.state.players["alice"].land_play_limit_this_turn, 4)
        session = resolved
        for instance_id in ("alice:2", "alice:3", "alice:4", "alice:5"):
            session = play_land(session, PlayLandAction("alice", instance_id), self.repo)
        self.assertEqual(session.state.players["alice"].lands_played_this_turn, 4)
        with self.assertRaisesRegex(ValueError, "already played"):
            play_land(session, PlayLandAction("alice", "alice:5"), self.repo)
        self.assertEqual(_cleanup_end_of_turn_state(session.state).players["alice"].land_play_limit_this_turn, 1)
