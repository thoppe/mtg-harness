from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import ResolveChoiceAction
from mtg_engine.cards.implementations import effect_key_for
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.priority import _legal_noncreature_spell_targets
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import TurnResult, _resolve_noncreature_spell, resolve_pending_choice
from mtg_engine.state.models import StackEntry
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
WAVE_FIVE_IDS = {
    "20370c3b-231f-4d9d-8b6e-f1eb25fa4b5d", "b8cff5f1-6871-49d2-89a7-24870308aadb",
    "8c1fe337-375a-4add-93b6-0ac39ed72b4f", "95a2802a-2621-40c3-84f8-51e8aad7b6f0",
    "c586312d-d04a-4bfb-bbb2-b41186ca178e", "ffe6371c-d137-4062-8c6e-6e9794ab25bc",
    "c57ee68e-6832-4d4c-b710-fc03a2c10a9c", "9225016d-adfd-43c6-99cd-d41a7e0d35d6",
    "f9be5566-c3df-44cc-9de4-29510c8c245f", "4135131d-4653-4767-ad1d-68c9bf393c3a",
    "f525cf10-e24c-4c46-9a13-6f8579d09d50", "b3b4c21d-f8d7-455f-be46-d5eb909d54df",
    "1bd70be6-752c-4ecb-a3e8-2bacec4b94fc", "6237896e-f033-41b2-9943-670f1becb582",
    "e199e183-e857-4dc7-87f4-36b32c4dac96", "dcf105c1-d37b-4e92-a420-9872a2187764",
    "d9353eb6-c7e7-4d85-a0c2-32b1d091881a", "78826359-fe63-44ad-adc4-a17ffcd710e4",
    "9b8c44a0-82ef-4beb-a762-c2a2a21380f3",
}
ANCESTRAL = "95a2802a-2621-40c3-84f8-51e8aad7b6f0"
RAIN = "72cecab3-519e-4a23-9623-b423a5c5a251"
SORCEROUS_SIGHT = "20370c3b-231f-4d9d-8b6e-f1eb25fa4b5d"


class WaveFiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = CardRepository.from_information_directory(INFO)

    def test_every_promoted_wave_five_card_has_a_name_scoped_effect(self) -> None:
        self.assertEqual(len(WAVE_FIVE_IDS), 19)
        self.assertTrue(all(effect_key_for(oracle_id) is not None for oracle_id in WAVE_FIVE_IDS))
        self.assertTrue(all(self.repo.has(oracle_id) for oracle_id in WAVE_FIVE_IDS))

    def test_ancestral_memories_keeps_selected_cards_and_buries_the_rest(self) -> None:
        state = initialize_game(
            SetupInput("wave5", ("alice", "bob"), "alice", {"alice": (ANCESTRAL, RAIN, RAIN, RAIN), "bob": (RAIN,)}, {"alice": (ANCESTRAL,), "bob": (RAIN,)}, 9),
            self.repo,
        ).state
        state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")
        entry = StackEntry(card_instance_id="alice:1", controller_id="alice")
        pending = _resolve_noncreature_spell(TurnResult(state, ()), entry, self.repo)
        decision = pending.state.pending_decision
        self.assertEqual(decision.kind, "choose_two_from_library_prefix")
        resolved = resolve_pending_choice(pending, ResolveChoiceAction("alice", decision.decision_id, selected_instance_ids=("alice:2", "alice:3")), self.repo)
        self.assertEqual(resolved.state.players["alice"].hand, ("alice:2", "alice:3"))
        self.assertEqual(resolved.state.players["alice"].graveyard[-2:], ("alice:1", "alice:4"))

    def test_hidden_choice_rejects_cards_outside_its_snapshot(self) -> None:
        state = initialize_game(
            SetupInput("wave5-illegal", ("alice", "bob"), "alice", {"alice": (ANCESTRAL, RAIN, RAIN), "bob": (RAIN,)}, {"alice": (ANCESTRAL,), "bob": (RAIN,)}, 4), self.repo
        ).state
        state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="stack", player_id="alice")
        pending = _resolve_noncreature_spell(TurnResult(state, ()), StackEntry(card_instance_id="alice:1", controller_id="alice"), self.repo)
        decision = pending.state.pending_decision
        with self.assertRaisesRegex(ValueError, "legal option"):
            resolve_pending_choice(pending, ResolveChoiceAction("alice", decision.decision_id, selected_instance_ids=("alice:2", "bob:1")), self.repo)

    def test_targeted_and_targetless_wave_five_spells_are_enumerable(self) -> None:
        state = initialize_game(
            SetupInput("wave5-targets", ("alice", "bob"), "alice", {"alice": (SORCEROUS_SIGHT, ANCESTRAL), "bob": (RAIN,)}, {"alice": (SORCEROUS_SIGHT, ANCESTRAL), "bob": (RAIN,)}, 4), self.repo
        ).state
        self.assertEqual(
            _legal_noncreature_spell_targets(state, self.repo, "alice:1"),
            (("bob",),),
        )
        self.assertEqual(
            _legal_noncreature_spell_targets(state, self.repo, "alice:2"),
            ((),),
        )
