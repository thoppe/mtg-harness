from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import ActivateManaAbilityAction, CastCreatureSpellAction, DeclareAttackersAction, DeclareBlockersAction, PassPriorityAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.events.log import EventLog
from mtg_engine.flow.priority import blocker_attack_rejection_reason, enumerate_legal_actions
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import TurnResult, _destroy_permanents, activate_mana_ability, advance_to_begin_combat, advance_to_cleanup, cast_creature_spell, declare_attackers, declare_blockers, pass_priority, resolve_combat_damage, start_first_turn
from mtg_engine.rules.combat import apply_state_based_actions
from mtg_engine.state.zones import move_object


INFO = Path(__file__).resolve().parents[2] / "information"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
ARMORED_PEGASUS = "f097a059-5505-4c3c-b879-7853ab6972ed"
BULL_HIPPO = "4d62a448-b6a5-43b1-a281-9e9361a5524a"
ARCHANGEL = "9971697b-2acc-4bc2-a44e-074d03a51df7"
ARDENT_MILITIA = "23625877-b6db-480c-8885-a62b7d0457df"
CLOUD_DRAGON = "3c46f309-69ae-43b1-adf6-bdb26599c1f4"
CLOUD_PIRATES = "d334aa85-3470-4f5d-9cbc-b88bf991a5af"
CLOUD_SPIRIT = "9e1a6481-f460-4551-96e8-30b289f2cb92"
ALABASTER_DRAGON = "2392a41a-59d3-4749-be94-4d9df0af9c4c"
WAVE_THREE_CARD_NAMES = {
    "2392a41a-59d3-4749-be94-4d9df0af9c4c": "Alabaster Dragon",
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

    def test_alabaster_dragon_casts_for_its_full_mana_cost_and_resolves(self) -> None:
        lands = (PLAINS,) * 6
        state = initialize_game(
            SetupInput(
                "alabaster-cast",
                ("alice", "bob"),
                "alice",
                {"alice": lands + (ALABASTER_DRAGON,), "bob": ()},
                {"alice": lands + (ALABASTER_DRAGON,), "bob": ()},
                41,
            ),
            self.repository,
        ).state
        for instance_id in tuple(state.players["alice"].hand[:-1]):
            state = move_object(state, instance_id=instance_id, from_zone="hand", to_zone="battlefield", player_id="alice")
        session = start_first_turn(TurnResult(state, ()))
        for instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(session, ActivateManaAbilityAction("alice", instance_id), self.repository)

        stacked = cast_creature_spell(session, CastCreatureSpellAction("alice", "alice:7"), self.repository)
        after_alice_passes = pass_priority(stacked, PassPriorityAction("alice"), self.repository)
        resolved = pass_priority(after_alice_passes, PassPriorityAction("bob"), self.repository)

        self.assertEqual(resolved.state.objects["alice:7"].zone, "battlefield")
        self.assertEqual(self.repository.get(ALABASTER_DRAGON).mana_cost, "{4}{W}{W}")

    def test_alabaster_dragon_flying_rejects_a_nonflying_blocker(self) -> None:
        state = _combat_state(
            self.repository,
            alice_cards=(ALABASTER_DRAGON,),
            bob_cards=(MUCK_RATS,),
            attacker_id="alice:1",
            blocker_id="bob:1",
        )
        blocked_action = DeclareBlockersAction(player_id="bob", blockers={"alice:1": ("bob:1",)})

        self.assertEqual(
            blocker_attack_rejection_reason(
                state=state,
                card_repository=self.repository,
                blocker_id="bob:1",
                attacker_id="alice:1",
            ),
            "blocker cannot block the selected attacker",
        )
        with self.assertRaisesRegex(ValueError, "blocker cannot block"):
            declare_blockers(TurnResult(state, ()), blocked_action, self.repository)

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

    def test_alabaster_dragon_death_trigger_uses_stack_priority_then_shuffles(self) -> None:
        state = _alabaster_death_state(self.repository, seed=19)
        destroyed_state, events = apply_state_based_actions(
            state,
            self.repository,
            active_player="alice",
        )

        self.assertEqual(destroyed_state.objects["alice:1"].zone, "graveyard")
        self.assertEqual(destroyed_state.stack_entries[0].entry_kind, "alabaster_dragon_death_trigger")
        self.assertEqual(destroyed_state.stack_entries[0].source_object_id, "alice:1@1")
        self.assertEqual(destroyed_state.stack_entries[0].expected_graveyard_object_id, "alice:1@2")
        self.assertEqual(events[-1]["event_type"], "triggered_ability_put_on_stack")
        self.assertEqual(events[-2]["payload"]["from_object_id"], "alice:1@1")
        self.assertEqual(events[-2]["payload"]["to_object_id"], "alice:1@2")

        pending = TurnResult(destroyed_state, ())
        after_alice_passes = pass_priority(
            pending,
            PassPriorityAction(player_id="alice"),
            self.repository,
        )
        self.assertEqual(after_alice_passes.state.turn.priority_player, "bob")
        self.assertEqual(len(after_alice_passes.state.stack_entries), 1)

        resolved = pass_priority(
            after_alice_passes,
            PassPriorityAction(player_id="bob"),
            self.repository,
        )
        self.assertEqual(resolved.state.objects["alice:1"].zone, "library")
        self.assertIn("alice:1", resolved.state.players["alice"].library)
        self.assertEqual(resolved.state.rng_cursor, 1)
        self.assertEqual(resolved.state.stack_entries, ())
        self.assertEqual(
            [event.event_type for event in resolved.event_log[-4:]],
            [
                "priority_passed",
                "object_moved_between_zones",
                "library_shuffled",
                "triggered_ability_resolved",
            ],
        )

    def test_alabaster_dragon_shuffle_is_seed_deterministic(self) -> None:
        final_libraries = []
        for _ in range(2):
            state = _alabaster_death_state(self.repository, seed=23)
            destroyed_state, _ = apply_state_based_actions(state, self.repository, active_player="alice")
            pending = TurnResult(destroyed_state, ())
            pending = pass_priority(pending, PassPriorityAction(player_id="alice"), self.repository)
            resolved = pass_priority(pending, PassPriorityAction(player_id="bob"), self.repository)
            final_libraries.append(resolved.state.players["alice"].library)
        self.assertEqual(final_libraries[0], final_libraries[1])

    def test_simultaneous_alabaster_deaths_use_two_player_apnap_stack_order(self) -> None:
        state = initialize_game(
            SetupInput(
                "alabaster-apnap",
                ("alice", "bob"),
                "alice",
                {"alice": (ALABASTER_DRAGON,), "bob": (ALABASTER_DRAGON,)},
                {"alice": (ALABASTER_DRAGON,), "bob": (ALABASTER_DRAGON,)},
                43,
            ),
            self.repository,
        ).state
        for player_id in ("alice", "bob"):
            state = move_object(state, instance_id=f"{player_id}:1", from_zone="hand", to_zone="battlefield", player_id=player_id)
        state = replace(
            state,
            objects={
                **state.objects,
                "alice:1": replace(state.objects["alice:1"], damage_marked=4),
                "bob:1": replace(state.objects["bob:1"], damage_marked=4),
            },
        )

        destroyed_state, _ = apply_state_based_actions(state, self.repository, active_player="alice")

        self.assertEqual([entry.controller_id for entry in destroyed_state.stack_entries], ["alice", "bob"])

    def test_game_ending_sba_does_not_queue_alabaster_trigger(self) -> None:
        state = _alabaster_death_state(self.repository, seed=47)
        state = replace(
            state,
            players={**state.players, "bob": replace(state.players["bob"], life_total=0)},
        )

        destroyed_state, events = apply_state_based_actions(state, self.repository, active_player="alice")

        self.assertEqual(destroyed_state.outcome.status, "completed")
        self.assertEqual(destroyed_state.stack_entries, ())
        self.assertNotIn("triggered_ability_put_on_stack", [event["event_type"] for event in events])

    def test_destroy_effect_path_enqueues_alabaster_trigger(self) -> None:
        state = _alabaster_death_state(self.repository, seed=29)
        dragon = replace(state.objects["alice:1"], damage_marked=0)
        state = replace(state, objects={**state.objects, "alice:1": dragon})
        event_log = EventLog(game_id=state.game_id)

        destroyed_state, destroyed_count = _destroy_permanents(
            state,
            event_log,
            instance_ids=("alice:1",),
            active_player="bob",
            reason="test_destroy",
        )

        self.assertEqual(destroyed_count, 1)
        self.assertEqual(destroyed_state.objects["alice:1"].zone, "graveyard")
        self.assertEqual(destroyed_state.stack_entries[0].entry_kind, "alabaster_dragon_death_trigger")
        self.assertEqual(event_log.events[-1].event_type, "triggered_ability_put_on_stack")

    def test_alabaster_trigger_is_a_no_op_if_source_left_graveyard(self) -> None:
        state = _alabaster_death_state(self.repository, seed=31)
        destroyed_state, _ = apply_state_based_actions(state, self.repository, active_player="alice")
        moved_state = move_object(
            destroyed_state,
            instance_id="alice:1",
            from_zone="graveyard",
            to_zone="hand",
            player_id="alice",
        )

        pending = TurnResult(moved_state, ())
        pending = pass_priority(pending, PassPriorityAction(player_id="alice"), self.repository)
        resolved = pass_priority(pending, PassPriorityAction(player_id="bob"), self.repository)

        self.assertEqual(resolved.state.objects["alice:1"].zone, "hand")
        self.assertEqual(resolved.state.rng_cursor, 0)
        self.assertNotIn("library_shuffled", [event.event_type for event in resolved.event_log])
        self.assertFalse(resolved.event_log[-1].payload["moved_to_library"])

    def test_alabaster_trigger_is_a_no_op_after_leaving_and_returning_to_graveyard(self) -> None:
        state = _alabaster_death_state(self.repository, seed=37)
        destroyed_state, _ = apply_state_based_actions(state, self.repository, active_player="alice")
        moved_state = move_object(
            destroyed_state,
            instance_id="alice:1",
            from_zone="graveyard",
            to_zone="hand",
            player_id="alice",
        )
        returned_state = move_object(
            moved_state,
            instance_id="alice:1",
            from_zone="hand",
            to_zone="graveyard",
            player_id="alice",
        )

        pending = TurnResult(returned_state, ())
        pending = pass_priority(pending, PassPriorityAction(player_id="alice"), self.repository)
        resolved = pass_priority(pending, PassPriorityAction(player_id="bob"), self.repository)

        self.assertEqual(resolved.state.objects["alice:1"].zone, "graveyard")
        self.assertEqual(resolved.state.rng_cursor, 0)
        self.assertFalse(resolved.event_log[-1].payload["moved_to_library"])

    def test_alabaster_combat_death_resolves_before_combat_can_end(self) -> None:
        state = _combat_state(
            self.repository,
            alice_cards=(ARCHANGEL,),
            bob_cards=(ALABASTER_DRAGON,),
            attacker_id="alice:1",
            blocker_id="bob:1",
        )
        blocked = declare_blockers(
            TurnResult(state, ()),
            DeclareBlockersAction(player_id="bob", blockers={"alice:1": ("bob:1",)}),
            self.repository,
        )
        damaged = resolve_combat_damage(blocked, self.repository)

        self.assertEqual(damaged.state.turn.step, "combat_damage_step")
        self.assertEqual(damaged.state.turn.priority_player, "alice")
        self.assertEqual(len(damaged.state.stack_entries), 1)
        with self.assertRaisesRegex(ValueError, "end_combat_step"):
            advance_to_cleanup(damaged)

        after_alice_passes = pass_priority(damaged, PassPriorityAction(player_id="alice"), self.repository)
        resolved = pass_priority(after_alice_passes, PassPriorityAction(player_id="bob"), self.repository)
        self.assertEqual(resolved.state.objects["bob:1"].zone, "library")
        self.assertEqual(resolved.state.turn.step, "combat_damage_step")
        passed_once = pass_priority(resolved, PassPriorityAction(player_id="alice"), self.repository)
        ended = pass_priority(passed_once, PassPriorityAction(player_id="bob"), self.repository)
        self.assertEqual(ended.state.turn.step, "end_combat_step")


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


def _attacker_declaration_state(repository: CardRepository, card_id: str):
    bootstrap = initialize_game(
        SetupInput("wave-three-vigilance", ("alice", "bob"), "alice", {"alice": (card_id,), "bob": ()}, {"alice": (card_id,), "bob": ()}, 1),
        repository,
    )
    state = bootstrap.state
    state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
    state = replace(
        state,
        objects={
            **state.objects,
            "alice:1": replace(state.objects["alice:1"], entered_battlefield_turn=0),
        },
    )
    started = start_first_turn(replace(bootstrap, state=state))
    return advance_to_begin_combat(started).state


def _alabaster_death_state(repository: CardRepository, *, seed: int):
    bootstrap = initialize_game(
        SetupInput(
            "alabaster-death",
            ("alice", "bob"),
            "alice",
            {"alice": (ALABASTER_DRAGON, MUCK_RATS, ISLAND), "bob": ()},
            {"alice": (ALABASTER_DRAGON,), "bob": ()},
            seed,
        ),
        repository,
    )
    state = bootstrap.state
    state = move_object(state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
    damaged_dragon = replace(state.objects["alice:1"], damage_marked=4)
    state = replace(
        state,
        objects={**state.objects, "alice:1": damaged_dragon},
    )
    return start_first_turn(replace(bootstrap, state=state)).state
