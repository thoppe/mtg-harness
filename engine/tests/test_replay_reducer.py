from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    CastCreatureSpellAction,
    PassPriorityAction,
    PlayLandAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import activate_mana_ability, cast_creature_spell, pass_priority, play_land, start_first_turn
from mtg_engine.replay.reducer import ReplayInput, replay


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"


class ReplayReducerTests(unittest.TestCase):
    def test_replays_land_mana_creature_cast_and_stack_passes(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-reducer-creature",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={"alice": (SWAMP, MUCK_RATS), "bob": (PLAINS,)},
            opening_hands={"alice": (SWAMP, MUCK_RATS), "bob": (PLAINS,)},
            rng_seed=71,
        )
        actions = (
            PlayLandAction(player_id="alice", card_instance_id="alice:1"),
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
            CastCreatureSpellAction(player_id="alice", card_instance_id="alice:2"),
            PassPriorityAction(player_id="alice"),
            PassPriorityAction(player_id="bob"),
        )

        direct = start_first_turn(initialize_game(setup, repository))
        direct = play_land(direct, actions[0], repository)
        direct = activate_mana_ability(direct, actions[1], repository)
        direct = cast_creature_spell(direct, actions[2], repository)
        direct = pass_priority(direct, actions[3], repository)
        direct = pass_priority(direct, actions[4], repository)
        reduced = replay(ReplayInput(setup=setup, actions=actions), repository)

        self.assertEqual(reduced.state, direct.state)
        self.assertEqual(reduced.event_log, direct.event_log)

    def test_rejects_an_illegal_action_log(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-reducer-invalid",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={"alice": (PLAINS,), "bob": (PLAINS,)},
            opening_hands={"alice": (PLAINS,), "bob": (PLAINS,)},
            rng_seed=72,
        )

        with self.assertRaisesRegex(ValueError, "mana source must be on the battlefield"):
            replay(
                ReplayInput(
                    setup=setup,
                    actions=(ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),),
                ),
                repository,
            )
