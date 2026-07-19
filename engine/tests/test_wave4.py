from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import DeclareAttackersAction, DeclareBlockersAction, PassPriorityAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.priority import (
    attacker_attack_rejection_reason,
    blocker_attack_rejection_reason,
    enumerate_legal_actions,
)
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import (
    TurnResult,
    advance_to_begin_combat,
    declare_attackers,
    declare_blockers,
    pass_priority,
    start_first_turn,
)
from mtg_engine.state.models import TurnState
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
ARMORED_PEGASUS = "f097a059-5505-4c3c-b879-7853ab6972ed"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
MOUNTAIN_GOAT = "031cd561-d9b1-4a0e-bc38-bc09e80563c3"
RAGING_GOBLIN = "30997b43-fc13-41d3-8064-1ccc2cb6fd2b"
RAGING_COUGAR = "695ebb35-55fd-4ed1-8cbe-e3fc1223115b"
RAGING_MINOTAUR = "4cfd04b3-57bd-4860-8b47-57a0fd0a23fa"
VOLCANIC_DRAGON = "994db177-03f5-43dd-bf7b-2994e8d430d3"
SKELETAL_CROCODILE = "90f9440a-0bf8-46eb-9cfa-16fb88a217d8"
WALL_OF_SWORDS = "eb098958-50d3-4476-ba74-382033703ff9"
WHIPTAIL_WURM = "50fa6a63-e031-47cb-8fd5-a6c235203722"
WILLOW_DRYAD = "19d5eb29-2d35-44e7-afa1-3ba8d812ed41"

WAVE_FOUR_CARDS = {
    "53fb9a9b-1f5d-48c9-88c0-0864c187f15e": "Minotaur Warrior",
    "1e41136b-afa7-45ee-8d04-d0c7514b5387": "Moon Sprite",
    MOUNTAIN_GOAT: "Mountain Goat",
    "ef7788af-8edc-46df-a5b6-895c734ea423": "Panther Warriors",
    "d8a0c3ff-7042-4b52-a216-15e170c8094f": "Python",
    RAGING_GOBLIN: "Raging Goblin",
    RAGING_COUGAR: "Raging Cougar",
    RAGING_MINOTAUR: "Raging Minotaur",
    "2cdebbc2-2e0b-4d26-bb7f-4736f0318ca7": "Redwood Treefolk",
    "2b856a43-ca6b-4f08-b610-9794ee6d7fcf": "Regal Unicorn",
    "ae37dd07-2926-4801-b89d-3ffad9f0f575": "Rowan Treefolk",
    VOLCANIC_DRAGON: "Volcanic Dragon",
    SKELETAL_CROCODILE: "Skeletal Crocodile",
    "7af786a0-0851-4f87-ad0d-36b40527700c": "Skeletal Snake",
    "e15060c3-3773-4548-8747-ff59dcf2b519": "Snapping Drake",
    "05425f2f-7228-4bf5-8fe1-6fe99107e8e0": "Spined Wurm",
    "4916773d-5ccb-48ff-8aa3-09771ae88e81": "Spotted Griffin",
    "e66e3450-bddb-46ac-bc7e-c7732e258374": "Starlit Angel",
    WALL_OF_SWORDS: "Wall of Swords",
    WHIPTAIL_WURM: "Whiptail Wurm",
    WILLOW_DRYAD: "Willow Dryad",
}


class Wave4CombatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFO)

    def test_wave_four_cards_load_from_the_active_support_slice(self) -> None:
        self.assertTrue(set(WAVE_FOUR_CARDS).issubset(self.repository.allowed_oracle_ids))
        for oracle_id, name in WAVE_FOUR_CARDS.items():
            with self.subTest(oracle_id=oracle_id):
                self.assertEqual(self.repository.get(oracle_id).name, name)

    def test_mountainwalk_excludes_blocks_only_when_defender_controls_a_mountain(self) -> None:
        mountain_state = _combat_state(
            self.repository,
            alice_cards=(MOUNTAIN_GOAT,),
            bob_cards=(MOUNTAIN, MUCK_RATS),
            attacker_id="alice:1",
            blocker_id="bob:2",
        )
        blocked_action = DeclareBlockersAction("bob", {"alice:1": ("bob:2",)})

        self.assertEqual(
            blocker_attack_rejection_reason(
                state=mountain_state,
                card_repository=self.repository,
                blocker_id="bob:2",
                attacker_id="alice:1",
            ),
            "blocker cannot block the selected attacker",
        )
        self.assertNotIn(blocked_action, enumerate_legal_actions(mountain_state, self.repository))
        with self.assertRaisesRegex(ValueError, "cannot block"):
            declare_blockers(TurnResult(mountain_state, ()), blocked_action, self.repository)

        no_mountain_state = _combat_state(
            self.repository,
            alice_cards=(MOUNTAIN_GOAT,),
            bob_cards=(MUCK_RATS,),
            attacker_id="alice:1",
            blocker_id="bob:1",
        )
        allowed_action = DeclareBlockersAction("bob", {"alice:1": ("bob:1",)})
        self.assertIn(allowed_action, enumerate_legal_actions(no_mountain_state, self.repository))
        self.assertEqual(
            declare_blockers(TurnResult(no_mountain_state, ()), allowed_action, self.repository).state.combat.blockers,
            {"alice:1": ("bob:1",)},
        )

    def test_haste_creatures_can_attack_on_the_turn_they_enter(self) -> None:
        for card_id in (RAGING_GOBLIN, RAGING_COUGAR, RAGING_MINOTAUR, VOLCANIC_DRAGON):
            with self.subTest(card_id=card_id):
                state = _attacker_declaration_state(self.repository, card_id, turn_number=1)
                action = DeclareAttackersAction("alice", ("alice:1",))

                self.assertIsNone(
                    attacker_attack_rejection_reason(
                        state=state,
                        card_repository=self.repository,
                        attacker_id="alice:1",
                    )
                )
                self.assertIn(action, enumerate_legal_actions(state, self.repository))
                self.assertTrue(declare_attackers(TurnResult(state, ()), action, self.repository).state.objects["alice:1"].tapped)

    def test_haste_exception_does_not_allow_a_nonhaste_creature_to_attack_immediately(self) -> None:
        state = _attacker_declaration_state(self.repository, SKELETAL_CROCODILE, turn_number=1)

        self.assertEqual(
            attacker_attack_rejection_reason(
                state=state,
                card_repository=self.repository,
                attacker_id="alice:1",
            ),
            "summoning-sick creature cannot attack in v0",
        )

    def test_volcanic_dragon_reuses_flying_evasion(self) -> None:
        state = _combat_state(
            self.repository,
            alice_cards=(VOLCANIC_DRAGON,),
            bob_cards=(MUCK_RATS,),
            attacker_id="alice:1",
            blocker_id="bob:1",
        )

        self.assertEqual(
            blocker_attack_rejection_reason(
                state=state,
                card_repository=self.repository,
                blocker_id="bob:1",
                attacker_id="alice:1",
            ),
            "blocker cannot block the selected attacker",
        )

    def test_wall_of_swords_reuses_defender_and_flying(self) -> None:
        attacker_state = _attacker_declaration_state(self.repository, WALL_OF_SWORDS, turn_number=2)
        self.assertEqual(
            attacker_attack_rejection_reason(
                state=attacker_state,
                card_repository=self.repository,
                attacker_id="alice:1",
            ),
            "creature with defender cannot attack",
        )

        blocker_state = _combat_state(
            self.repository,
            alice_cards=(ARMORED_PEGASUS,),
            bob_cards=(WALL_OF_SWORDS,),
            attacker_id="alice:1",
            blocker_id="bob:1",
        )
        self.assertIsNone(
            blocker_attack_rejection_reason(
                state=blocker_state,
                card_repository=self.repository,
                blocker_id="bob:1",
                attacker_id="alice:1",
            )
        )

    def test_willow_dryad_reuses_forestwalk(self) -> None:
        state = _combat_state(
            self.repository,
            alice_cards=(WILLOW_DRYAD,),
            bob_cards=(FOREST, MUCK_RATS),
            attacker_id="alice:1",
            blocker_id="bob:2",
        )
        self.assertEqual(
            blocker_attack_rejection_reason(
                state=state,
                card_repository=self.repository,
                blocker_id="bob:2",
                attacker_id="alice:1",
            ),
            "blocker cannot block the selected attacker",
        )


def _combat_state(
    repository: CardRepository,
    *,
    alice_cards: tuple[str, ...],
    bob_cards: tuple[str, ...],
    attacker_id: str,
    blocker_id: str,
):
    state = initialize_game(
        SetupInput("wave-four-combat", ("alice", "bob"), "alice", {"alice": alice_cards, "bob": bob_cards}, {"alice": alice_cards, "bob": bob_cards}, 1),
        repository,
    ).state
    for player_id, cards in (("alice", alice_cards), ("bob", bob_cards)):
        for index in range(1, len(cards) + 1):
            state = move_object(state, instance_id=f"{player_id}:{index}", from_zone="hand", to_zone="battlefield", player_id=player_id)
    state = replace(
        state,
        objects={
            **state.objects,
            attacker_id: replace(state.objects[attacker_id], entered_battlefield_turn=0),
        },
    )
    session = start_first_turn(TurnResult(state, ()))
    session = advance_to_begin_combat(session)
    session = declare_attackers(
        session,
        DeclareAttackersAction(player_id="alice", attacker_ids=(attacker_id,)),
        repository,
    )
    session = pass_priority(
        session,
        PassPriorityAction(player_id="alice"),
        repository,
    )
    return pass_priority(
        session,
        PassPriorityAction(player_id="bob"),
        repository,
    ).state


def _attacker_declaration_state(repository: CardRepository, card_id: str, *, turn_number: int):
    state = initialize_game(
        SetupInput("wave-four-attackers", ("alice", "bob"), "alice", {"alice": (card_id,), "bob": ()}, {"alice": (card_id,), "bob": ()}, 1),
        repository,
    ).state
    state = replace(state, turn=TurnState(turn_number, "alice", "alice", "precombat_main_step"))
    state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
    return replace(state, turn=TurnState(turn_number, "alice", "alice", "declare_attackers_step"))
