from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import DeclareAttackersAction, DeclareBlockersAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.priority import blocker_attack_rejection_reason, enumerate_legal_actions
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import TurnResult, declare_attackers, declare_blockers
from mtg_engine.rules.combat import with_combat_state
from mtg_engine.state.models import TurnState
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
ARMORED_PEGASUS = "f097a059-5505-4c3c-b879-7853ab6972ed"
BULL_HIPPO = "4d62a448-b6a5-43b1-a281-9e9361a5524a"
ARCHANGEL = "9971697b-2acc-4bc2-a44e-074d03a51df7"
ARDENT_MILITIA = "23625877-b6db-480c-8885-a62b7d0457df"
CLOUD_DRAGON = "3c46f309-69ae-43b1-adf6-bdb26599c1f4"
CLOUD_PIRATES = "d334aa85-3470-4f5d-9cbc-b88bf991a5af"
CLOUD_SPIRIT = "9e1a6481-f460-4551-96e8-30b289f2cb92"
WAVE_THREE_CARD_NAMES = {
    "9971697b-2acc-4bc2-a44e-074d03a51df7": "Archangel",
    "23625877-b6db-480c-8885-a62b7d0457df": "Ardent Militia",
    "5edfe083-391b-41ae-ac4d-d648042cfa5e": "Arrogant Vampire",
    "60824fae-20ed-4122-82c9-e99a1b679c54": "Bog Raiders",
    "508248d1-09a4-4e41-a4c9-286618e5061e": "Bog Wraith",
    "4d62a448-b6a5-43b1-a281-9e9361a5524a": "Bull Hippo",
    "10706fd1-7847-4316-be8d-59b56143ce45": "Coral Eel",
    "ce8f4eb4-08b8-404b-9147-1e28c1b14a65": "Desert Drake",
    "72b42c63-fe4d-4823-9692-30fb5bab384a": "Djinn of the Lamp",
    "092f2c34-1f75-4998-b219-2cf1ca73656d": "Elvish Ranger",
    "cf26dcb4-e181-4ba5-bc03-b56f57032b85": "Feral Shadow",
    "c181d2a4-5959-4409-9bd3-ecedf8ec9516": "Giant Octopus",
    "e740ce2f-2134-473c-afa1-1b6d2d1e38ef": "Giant Spider",
    "56c5afdc-6777-45c7-8e2c-3cadecb95c5a": "Goblin Bully",
    "c0e6ae0f-6cf7-48ca-acb8-73d4c38b9005": "Gorilla Warrior",
    "14c8f55d-d177-4c25-a931-ebeb9e6062a0": "Grizzly Bears",
    "2f3878b8-61af-4276-b7ab-11b70e44eb62": "Highland Giant",
    "342199e0-15b6-4824-83da-25caef2592b3": "Hill Giant",
    "7a4ae76b-6241-4fa8-b239-5ec941a0e7df": "Horned Turtle",
    "920cc1a7-ac6b-44c0-ade7-347f05bba0f2": "Knight Errant",
    "123337af-f976-4956-949f-c650da812113": "Lizard Warrior",
    "218d9277-c179-4de3-9c7f-79b5a6d4fa38": "Merfolk of the Pearl Trident",
    "d334aa85-3470-4f5d-9cbc-b88bf991a5af": "Cloud Pirates",
    "9e1a6481-f460-4551-96e8-30b289f2cb92": "Cloud Spirit",
    "fff6f2d0-22b5-41d0-99dc-bc817c3bd166": "Devoted Hero",
    "9297e50f-f8a5-4793-b64d-a119404f94ce": "Elite Cat Warrior",
}


class Wave3CombatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFO)

    def test_wave_three_cards_load_from_the_active_support_slice(self) -> None:
        self.assertTrue(set(WAVE_THREE_CARD_NAMES).issubset(self.repository.allowed_oracle_ids))
        for oracle_id, name in WAVE_THREE_CARD_NAMES.items():
            with self.subTest(oracle_id=oracle_id):
                self.assertEqual(self.repository.get(oracle_id).name, name)

    def test_bull_hippo_islandwalk_excludes_blocks_from_enumeration_and_submission(self) -> None:
        state = _combat_state(
            self.repository,
            alice_cards=(BULL_HIPPO,),
            bob_cards=(ISLAND, MUCK_RATS),
            attacker_id="alice:1",
            blocker_id="bob:2",
        )

        actions = enumerate_legal_actions(state, self.repository)
        self.assertNotIn(
            DeclareBlockersAction(player_id="bob", blockers={"alice:1": ("bob:2",)}),
            actions,
        )
        with self.assertRaisesRegex(ValueError, "cannot block"):
            declare_blockers(
                TurnResult(state, ()),
                DeclareBlockersAction(player_id="bob", blockers={"alice:1": ("bob:2",)}),
                self.repository,
            )

    def test_bull_hippo_can_be_blocked_without_an_island(self) -> None:
        state = _combat_state(
            self.repository,
            alice_cards=(BULL_HIPPO,),
            bob_cards=(MUCK_RATS,),
            attacker_id="alice:1",
            blocker_id="bob:1",
        )
        action = DeclareBlockersAction(player_id="bob", blockers={"alice:1": ("bob:1",)})

        self.assertIn(action, enumerate_legal_actions(state, self.repository))
        result = declare_blockers(TurnResult(state, ()), action, self.repository)
        self.assertEqual(result.state.combat.blockers, {"alice:1": ("bob:1",)})

    def test_vigilance_attackers_stay_untapped(self) -> None:
        for card_id in (ARCHANGEL, ARDENT_MILITIA):
            with self.subTest(card_id=card_id):
                state = _attacker_declaration_state(self.repository, card_id)
                action = DeclareAttackersAction(player_id="alice", attacker_ids=("alice:1",))

                self.assertIn(action, enumerate_legal_actions(state, self.repository))
                result = declare_attackers(TurnResult(state, ()), action, self.repository)
                self.assertFalse(result.state.objects["alice:1"].tapped)

    def test_cloud_restriction_allows_only_flying_attackers(self) -> None:
        for blocker_card in (CLOUD_DRAGON, CLOUD_PIRATES, CLOUD_SPIRIT):
            with self.subTest(blocker_card=blocker_card):
                grounded_state = _combat_state(
                    self.repository,
                    alice_cards=(MUCK_RATS,),
                    bob_cards=(blocker_card,),
                    attacker_id="alice:1",
                    blocker_id="bob:1",
                )
                blocked_action = DeclareBlockersAction(player_id="bob", blockers={"alice:1": ("bob:1",)})
                self.assertNotIn(blocked_action, enumerate_legal_actions(grounded_state, self.repository))
                self.assertEqual(
                    blocker_attack_rejection_reason(
                        state=grounded_state,
                        card_repository=self.repository,
                        blocker_id="bob:1",
                        attacker_id="alice:1",
                    ),
                    f"{self.repository.get(blocker_card).name} can block only creatures with flying",
                )
                with self.assertRaisesRegex(ValueError, "can block only creatures with flying"):
                    declare_blockers(TurnResult(grounded_state, ()), blocked_action, self.repository)

                flying_state = _combat_state(
                    self.repository,
                    alice_cards=(ARMORED_PEGASUS,),
                    bob_cards=(blocker_card,),
                    attacker_id="alice:1",
                    blocker_id="bob:1",
                )
                self.assertIn(blocked_action, enumerate_legal_actions(flying_state, self.repository))
                declare_blockers(TurnResult(flying_state, ()), blocked_action, self.repository)


def _combat_state(
    repository: CardRepository,
    *,
    alice_cards: tuple[str, ...],
    bob_cards: tuple[str, ...],
    attacker_id: str,
    blocker_id: str,
):
    state = initialize_game(
        SetupInput("wave-three-combat", ("alice", "bob"), "alice", {"alice": alice_cards, "bob": bob_cards}, {"alice": alice_cards, "bob": bob_cards}, 1),
        repository,
    ).state
    for player_id, cards in (("alice", alice_cards), ("bob", bob_cards)):
        for index in range(1, len(cards) + 1):
            state = move_object(state, instance_id=f"{player_id}:{index}", from_zone="hand", to_zone="battlefield", player_id=player_id)
    state = with_combat_state(
        state,
        attacking_player="alice",
        defending_player="bob",
        attackers=(attacker_id,),
        blockers={},
    )
    return replace(state, turn=TurnState(1, "alice", "bob", "declare_blockers_step"))


def _attacker_declaration_state(repository: CardRepository, card_id: str):
    state = initialize_game(
        SetupInput("wave-three-vigilance", ("alice", "bob"), "alice", {"alice": (card_id,), "bob": ()}, {"alice": (card_id,), "bob": ()}, 1),
        repository,
    ).state
    state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
    return replace(state, turn=TurnState(2, "alice", "alice", "declare_attackers_step"))
