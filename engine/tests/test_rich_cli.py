from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.midgame_scenarios import create_midgame_session
from mtg_engine.flow.setup import SetupInput
from mtg_engine.output.cli import RichCliRenderer
from mtg_engine.services import GameSession, SessionRejection


INFO = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"


class RichCliRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFO)

    def _renderer(self) -> tuple[RichCliRenderer, io.StringIO]:
        output = io.StringIO()
        return RichCliRenderer(Console(file=output, force_terminal=False, no_color=True, width=120)), output

    def test_player_frame_shows_only_the_viewers_hand_identity(self) -> None:
        session = GameSession.from_setup(
            SetupInput(
                game_id="rich-private-hand",
                players=("alice", "bob"),
                starting_player="alice",
                libraries={"alice": (PLAINS,), "bob": (MUCK_RATS,)},
                opening_hands={"alice": (PLAINS,), "bob": (MUCK_RATS,)},
                rng_seed=6,
            ),
            self.repository,
        )
        renderer, output = self._renderer()

        renderer.game_state(session, "alice")

        rendered = output.getvalue()
        self.assertIn("alice's hand", rendered)
        self.assertIn("Plains", rendered)
        self.assertNotIn("Muck Rats", rendered)
        self.assertIn("Turn 1", rendered)

    def test_action_pane_is_complete_for_the_current_descriptor_response(self) -> None:
        session = create_midgame_session(self.repository, "combat-attackers")
        response = session.legal_actions_api("alice")
        self.assertNotIsInstance(response, SessionRejection)
        assert not isinstance(response, SessionRejection)
        renderer, output = self._renderer()

        renderer.actions(response)

        rendered = output.getvalue()
        self.assertIn("Your legal actions", rendered)
        for index, action in enumerate(response.actions, start=1):
            self.assertIn(str(index), rendered)
            self.assertIn(action.kind, rendered)

    def test_frame_includes_public_stack_and_combat_context(self) -> None:
        renderer, output = self._renderer()

        renderer.game_state(create_midgame_session(self.repository, "combat-blockers"), "bob")
        renderer.game_state(create_midgame_session(self.repository, "mystic-denial-response"), "bob")

        rendered = output.getvalue()
        self.assertIn("Combat", rendered)
        self.assertIn("Charging Rhino", rendered)
        self.assertIn("Stack", rendered)
        self.assertIn("Volcanic Hammer", rendered)

    def test_candidate_pane_renders_only_api_labels(self) -> None:
        session = create_midgame_session(self.repository, "private-choice")
        response = session.legal_actions_api("alice")
        self.assertNotIsInstance(response, SessionRejection)
        assert not isinstance(response, SessionRejection)
        choice = next(action for action in response.actions if action.kind == "ResolveChoiceAction")
        candidates = session.valid_targets_api("alice", choice.action_id, "selected_instance_ids")
        self.assertNotIsInstance(candidates, SessionRejection)
        assert not isinstance(candidates, SessionRejection)
        renderer, output = self._renderer()

        renderer.candidates(candidates.candidates)

        rendered = output.getvalue()
        self.assertIn("Valid choices", rendered)
        for candidate in candidates.candidates:
            self.assertIn(candidate.label, rendered)
            self.assertNotIn(candidate.candidate_id, rendered)
            self.assertNotIn(str(candidate.value), rendered)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
