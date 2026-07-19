from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput
from mtg_engine.services import GameSession, SessionRejection, api_payload


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
SECRET = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"


class SessionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="session-api",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={"alice": (PLAINS, SECRET), "bob": (PLAINS, SECRET)},
            opening_hands={"alice": (PLAINS,), "bob": (PLAINS,)},
            rng_seed=99,
        )
        self.session = GameSession.from_setup(setup, self.repository)

    def test_descriptors_are_player_scoped_and_json_safe(self) -> None:
        alice = self.session.legal_actions_api("alice")
        self.assertFalse(isinstance(alice, SessionRejection))
        assert not isinstance(alice, SessionRejection)
        self.assertTrue(alice.actions)
        self.assertTrue(all(action.player_id == "alice" for action in alice.actions))
        self.assertEqual(api_payload(alice)["state_revision"], self.session.revision)  # type: ignore[index]

        bob = self.session.legal_actions_api("bob")
        self.assertFalse(isinstance(bob, SessionRejection))
        assert not isinstance(bob, SessionRejection)
        self.assertEqual(bob.actions, ())
        self.assertEqual(self.session.legal_actions_api("mallory").code, "wrong_player")  # type: ignore[union-attr]

    def test_submission_rejections_do_not_mutate_and_stale_revisions_are_rejected(self) -> None:
        response = self.session.legal_actions_api("alice")
        assert not isinstance(response, SessionRejection)
        pass_descriptor = next(item for item in response.actions if item.kind == "PassPriorityAction")
        before_state = self.session.state
        before_log = self.session.result.event_log

        malformed = self.session.submit_descriptor(
            "alice", pass_descriptor.action_id, {"not_a_parameter": True}, response.state_revision
        )
        self.assertFalse(malformed.accepted)
        self.assertEqual(malformed.rejection.code if malformed.rejection else None, "malformed_parameters")
        self.assertEqual(self.session.state, before_state)
        self.assertEqual(self.session.result.event_log, before_log)

        accepted = self.session.submit_descriptor("alice", pass_descriptor.action_id, {}, response.state_revision)
        self.assertTrue(accepted.accepted)
        self.assertNotEqual(accepted.state_revision, response.state_revision)
        stale = self.session.submit_descriptor("alice", pass_descriptor.action_id, {}, response.state_revision)
        self.assertFalse(stale.accepted)
        self.assertEqual(stale.rejection.code if stale.rejection else None, "stale_revision")

    def test_wrong_player_unknown_descriptor_and_unknown_slot_are_structured_rejections(self) -> None:
        response = self.session.legal_actions_api("alice")
        assert not isinstance(response, SessionRejection)
        descriptor = response.actions[0]
        wrong_player = self.session.submit_descriptor("mallory", descriptor.action_id, {}, response.state_revision)
        self.assertEqual(wrong_player.rejection.code if wrong_player.rejection else None, "wrong_player")
        unknown = self.session.submit_descriptor("alice", "not-an-action", {}, response.state_revision)
        self.assertEqual(unknown.rejection.code if unknown.rejection else None, "unknown_descriptor")
        target_result = self.session.valid_targets_api("alice", descriptor.action_id, "not-a-slot")
        self.assertIsInstance(target_result, SessionRejection)
        self.assertEqual(target_result.code, "unknown_slot")  # type: ignore[union-attr]
