from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import CastNonCreatureSpellAction
from mtg_engine.cards.implementations import effect_key_for
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import TurnResult, _resolve_noncreature_spell
from mtg_engine.state.models import StackEntry
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
WAVE_SIX_IDS = {
    "0596920f-9946-42f4-a03b-24aab67f9f1b", "9a40614b-50a3-422c-849e-53c8b7d3d204",
    "66107cfd-4bdb-4266-a650-940743555ea4", "39e21a5a-b278-478a-854c-17695c0f6246",
    "4d98aea2-b4ff-4903-ba28-a53fbfaad6b1", "052838cb-dcf0-46f5-82b1-c3ed863b42b7",
    "0e7b9caf-8285-4386-98bc-9a809827f447", "7962db58-dbd9-4b94-8a21-a1625da4c384",
    "24cf7fad-233b-49fd-b2a1-a29e3e30041c", "360039a5-1cbd-4ee3-8f94-21b5348e106a",
}
BLAZE = "0596920f-9946-42f4-a03b-24aab67f9f1b"
EARTHQUAKE = "9a40614b-50a3-422c-849e-53c8b7d3d204"
FORKED_LIGHTNING = "66107cfd-4bdb-4266-a650-940743555ea4"
LAST_CHANCE = "360039a5-1cbd-4ee3-8f94-21b5348e106a"
CREATURE = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"


class WaveSixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = CardRepository.from_information_directory(INFO)

    def _state(self, spell: str, *, extra: tuple[str, ...] = ()):  # all cards initially in hand
        cards = (spell,) + extra
        state = initialize_game(SetupInput("wave6", ("alice", "bob"), "alice", {"alice": cards, "bob": ()}, {"alice": cards, "bob": ()}, 11), self.repo).state
        return move_object(state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")

    def test_every_wave_six_card_has_a_name_scoped_effect(self) -> None:
        self.assertEqual(len(WAVE_SIX_IDS), 10)
        self.assertTrue(all(effect_key_for(oracle_id) is not None and self.repo.has(oracle_id) for oracle_id in WAVE_SIX_IDS))

    def test_blaze_uses_declared_x_and_earthquake_hits_each_player(self) -> None:
        state = self._state(BLAZE)
        result = _resolve_noncreature_spell(TurnResult(state, ()), StackEntry(card_instance_id="alice:1", controller_id="alice", target_ids=("bob",), chosen_x=3), self.repo)
        self.assertEqual(result.state.players["bob"].life_total, 17)
        state = self._state(EARTHQUAKE)
        result = _resolve_noncreature_spell(TurnResult(state, ()), StackEntry(card_instance_id="alice:1", controller_id="alice", chosen_x=2), self.repo)
        self.assertEqual((result.state.players["alice"].life_total, result.state.players["bob"].life_total), (18, 18))

    def test_forked_lightning_requires_positive_complete_allocation(self) -> None:
        state = self._state(FORKED_LIGHTNING, extra=(CREATURE,))
        state = move_object(state, instance_id="alice:2", from_zone="hand", to_zone="battlefield", player_id="alice")
        entry = StackEntry(card_instance_id="alice:1", controller_id="alice", target_ids=("alice:2",), damage_assignments=(("alice:2", 4),))
        result = _resolve_noncreature_spell(TurnResult(state, ()), entry, self.repo)
        self.assertEqual(result.state.objects["alice:2"].zone, "graveyard")

    def test_last_chance_schedules_an_extra_turn_with_delayed_loss(self) -> None:
        state = self._state(LAST_CHANCE)
        result = _resolve_noncreature_spell(TurnResult(state, ()), StackEntry(card_instance_id="alice:1", controller_id="alice"), self.repo)
        self.assertEqual(result.state.extra_turns[0].player_id, "alice")
        self.assertTrue(result.state.extra_turns[0].lose_at_end_step)
