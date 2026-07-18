from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import _cleanup_end_of_turn_state, _damage_creatures_once, _require_legal_noncreature_target, _resolve_direct_damage_sorcery
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
RAIN = "72cecab3-519e-4a23-9623-b423a5c5a251"
LAVA_FLOW = "91c0a76e-3992-437f-b85a-97b0b4adbb84"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"


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
