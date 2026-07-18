from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import _require_legal_noncreature_target, _resolve_direct_damage_sorcery
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
RAIN = "72cecab3-519e-4a23-9623-b423a5c5a251"
LAVA_FLOW = "91c0a76e-3992-437f-b85a-97b0b4adbb84"


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
