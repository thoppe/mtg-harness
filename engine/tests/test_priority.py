from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import ActivateManaAbilityAction, AdvanceStepAction, PassPriorityAction, PlayLandAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.priority import enumerate_legal_actions
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import pass_priority, play_land, start_first_turn


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
FOOT_SOLDIERS = "a768ba13-4d1c-4dce-a4a6-86a39c069c3f"


class PriorityTests(unittest.TestCase):
    def test_precombat_main_enumerates_land_then_step_controls(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertEqual(
            actions,
            (
                PlayLandAction(player_id="alice", card_instance_id="alice:1"),
                AdvanceStepAction(player_id="alice", to_step="begin_combat_step"),
                PassPriorityAction(player_id="alice"),
            ),
        )

    def test_played_land_exposes_mana_ability_and_step_controls(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)
        session = play_land(session, PlayLandAction(player_id="alice", card_instance_id="alice:1"), repository)

        actions = enumerate_legal_actions(session.state, repository)

        self.assertEqual(
            actions,
            (
                ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
                AdvanceStepAction(player_id="alice", to_step="begin_combat_step"),
                PassPriorityAction(player_id="alice"),
            ),
        )

    def test_pass_priority_auto_advances_when_opponent_has_no_supported_actions(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_main_phase_session(repository)

        result = pass_priority(session, PassPriorityAction(player_id="alice"), repository)

        self.assertEqual(result.state.turn.step, "declare_attackers_step")
        self.assertEqual(result.state.turn.priority_player, "alice")
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            ["priority_passed", "priority_passed", "step_changed", "step_changed"],
        )


def _build_main_phase_session(repository: CardRepository):
    setup = SetupInput(
        game_id="priority-001",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, FOOT_SOLDIERS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS,),
            "bob": (PLAINS,),
        },
        rng_seed=13,
    )
    return start_first_turn(initialize_game(setup, repository))


if __name__ == "__main__":
    unittest.main()
