from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import CastNonCreatureSpellAction, ResolveChoiceAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import start_first_turn
from mtg_engine.services.legal_actions_api import (
    LegalActionApiError,
    action_for_descriptor,
    build_legal_actions_response,
    state_revision,
    valid_targets_response,
)
from mtg_engine.state.models import PendingDecision
from mtg_engine.state.zones import move_object


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
VOLCANIC_HAMMER = "98fa5a06-0553-40fd-999c-bc31c9b3f4db"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
FORKED_LIGHTNING = "66107cfd-4bdb-4266-a650-940743555ea4"
SECRET = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"


class LegalActionsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFORMATION_DIR)

    def _state(self):
        bootstrap = initialize_game(
            SetupInput(
                "api", ("alice", "bob"), "alice",
                {"alice": (MOUNTAIN, VOLCANIC_HAMMER), "bob": (PLAINS,)},
                {"alice": (MOUNTAIN, VOLCANIC_HAMMER), "bob": (PLAINS,)}, 8,
            ), self.repository,
        )
        return start_first_turn(bootstrap).state

    def test_descriptor_is_player_scoped_and_maps_only_to_enumerated_action(self) -> None:
        state = self._state()
        response = build_legal_actions_response(state, self.repository, "alice")
        self.assertEqual(response.schema_version, "v0")
        self.assertEqual(response.state_revision, state_revision(state))
        self.assertFalse(build_legal_actions_response(state, self.repository, "bob").actions)
        land = next(item for item in response.actions if item.kind == "PlayLandAction")
        action = action_for_descriptor(state, self.repository, "alice", land.action_id)
        self.assertEqual(action.player_id, "alice")
        with self.assertRaises(LegalActionApiError) as rejected:
            action_for_descriptor(state, self.repository, "bob", land.action_id)
        self.assertEqual(rejected.exception.code, "unknown_descriptor")

    def test_target_candidates_are_projections_of_cast_variants(self) -> None:
        state = self._state()
        # Give Alice enough mana for Volcanic Hammer without changing its hand.
        state = replace(state, players={
            **state.players,
            "alice": replace(state.players["alice"], mana_pool=("R", "R")),
        })
        response = build_legal_actions_response(state, self.repository, "alice")
        spell = next(item for item in response.actions if item.kind == "CastNonCreatureSpellAction")
        targets = valid_targets_response(state, self.repository, "alice", spell.action_id, "target_instance_ids")
        self.assertEqual({item.value for item in targets.candidates}, {"alice", "bob"})
        action = action_for_descriptor(
            state, self.repository, "alice", spell.action_id,
            {"target_instance_ids": ["bob"]},
        )
        self.assertIsInstance(action, CastNonCreatureSpellAction)
        self.assertEqual(action.target_instance_ids, ("bob",))

    def test_private_choice_is_only_visible_to_chooser_and_partial_candidates_are_bounded(self) -> None:
        state = self._state()
        state = replace(state, pending_decision=PendingDecision(
            decision_id="choice:api", chooser_id="alice", kind="any_number",
            source_object_id="alice:1@0", option_ids=("alice:1", "alice:2"),
            min_selections=0, max_selections=2,
        ))
        alice = build_legal_actions_response(state, self.repository, "alice")
        self.assertEqual(build_legal_actions_response(state, self.repository, "bob").actions, ())
        choice = next(item for item in alice.actions if item.kind == "ResolveChoiceAction")
        choices = valid_targets_response(
            state, self.repository, "alice", choice.action_id, "selected_instance_ids",
            {"selected_instance_ids": ["alice:1"]},
        )
        self.assertEqual([item.value for item in choices.candidates], ["alice:2"])
        action = action_for_descriptor(
            state, self.repository, "alice", choice.action_id,
            {"selected_instance_ids": ["alice:1", "alice:2"]},
        )
        self.assertEqual(action, ResolveChoiceAction("alice", "choice:api", selected_instance_ids=("alice:1", "alice:2")))

    def test_unknown_player_and_incomplete_action_have_safe_rejection_codes(self) -> None:
        state = self._state()
        with self.assertRaises(LegalActionApiError) as rejected:
            build_legal_actions_response(state, self.repository, "mallory")
        self.assertEqual(rejected.exception.code, "wrong_player")

    def test_variant_bounds_describe_multi_target_allocation_and_x_actions(self) -> None:
        bootstrap = initialize_game(
            SetupInput(
                "api-variants", ("alice", "bob"), "alice",
                {"alice": (FORKED_LIGHTNING, SECRET), "bob": (SECRET,)},
                {"alice": (FORKED_LIGHTNING, SECRET), "bob": (SECRET,)}, 9,
            ), self.repository,
        )
        state = start_first_turn(bootstrap).state
        state = move_object(
            state, instance_id="alice:2", from_zone="hand", to_zone="battlefield", player_id="alice"
        )
        state = move_object(
            state, instance_id="bob:1", from_zone="hand", to_zone="battlefield", player_id="bob"
        )
        state = replace(state, players={
            **state.players,
            "alice": replace(state.players["alice"], mana_pool=("R", "R", "R", "R")),
        })
        response = build_legal_actions_response(state, self.repository, "alice")
        spell = next(action for action in response.actions if action.kind == "CastNonCreatureSpellAction")
        slots = {slot.name: slot for slot in spell.parameters}
        self.assertEqual((slots["target_instance_ids"].minimum, slots["target_instance_ids"].maximum), (1, 2))
        self.assertEqual((slots["damage_assignments"].minimum, slots["damage_assignments"].maximum), (1, 2))

    def test_unknown_partial_slot_rejects_without_widening_candidate_query(self) -> None:
        state = self._state()
        state = replace(state, pending_decision=PendingDecision(
            decision_id="choice:partial", chooser_id="alice", kind="any_number",
            source_object_id="alice:1@0", option_ids=("alice:1",),
            min_selections=0, max_selections=1,
        ))
        response = build_legal_actions_response(state, self.repository, "alice")
        choice = next(item for item in response.actions if item.kind == "ResolveChoiceAction")
        with self.assertRaises(LegalActionApiError) as rejected:
            valid_targets_response(
                state, self.repository, "alice", choice.action_id, "selected_instance_ids",
                {"forged": "value"},
            )
        # Unknown slots remain indistinguishable from any other malformed
        # partial request and cannot be used to widen a legal candidate query.
        self.assertEqual(rejected.exception.code, "malformed_parameters")
