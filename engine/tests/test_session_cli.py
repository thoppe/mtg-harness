from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import PassPriorityAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.cli import main, run_cli
from mtg_engine.decks.fixtures import portal_blue_starter, portal_white_starter
from mtg_engine.flow.setup import SetupInput
from mtg_engine.replay.reducer import replay
from mtg_engine.services import GameSession


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
SECRET = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"


class GameSessionAndCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFORMATION_DIR)
        self.setup = SetupInput(
            game_id="session-cli",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={"alice": (PLAINS, SECRET), "bob": (PLAINS, SECRET)},
            opening_hands={"alice": (PLAINS,), "bob": (PLAINS,)},
            rng_seed=4,
        )

    def test_session_only_accepts_currently_enumerated_actions_and_replays(self) -> None:
        session = GameSession.from_setup(self.setup, self.repository)
        with self.assertRaisesRegex(ValueError, "enumerated"):
            session.submit(PassPriorityAction("bob"))

        action = next(action for action in session.legal_actions() if isinstance(action, PassPriorityAction))
        session.submit(action)
        replayed = replay(session.replay_input(), self.repository)
        self.assertEqual(replayed.state, session.state)
        self.assertEqual(replayed.event_log, session.result.event_log)

    def test_cli_uses_numeric_actions_saves_replay_and_does_not_print_hidden_card_name(self) -> None:
        session = GameSession.from_setup(self.setup, self.repository)
        lines: list[str] = []
        answers = iter(("3", "q"))  # pass priority is the third first-turn action
        with tempfile.TemporaryDirectory() as temp_dir:
            replay_path = Path(temp_dir) / "game.json"
            run_cli(session, input_fn=lambda _prompt: next(answers), output=lines.append, replay_path=replay_path)
            encoded = json.loads(replay_path.read_text(encoding="utf-8"))

        self.assertEqual(encoded["actions"][0]["type"], "PassPriorityAction")
        rendered = "\n".join(lines)
        self.assertNotIn("Muck Rats", rendered)
        self.assertNotIn("SECRET", rendered)
        self.assertIn("hand=1", rendered)

    def test_cli_main_starts_a_validated_deck_game_after_kept_hands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            white_path = Path(temp_dir) / "white.json"
            blue_path = Path(temp_dir) / "blue.json"
            white_path.write_text(json.dumps(portal_white_starter().to_payload()), encoding="utf-8")
            blue_path.write_text(json.dumps(portal_blue_starter().to_payload()), encoding="utf-8")
            with patch("builtins.input", side_effect=("k", "k")), patch(
                "mtg_engine.cli.run_cli"
            ) as run:
                exit_code = main(("--deck-a", str(white_path), "--deck-b", str(blue_path), "--seed", "31"))

        self.assertEqual(exit_code, 0)
        started_session = run.call_args.args[0]
        self.assertEqual(started_session.state.turn.step, "precombat_main_step")

    def test_cli_main_starts_a_labeled_midgame_rules_harness(self) -> None:
        with patch("mtg_engine.cli.run_cli") as run:
            exit_code = main(("--scenario", "combat-blockers"))

        self.assertEqual(exit_code, 0)
        started_session = run.call_args.args[0]
        self.assertEqual(started_session.state.game_id, "scenario-combat-attackers")
        self.assertEqual(started_session.state.turn.step, "declare_blockers_step")
