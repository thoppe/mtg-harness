from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateAbilityAction,
    ActivateManaAbilityAction,
    AdvanceStepAction,
    AdvanceTurnAction,
    CastCreatureSpellAction,
    CastNonCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PassPriorityAction,
    PlayLandAction,
    ResolveChoiceAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import (
    activate_ability,
    activate_mana_ability,
    advance_step,
    advance_turn,
    cast_creature_spell,
    cast_noncreature_spell,
    declare_attackers,
    declare_blockers,
    pass_priority,
    play_land,
    resolve_pending_choice,
    start_first_turn,
)
from mtg_engine.replay.reducer import ReplayInput, replay


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
SORCEROUS_SIGHT = "20370c3b-231f-4d9d-8b6e-f1eb25fa4b5d"
PERSONAL_TUTOR = "90f54959-2c9b-4b8a-84c9-d6893eb43553"
RAIN_OF_TEARS = "72cecab3-519e-4a23-9623-b423a5c5a251"
CAPRICIOUS_SORCERER = "09fe624f-c66a-46e4-a9af-7e3c3ca1a4e3"


class ReplayReducerTests(unittest.TestCase):
    def test_replays_turn_handoffs_and_aged_activated_ability(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-reducer-activated-ability",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (
                    ISLAND,
                    ISLAND,
                    ISLAND,
                    CAPRICIOUS_SORCERER,
                    PLAINS,
                    PLAINS,
                    PLAINS,
                    PLAINS,
                ),
                "bob": (SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, SWAMP),
            },
            opening_hands={
                "alice": (ISLAND, ISLAND, ISLAND, CAPRICIOUS_SORCERER),
                "bob": (SWAMP,),
            },
            rng_seed=76,
        )

        actions: list[object] = []
        for turn_number in range(1, 7):
            active = "alice" if turn_number % 2 else "bob"
            defending = "bob" if active == "alice" else "alice"
            if turn_number in {1, 3, 5}:
                land_id = {1: "alice:1", 3: "alice:2", 5: "alice:3"}[turn_number]
                actions.append(PlayLandAction(active, land_id))
            if turn_number == 5:
                actions.extend(
                    (
                        ActivateManaAbilityAction(active, "alice:1"),
                        ActivateManaAbilityAction(active, "alice:2"),
                        ActivateManaAbilityAction(active, "alice:3"),
                        CastCreatureSpellAction(active, "alice:4"),
                        PassPriorityAction(active),
                        PassPriorityAction(defending),
                    )
                )
            actions.extend(
                (
                    AdvanceStepAction(active, "begin_combat_step"),
                    DeclareAttackersAction(active, ()),
                    PassPriorityAction(active),
                    PassPriorityAction(defending),
                    DeclareBlockersAction(defending, {}),
                    AdvanceTurnAction(active),
                )
            )
        actions.extend(
            (
                ActivateAbilityAction("alice", "alice:4", target_instance_id="bob"),
                PassPriorityAction("alice"),
                PassPriorityAction("bob"),
            )
        )

        direct = start_first_turn(initialize_game(setup, repository))
        for action in actions:
            if isinstance(action, PlayLandAction):
                direct = play_land(direct, action, repository)
            elif isinstance(action, ActivateManaAbilityAction):
                direct = activate_mana_ability(direct, action, repository)
            elif isinstance(action, CastCreatureSpellAction):
                direct = cast_creature_spell(direct, action, repository)
            elif isinstance(action, PassPriorityAction):
                direct = pass_priority(direct, action, repository)
            elif isinstance(action, AdvanceStepAction):
                direct = advance_step(direct, action)
            elif isinstance(action, DeclareAttackersAction):
                direct = declare_attackers(direct, action, repository)
            elif isinstance(action, DeclareBlockersAction):
                direct = declare_blockers(direct, action, repository)
            elif isinstance(action, AdvanceTurnAction):
                direct = advance_turn(direct, action, repository)
            elif isinstance(action, ActivateAbilityAction):
                direct = activate_ability(direct, action, repository)

        reduced = replay(ReplayInput(setup=setup, actions=tuple(actions)), repository)

        self.assertEqual(reduced.state, direct.state)
        self.assertEqual(reduced.event_log, direct.event_log)
        self.assertEqual(reduced.state.turn.turn_number, 7)
        self.assertEqual(reduced.state.players["bob"].life_total, 19)
        self.assertEqual(reduced.state.objects["alice:4"].zone, "battlefield")
        self.assertTrue(reduced.state.objects["alice:4"].tapped)

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

    def test_replays_empty_combat_declarations_and_response_passes(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-reducer-combat",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={"alice": (PLAINS,), "bob": (SWAMP,)},
            opening_hands={"alice": (PLAINS,), "bob": (SWAMP,)},
            rng_seed=73,
        )
        actions = (
            AdvanceStepAction(player_id="alice", to_step="begin_combat_step"),
            DeclareAttackersAction(player_id="alice", attacker_ids=()),
            PassPriorityAction(player_id="alice"),
            PassPriorityAction(player_id="bob"),
            DeclareBlockersAction(player_id="bob", blockers={}),
        )

        direct = start_first_turn(initialize_game(setup, repository))
        direct = advance_step(direct, actions[0])
        direct = declare_attackers(direct, actions[1], repository)
        direct = pass_priority(direct, actions[2], repository)
        direct = pass_priority(direct, actions[3], repository)
        direct = declare_blockers(direct, actions[4], repository)
        reduced = replay(ReplayInput(setup=setup, actions=actions), repository)

        self.assertEqual(reduced.state, direct.state)
        self.assertEqual(reduced.event_log, direct.event_log)
        self.assertEqual(reduced.state.turn.step, "combat_damage_step")
        self.assertEqual(
            [event.event_type for event in reduced.event_log[-4:]],
            [
                "priority_passed",
                "step_changed",
                "blockers_declared",
                "step_changed",
            ],
        )

    def test_replays_targeted_noncreature_cast_resolution_and_draw(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-reducer-sorcery",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (ISLAND, SORCEROUS_SIGHT, PLAINS),
                "bob": (SWAMP,),
            },
            opening_hands={
                "alice": (ISLAND, SORCEROUS_SIGHT),
                "bob": (SWAMP,),
            },
            rng_seed=74,
        )
        actions = (
            PlayLandAction(player_id="alice", card_instance_id="alice:1"),
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:2",
                target_instance_id="bob",
            ),
            PassPriorityAction(player_id="alice"),
            PassPriorityAction(player_id="bob"),
        )

        direct = start_first_turn(initialize_game(setup, repository))
        direct = play_land(direct, actions[0], repository)
        direct = activate_mana_ability(direct, actions[1], repository)
        direct = cast_noncreature_spell(direct, actions[2], repository)
        direct = pass_priority(direct, actions[3], repository)
        direct = pass_priority(direct, actions[4], repository)
        reduced = replay(ReplayInput(setup=setup, actions=actions), repository)

        self.assertEqual(reduced.state, direct.state)
        self.assertEqual(reduced.event_log, direct.event_log)
        self.assertEqual(reduced.state.players["alice"].hand, ("alice:3",))
        self.assertEqual(reduced.state.players["alice"].graveyard, ("alice:2",))
        self.assertEqual(
            [event.event_type for event in reduced.event_log[-4:]],
            [
                "spell_resolved",
                "hand_looked_at",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_replays_private_tutor_choice_shuffle_and_topdeck(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="replay-reducer-choice",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (ISLAND, PERSONAL_TUTOR, RAIN_OF_TEARS, MUCK_RATS),
                "bob": (PLAINS,),
            },
            opening_hands={
                "alice": (ISLAND, PERSONAL_TUTOR),
                "bob": (PLAINS,),
            },
            rng_seed=75,
        )
        prefix = (
            PlayLandAction(player_id="alice", card_instance_id="alice:1"),
            ActivateManaAbilityAction(player_id="alice", source_instance_id="alice:1"),
            CastNonCreatureSpellAction(player_id="alice", card_instance_id="alice:2"),
            PassPriorityAction(player_id="alice"),
            PassPriorityAction(player_id="bob"),
        )

        direct = start_first_turn(initialize_game(setup, repository))
        direct = play_land(direct, prefix[0], repository)
        direct = activate_mana_ability(direct, prefix[1], repository)
        direct = cast_noncreature_spell(direct, prefix[2], repository)
        direct = pass_priority(direct, prefix[3], repository)
        direct = pass_priority(direct, prefix[4], repository)
        decision = direct.state.pending_decision
        self.assertIsNotNone(decision)
        choice = ResolveChoiceAction(
            player_id="alice",
            decision_id=decision.decision_id,
            selected_instance_id="alice:3",
        )
        direct = resolve_pending_choice(direct, choice, repository)
        reduced = replay(
            ReplayInput(setup=setup, actions=prefix + (choice,)),
            repository,
        )

        self.assertEqual(reduced.state, direct.state)
        self.assertEqual(reduced.event_log, direct.event_log)
        self.assertEqual(reduced.state.players["alice"].library[0], "alice:3")
        self.assertEqual(reduced.state.rng_cursor, 1)
        self.assertEqual(
            [event.event_type for event in reduced.event_log[-4:]],
            [
                "object_moved_between_zones",
                "choice_resolved",
                "library_shuffled",
                "card_revealed",
            ],
        )

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
