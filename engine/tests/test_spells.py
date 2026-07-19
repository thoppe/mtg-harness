from __future__ import annotations

from dataclasses import replace
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
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
from mtg_engine.flow.priority import enumerate_legal_actions
from mtg_engine.flow.turns import (
    activate_mana_ability,
    advance_to_cleanup,
    cast_creature_spell,
    cast_noncreature_spell as _cast_noncreature_spell,
    declare_attackers,
    declare_blockers,
    pass_priority,
    play_land,
    resolve_combat_damage,
    resolve_pending_choice,
    start_first_turn,
    start_next_turn,
)
from mtg_engine.state.zones import move_object, update_object


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
FOOT_SOLDIERS = "a768ba13-4d1c-4dce-a4a6-86a39c069c3f"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
VENGEANCE = "1d001145-5d14-43a9-bf3b-3ce5c20b2a46"
PATH_OF_PEACE = "b7593cf8-4dcb-473b-a2ef-180fffe66738"
HAND_OF_DEATH = "dc45b2e3-272b-479b-8e3b-36eead606a3a"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
TOUCH_OF_BRILLIANCE = "6365aba1-78d3-416c-89cd-9449578eedbf"
TIME_EBB = "30cc8f7b-3c28-40f5-8f8f-157e8212280b"
TIDAL_SURGE = "be738992-77fe-498d-b219-e5da4ce5bf07"
VOLCANIC_HAMMER = "98fa5a06-0553-40fd-999c-bc31c9b3f4db"
LAVA_AXE = "387b6b07-a283-412d-94c3-f7f1dc76e858"
MIND_ROT = "ad44cf74-b717-48fb-9fa2-77512024d76a"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
WINTERS_GRASP = "e9b8679d-52a9-4f0f-9365-f3e4b7a69805"
SYMBOL_OF_UNSUMMONING = "c44f1a81-269b-4f05-8ff2-e7ce19a93937"
ARMAGEDDON = "c9ed8b01-959a-47d6-891e-0abbdccf6e4f"
RAIN_OF_SALT = "1219e330-01ac-405a-b75a-dd4298598167"
SACRED_NECTAR = "30870ee5-6ad7-48a9-983e-d3b018f2344f"
ARMORED_PEGASUS = "f097a059-5505-4c3c-b879-7853ab6972ed"
WIND_DRAKE = "d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca"
BOG_IMP = "45b94e3c-a905-435b-aee5-bec9239fd24c"
STORM_CROW = "000d5588-5a4c-434e-988d-396632ade42c"
KEEN_EYED_ARCHERS = "0ace32d6-7261-447c-9ee2-e03febaab91b"
ANACONDA = "3eff03f1-2c5f-4c59-b465-a8c4cd05e1ba"
WALL_OF_GRANITE = "8445094f-008b-491a-977c-e8582d5ab72c"
WRATH_OF_GOD = "34515b16-c9a4-4f98-8c77-416a7a523407"
RAIN_OF_DAGGERS = "e2048201-6dc9-4cf5-916f-1d867ae8dbdd"


def cast_noncreature_spell(session, action, repository):
    """Resolve a noncreature spell after both players pass priority in test setups."""
    stacked = _cast_noncreature_spell(session, action, repository)
    after_controller_pass = pass_priority(
        stacked,
        PassPriorityAction(player_id=action.player_id),
        repository,
    )
    resolved = pass_priority(
        after_controller_pass,
        PassPriorityAction(player_id=after_controller_pass.state.turn.priority_player),
        repository,
    )
    # Existing effect assertions focus on the spell trace; the dedicated stack
    # test below owns the two priority-pass assertions.
    return replace(
        resolved,
        event_log=tuple(event for event in resolved.event_log if event.event_type != "priority_passed"),
    )


class SpellTests(unittest.TestCase):
    def test_setup_allows_multiple_copies_from_declared_universe(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        setup = SetupInput(
            game_id="spell-setup",
            players=("alice", "bob"),
            starting_player="alice",
            libraries={
                "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
                "bob": (PLAINS,),
            },
            opening_hands={
                "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
                "bob": (PLAINS,),
            },
            rng_seed=11,
        )

        bootstrap = initialize_game(setup, repository)
        self.assertEqual(len(bootstrap.state.players["alice"].hand), 4)

    def test_cast_border_guard_with_three_plains(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_castable_main_phase_session(repository)
        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4"))
        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            ["spell_cast", "object_moved_between_zones", "spell_resolved", "object_moved_between_zones"],
        )

    def test_cast_foot_soldiers_with_four_plains(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_foot_soldiers_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:5")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5"))
        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.objects["alice:5"].zone, "battlefield")
        self.assertEqual(result.state.objects["alice:5"].oracle_id, FOOT_SOLDIERS)
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            ["spell_cast", "object_moved_between_zones", "spell_resolved", "object_moved_between_zones"],
        )

    def test_cast_muck_rats_with_swamp(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_muck_rats_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:2")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2"))
        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.objects["alice:2"].zone, "battlefield")
        self.assertEqual(result.state.objects["alice:2"].oracle_id, MUCK_RATS)

    def test_cast_armored_pegasus_with_two_plains(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_armored_pegasus_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:3")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3"))
        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.objects["alice:3"].zone, "battlefield")
        self.assertEqual(result.state.objects["alice:3"].oracle_id, ARMORED_PEGASUS)
        self.assertTrue(repository.get(ARMORED_PEGASUS).has_flying)

    def test_cast_wind_drake_with_two_islands_and_one_generic(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_wind_drake_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4"))
        self.assertEqual(result.state.objects["alice:4"].oracle_id, WIND_DRAKE)
        self.assertTrue(repository.get(WIND_DRAKE).has_flying)

    def test_cast_bog_imp_with_two_swamps(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_bog_imp_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:3")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3"))
        self.assertEqual(result.state.objects["alice:3"].oracle_id, BOG_IMP)
        self.assertTrue(repository.get(BOG_IMP).has_flying)

    def test_cast_storm_crow_with_two_islands(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_storm_crow_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:3")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3"))
        self.assertEqual(result.state.objects["alice:3"].oracle_id, STORM_CROW)
        self.assertTrue(repository.get(STORM_CROW).has_flying)

    def test_cast_keen_eyed_archers_with_two_plains_and_one_generic(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_keen_eyed_archers_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4"))
        self.assertEqual(result.state.objects["alice:4"].oracle_id, KEEN_EYED_ARCHERS)
        self.assertTrue(repository.get(KEEN_EYED_ARCHERS).has_reach)

    def test_cast_anaconda_with_one_forest_and_three_generic(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_anaconda_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:5")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5"))
        self.assertEqual(result.state.objects["alice:5"].oracle_id, ANACONDA)
        self.assertTrue(repository.get(ANACONDA).has_swampwalk)

    def test_cast_wall_of_granite_with_two_mountains_and_one_generic(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_wall_of_granite_session(repository)

        result = _cast_creature_from_normal_turns(session, repository, "alice", "alice:4")

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4"))
        self.assertEqual(result.state.objects["alice:4"].oracle_id, WALL_OF_GRANITE)
        self.assertTrue(repository.get(WALL_OF_GRANITE).has_defender)

    def test_cast_vengeance_destroys_tapped_creature_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_vengeance_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:5",))
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1",))
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.objects["alice:5"].zone, "graveyard")
        self.assertEqual(result.state.objects["alice:5"].oracle_id, VENGEANCE)
        self.assertEqual(result.state.objects["bob:1"].zone, "graveyard")
        self.assertEqual(
            [event.event_type for event in result.event_log[-6:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_cast_path_of_peace_destroys_creature_and_grants_owner_life(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_path_of_peace_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(result.state.players["alice"].hand, ())
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:5",))
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1",))
        self.assertEqual(result.state.players["bob"].life_total, 24)
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.objects["alice:5"].zone, "graveyard")
        self.assertEqual(result.state.objects["alice:5"].oracle_id, PATH_OF_PEACE)
        self.assertEqual(result.state.objects["bob:1"].zone, "graveyard")
        self.assertEqual(
            [event.event_type for event in result.event_log[-7:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "life_total_changed",
                "object_moved_between_zones",
            ],
        )

    def test_cast_hand_of_death_destroys_nonblack_creature_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_hand_of_death_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(result.state.players["alice"].graveyard, ("alice:4",))
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1",))
        self.assertEqual(result.state.players["bob"].battlefield, ("bob:2",))
        self.assertEqual(result.state.objects["alice:4"].oracle_id, HAND_OF_DEATH)
        self.assertEqual(result.state.objects["bob:1"].zone, "graveyard")
        self.assertEqual(result.state.objects["bob:2"].zone, "battlefield")
        self.assertEqual(
            [event.event_type for event in result.event_log[-6:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_destroyed",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_cast_hand_of_death_rejects_black_creature_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_hand_of_death_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        with self.assertRaisesRegex(ValueError, "target must be nonblack creature"):
            cast_noncreature_spell(
                session,
                CastNonCreatureSpellAction(
                    player_id="alice",
                    card_instance_id="alice:4",
                    target_instance_id="bob:2",
                ),
                repository,
            )

    def test_targeted_spell_is_countered_when_its_only_target_is_gone_on_resolution(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_hand_of_death_session(repository)
        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        stacked = _cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            repository,
        )
        target_gone_state = move_object(
            stacked.state,
            instance_id="bob:1",
            from_zone="battlefield",
            to_zone="graveyard",
            player_id="bob",
        )
        after_controller_pass = pass_priority(
            replace(stacked, state=target_gone_state),
            PassPriorityAction(player_id="alice"),
            repository,
        )
        result = pass_priority(
            after_controller_pass,
            PassPriorityAction(player_id="bob"),
            repository,
        )

        self.assertEqual(result.state.players["alice"].graveyard, ("alice:4",))
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1",))
        self.assertNotIn("spell_resolved", [event.event_type for event in result.event_log[-4:]])
        self.assertEqual(result.event_log[-2].event_type, "spell_countered_on_resolution")

    def test_cast_touch_of_brilliance_draws_two_cards_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_touch_of_brilliance_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        stacked = _cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_id=None,
            ),
            repository,
        )

        self.assertEqual(stacked.state.stack, ("alice:5",))
        self.assertEqual(stacked.state.turn.priority_player, "alice")
        after_controller_pass = pass_priority(
            stacked,
            PassPriorityAction(player_id="alice"),
            repository,
        )
        result = pass_priority(
            after_controller_pass,
            PassPriorityAction(player_id="bob"),
            repository,
        )

        self.assertEqual(result.state.players["alice"].hand, ("alice:6", "alice:7"))
        self.assertEqual(result.state.players["alice"].library, ("alice:8",))
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:5",))
        self.assertEqual(result.state.players["alice"].mana_pool, ())
        self.assertEqual(result.state.stack, ())
        self.assertEqual(result.state.objects["alice:5"].zone, "graveyard")
        self.assertEqual(result.state.objects["alice:5"].oracle_id, TOUCH_OF_BRILLIANCE)
        non_mana_events = [
            event.event_type
            for event in result.event_log
            if event.event_type not in {"mana_added", "priority_passed"}
        ]
        spell_cast_index = non_mana_events.index("spell_cast")
        self.assertEqual(
            non_mana_events[spell_cast_index:],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "object_moved_between_zones",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_cast_time_ebb_moves_creature_to_top_of_library_and_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_time_ebb_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(result.state.players["bob"].battlefield, ())
        self.assertEqual(result.state.players["bob"].library[0], "bob:1")
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:4",))
        self.assertEqual(result.state.objects["bob:1"].zone, "library")
        self.assertEqual(result.state.objects["alice:4"].zone, "graveyard")
        self.assertEqual(result.state.objects["alice:4"].oracle_id, TIME_EBB)
        self.assertEqual(
            [event.event_type for event in result.event_log[-5:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "object_moved_between_zones",
                "object_moved_between_zones",
            ],
        )

    def test_cast_tidal_surge_taps_selected_nonflying_creatures(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_tidal_surge_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_ids=("bob:1", "bob:2"),
            ),
            repository,
        )

        self.assertTrue(result.state.objects["bob:1"].tapped)
        self.assertTrue(result.state.objects["bob:2"].tapped)
        self.assertFalse(result.state.objects["bob:3"].tapped)
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:3",))
        self.assertEqual(result.state.objects["alice:3"].oracle_id, TIDAL_SURGE)
        self.assertEqual(
            [event.event_type for event in result.event_log[-6:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "permanent_tapped",
                "permanent_tapped",
                "object_moved_between_zones",
            ],
        )

    def test_cast_tidal_surge_allows_zero_targets(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_tidal_surge_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_ids=(),
            ),
            repository,
        )

        self.assertFalse(result.state.objects["bob:1"].tapped)
        self.assertFalse(result.state.objects["bob:2"].tapped)
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:3",))
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "object_moved_between_zones",
            ],
        )

    def test_cast_tidal_surge_rejects_flying_creature_target(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_tidal_surge_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        with self.assertRaisesRegex(ValueError, "target must be a creature without flying"):
            cast_noncreature_spell(
                session,
                CastNonCreatureSpellAction(
                    player_id="alice",
                    card_instance_id="alice:3",
                    target_instance_ids=("bob:3",),
                ),
                repository,
            )

    def test_cast_volcanic_hammer_kills_target_creature_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_volcanic_hammer_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1",))
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:3",))
        self.assertEqual(result.state.objects["bob:1"].zone, "graveyard")
        self.assertEqual(result.state.objects["alice:3"].oracle_id, VOLCANIC_HAMMER)

    def test_cast_lava_axe_reduces_target_player_life_by_five(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_lava_axe_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:6",
                target_instance_id="bob",
            ),
            repository,
        )

        self.assertEqual(result.state.players["bob"].life_total, 15)
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:6",))
        self.assertEqual(result.state.objects["alice:6"].oracle_id, LAVA_AXE)

    def test_cast_mind_rot_target_player_chooses_two_cards(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_mind_rot_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        pending = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob",
            ),
            repository,
        )

        decision = pending.state.pending_decision
        self.assertIsNotNone(decision)
        self.assertEqual(decision.chooser_id, "bob")
        self.assertEqual(decision.option_ids, ("bob:1", "bob:2", "bob:3"))
        result = resolve_pending_choice(
            pending,
            ResolveChoiceAction(
                player_id="bob",
                decision_id=decision.decision_id,
                selected_instance_ids=("bob:2", "bob:3"),
            ),
            repository,
        )

        self.assertEqual(result.state.players["bob"].hand, ("bob:1",))
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:2", "bob:3"))
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:4",))
        self.assertEqual(result.state.objects["alice:4"].oracle_id, MIND_ROT)

    def test_mind_rot_choice_is_owned_by_target_and_enumerates_exact_pairs(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_mind_rot_session(repository)
        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )
        pending = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob",
            ),
            repository,
        )
        decision = pending.state.pending_decision

        actions = enumerate_legal_actions(pending.state, repository)
        self.assertEqual(len(actions), 3)
        self.assertTrue(all(action.player_id == "bob" for action in actions))
        self.assertTrue(all(len(action.selected_instance_ids) == 2 for action in actions))
        with self.assertRaises(ValueError):
            resolve_pending_choice(
                pending,
                ResolveChoiceAction(
                    player_id="alice",
                    decision_id=decision.decision_id,
                    selected_instance_ids=("bob:1", "bob:2"),
                ),
                repository,
            )

    def test_mind_rot_requires_only_the_cards_remaining_in_a_short_hand(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_mind_rot_session(repository)
        shortened = move_object(
            session.state,
            instance_id="bob:2",
            from_zone="hand",
            to_zone="graveyard",
            player_id="bob",
        )
        shortened = move_object(
            shortened,
            instance_id="bob:3",
            from_zone="hand",
            to_zone="graveyard",
            player_id="bob",
        )
        session = replace(session, state=shortened)
        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )
        pending = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob",
            ),
            repository,
        )
        decision = pending.state.pending_decision
        self.assertEqual((decision.min_selections, decision.max_selections), (1, 1))
        result = resolve_pending_choice(
            pending,
            ResolveChoiceAction(
                player_id="bob",
                decision_id=decision.decision_id,
                selected_instance_id="bob:1",
            ),
            repository,
        )
        self.assertEqual(result.state.players["bob"].hand, ())

    def test_cast_winters_grasp_destroys_target_land_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_winters_grasp_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(result.state.players["bob"].battlefield, ())
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1",))
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:4",))
        self.assertEqual(result.state.objects["bob:1"].zone, "graveyard")
        self.assertEqual(result.state.objects["alice:4"].oracle_id, WINTERS_GRASP)

    def test_cast_symbol_of_unsummoning_returns_creature_to_hand_and_draws_a_card(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_symbol_of_unsummoning_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:4",
                target_instance_id="bob:1",
            ),
            repository,
        )

        self.assertEqual(result.state.players["bob"].battlefield, ())
        self.assertEqual(result.state.players["bob"].hand, ("bob:1",))
        self.assertEqual(result.state.players["alice"].hand, ("alice:5",))
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:4",))
        self.assertEqual(result.state.objects["alice:4"].oracle_id, SYMBOL_OF_UNSUMMONING)

    def test_cast_armageddon_destroys_all_lands_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_armageddon_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_id=None,
            ),
            repository,
        )

        self.assertEqual(result.state.players["alice"].battlefield, ())
        self.assertEqual(result.state.players["bob"].battlefield, ())
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5"))
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1", "bob:2"))
        self.assertEqual(result.state.objects["alice:5"].oracle_id, ARMAGEDDON)

    def test_cast_rain_of_salt_destroys_two_target_lands_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_rain_of_salt_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:7",
                target_instance_ids=("bob:1", "bob:2"),
            ),
            repository,
        )

        self.assertEqual(result.state.players["bob"].battlefield, ())
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1", "bob:2"))
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:7",))
        self.assertEqual(result.state.objects["alice:7"].oracle_id, RAIN_OF_SALT)

    def test_cast_sacred_nectar_gains_4_life_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_sacred_nectar_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:3",
                target_instance_ids=(),
            ),
            repository,
        )

        self.assertEqual(result.state.players["alice"].life_total, 24)
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:3",))
        self.assertEqual(result.state.objects["alice:3"].oracle_id, SACRED_NECTAR)
        self.assertEqual(
            [event.event_type for event in result.event_log[-5:]],
            [
                "spell_cast",
                "object_moved_between_zones",
                "spell_resolved",
                "life_total_changed",
                "object_moved_between_zones",
            ],
        )

    def test_cast_wrath_of_god_destroys_all_creatures_and_moves_spell_to_graveyard(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_wrath_of_god_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:5",
                target_instance_ids=(),
            ),
            repository,
        )

        self.assertEqual(result.state.players["alice"].battlefield, ("alice:1", "alice:2", "alice:3", "alice:4"))
        self.assertEqual(result.state.players["bob"].battlefield, ())
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1", "bob:2"))
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:5",))
        self.assertEqual(result.state.objects["alice:5"].oracle_id, WRATH_OF_GOD)

    def test_cast_rain_of_daggers_destroys_target_opponent_creatures_and_loses_life(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _build_rain_of_daggers_session(repository)

        for source_instance_id in session.state.players["alice"].battlefield:
            session = activate_mana_ability(
                session,
                ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
                repository,
            )

        result = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction(
                player_id="alice",
                card_instance_id="alice:7",
                target_instance_id="bob",
            ),
            repository,
        )

        self.assertEqual(result.state.players["bob"].battlefield, ())
        self.assertEqual(result.state.players["bob"].graveyard, ("bob:1", "bob:2"))
        self.assertEqual(result.state.players["alice"].life_total, 16)
        self.assertEqual(result.state.players["alice"].graveyard, ("alice:7",))
        self.assertEqual(result.state.objects["alice:7"].oracle_id, RAIN_OF_DAGGERS)


def _build_castable_main_phase_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS,),
        },
        rng_seed=17,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_foot_soldiers_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-foot-soldiers",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, FOOT_SOLDIERS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, FOOT_SOLDIERS),
            "bob": (PLAINS,),
        },
        rng_seed=19,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_muck_rats_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-muck-rats",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (SWAMP, MUCK_RATS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (SWAMP, MUCK_RATS),
            "bob": (PLAINS,),
        },
        rng_seed=23,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_armored_pegasus_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-armored-pegasus",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (PLAINS,),
        },
        rng_seed=27,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_wind_drake_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-wind-drake",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (ISLAND, ISLAND, PLAINS, WIND_DRAKE),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (ISLAND, ISLAND, PLAINS, WIND_DRAKE),
            "bob": (PLAINS,),
        },
        rng_seed=28,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_bog_imp_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-bog-imp",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (SWAMP, SWAMP, BOG_IMP),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (SWAMP, SWAMP, BOG_IMP),
            "bob": (PLAINS,),
        },
        rng_seed=29,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_storm_crow_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-storm-crow",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (ISLAND, ISLAND, STORM_CROW),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (ISLAND, ISLAND, STORM_CROW),
            "bob": (PLAINS,),
        },
        rng_seed=30,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_wall_of_granite_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-wall-of-granite",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (MOUNTAIN, MOUNTAIN, PLAINS, WALL_OF_GRANITE),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (MOUNTAIN, MOUNTAIN, PLAINS, WALL_OF_GRANITE),
            "bob": (PLAINS,),
        },
        rng_seed=31,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_vengeance_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-vengeance",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, VENGEANCE),
            "bob": (MUCK_RATS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, VENGEANCE),
            "bob": (MUCK_RATS,),
        },
        rng_seed=29,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3", "alice:4"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )

    current_state = move_object(
        current_state,
        instance_id="bob:1",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    current_state = update_object(
        current_state,
        replace(current_state.objects["bob:1"], tapped=True),
    )
    return replace(session, state=current_state)


def _build_keen_eyed_archers_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-keen-eyed-archers",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, ISLAND, KEEN_EYED_ARCHERS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, ISLAND, KEEN_EYED_ARCHERS),
            "bob": (PLAINS,),
        },
        rng_seed=45,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_anaconda_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-anaconda",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (PLAINS,),
        },
        rng_seed=46,
    )
    return start_first_turn(initialize_game(setup, repository))


def _build_path_of_peace_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-path-of-peace",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, PATH_OF_PEACE),
            "bob": (MUCK_RATS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, PATH_OF_PEACE),
            "bob": (MUCK_RATS,),
        },
        rng_seed=31,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3", "alice:4"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )

    current_state = move_object(
        current_state,
        instance_id="bob:1",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    return replace(session, state=current_state)


def _build_hand_of_death_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-hand-of-death",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (SWAMP, SWAMP, SWAMP, HAND_OF_DEATH),
            "bob": (BORDER_GUARD, MUCK_RATS),
        },
        opening_hands={
            "alice": (SWAMP, SWAMP, SWAMP, HAND_OF_DEATH),
            "bob": (BORDER_GUARD, MUCK_RATS),
        },
        rng_seed=32,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )

    for creature_id in ("bob:1", "bob:2"):
        current_state = move_object(
            current_state,
            instance_id=creature_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
    return replace(session, state=current_state)


def _build_touch_of_brilliance_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-touch-of-brilliance",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, ISLAND, TOUCH_OF_BRILLIANCE, PLAINS, PLAINS, PLAINS),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, ISLAND, TOUCH_OF_BRILLIANCE),
            "bob": (PLAINS,),
        },
        rng_seed=33,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3", "alice:4"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )

    return replace(session, state=current_state)


def _build_time_ebb_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-time-ebb",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, ISLAND, TIME_EBB),
            "bob": (MUCK_RATS, PLAINS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, ISLAND, TIME_EBB),
            "bob": (MUCK_RATS,),
        },
        rng_seed=35,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )

    current_state = move_object(
        current_state,
        instance_id="bob:1",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    return replace(session, state=current_state)


def _build_tidal_surge_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-tidal-surge",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (ISLAND, PLAINS, TIDAL_SURGE),
            "bob": (MUCK_RATS, BORDER_GUARD, STORM_CROW),
        },
        opening_hands={
            "alice": (ISLAND, PLAINS, TIDAL_SURGE),
            "bob": (MUCK_RATS, BORDER_GUARD, STORM_CROW),
        },
        rng_seed=68,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )

    for creature_id in ("bob:1", "bob:2", "bob:3"):
        current_state = move_object(
            current_state,
            instance_id=creature_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
    return replace(session, state=current_state)


def _build_volcanic_hammer_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-volcanic-hammer",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (MOUNTAIN, MOUNTAIN, VOLCANIC_HAMMER),
            "bob": (MUCK_RATS,),
        },
        opening_hands={
            "alice": (MOUNTAIN, MOUNTAIN, VOLCANIC_HAMMER),
            "bob": (MUCK_RATS,),
        },
        rng_seed=36,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    current_state = move_object(
        current_state,
        instance_id="bob:1",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    return replace(session, state=current_state)


def _build_lava_axe_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-lava-axe",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, LAVA_AXE),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, LAVA_AXE),
            "bob": (PLAINS,),
        },
        rng_seed=37,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    return replace(session, state=current_state)


def _build_mind_rot_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-mind-rot",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (SWAMP, SWAMP, SWAMP, MIND_ROT),
            "bob": (PLAINS, MUCK_RATS, BORDER_GUARD),
        },
        opening_hands={
            "alice": (SWAMP, SWAMP, SWAMP, MIND_ROT),
            "bob": (PLAINS, MUCK_RATS, BORDER_GUARD),
        },
        rng_seed=38,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    return replace(session, state=current_state)


def _build_winters_grasp_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-winters-grasp",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (FOREST, FOREST, FOREST, WINTERS_GRASP),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (FOREST, FOREST, FOREST, WINTERS_GRASP),
            "bob": (PLAINS,),
        },
        rng_seed=39,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    current_state = move_object(
        current_state,
        instance_id="bob:1",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    return replace(session, state=current_state)


def _build_symbol_of_unsummoning_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-symbol-of-unsummoning",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (ISLAND, ISLAND, ISLAND, SYMBOL_OF_UNSUMMONING, PLAINS),
            "bob": (MUCK_RATS,),
        },
        opening_hands={
            "alice": (ISLAND, ISLAND, ISLAND, SYMBOL_OF_UNSUMMONING),
            "bob": (MUCK_RATS,),
        },
        rng_seed=40,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    current_state = move_object(
        current_state,
        instance_id="bob:1",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    return replace(session, state=current_state)


def _build_armageddon_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-armageddon",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, ARMAGEDDON),
            "bob": (PLAINS, SWAMP),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, ARMAGEDDON),
            "bob": (PLAINS, SWAMP),
        },
        rng_seed=41,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3", "alice:4"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    for land_id in ("bob:1", "bob:2"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
    return replace(session, state=current_state)


def _build_rain_of_salt_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-rain-of-salt",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, RAIN_OF_SALT),
            "bob": (PLAINS, SWAMP),
        },
        opening_hands={
            "alice": (MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, MOUNTAIN, RAIN_OF_SALT),
            "bob": (PLAINS, SWAMP),
        },
        rng_seed=42,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5", "alice:6"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    for land_id in ("bob:1", "bob:2"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
    return replace(session, state=current_state)


def _build_wrath_of_god_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-wrath-of-god",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, WRATH_OF_GOD),
            "bob": (MUCK_RATS, BORDER_GUARD),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, WRATH_OF_GOD),
            "bob": (MUCK_RATS, BORDER_GUARD),
        },
        rng_seed=43,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3", "alice:4"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    current_state = move_object(
        current_state,
        instance_id="bob:1",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    current_state = move_object(
        current_state,
        instance_id="bob:2",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    return replace(session, state=current_state)


def _build_sacred_nectar_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-sacred-nectar",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, SACRED_NECTAR),
            "bob": (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, SACRED_NECTAR),
            "bob": (PLAINS,),
        },
        rng_seed=44,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    return replace(session, state=current_state)


def _build_rain_of_daggers_session(repository: CardRepository):
    setup = SetupInput(
        game_id="spell-cast-rain-of-daggers",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, RAIN_OF_DAGGERS),
            "bob": (MUCK_RATS, BORDER_GUARD),
        },
        opening_hands={
            "alice": (SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, SWAMP, RAIN_OF_DAGGERS),
            "bob": (MUCK_RATS, BORDER_GUARD),
        },
        rng_seed=42,
    )
    session = start_first_turn(initialize_game(setup, repository))
    current_state = session.state

    for land_id in ("alice:1", "alice:2", "alice:3", "alice:4", "alice:5", "alice:6"):
        current_state = move_object(
            current_state,
            instance_id=land_id,
            from_zone="hand",
            to_zone="battlefield",
            player_id="alice",
        )
    current_state = move_object(
        current_state,
        instance_id="bob:1",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    current_state = move_object(
        current_state,
        instance_id="bob:2",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    return replace(session, state=current_state)


def _cast_creature_from_normal_turns(session, repository: CardRepository, player_id: str, creature_id: str):
    current_session = _advance_to_player_main_phase(session, repository, player_id)
    player = current_session.state.players[player_id]
    land_ids = [instance_id for instance_id in player.hand if instance_id != creature_id]
    chosen_land_ids = _select_land_ids_for_spell(current_session, repository, land_ids, creature_id)

    for index, land_id in enumerate(chosen_land_ids, start=1):
        current_session = play_land(
            current_session,
            PlayLandAction(player_id=player_id, card_instance_id=land_id),
            repository,
        )
        if index != len(chosen_land_ids):
            current_session = _advance_to_player_main_phase(
                _advance_to_next_turn(current_session, repository),
                repository,
                player_id,
            )

    for source_instance_id in current_session.state.players[player_id].battlefield:
        if len(repository.get(current_session.state.objects[source_instance_id].oracle_id).produced_mana) != 1:
            continue
        current_session = activate_mana_ability(
            current_session,
            ActivateManaAbilityAction(player_id=player_id, source_instance_id=source_instance_id),
            repository,
        )

    current_session = cast_creature_spell(
        current_session,
        CastCreatureSpellAction(player_id=player_id, card_instance_id=creature_id),
        repository,
    )
    current_session = pass_priority(current_session, PassPriorityAction(player_id=player_id), repository)
    opponent_id = "bob" if player_id == "alice" else "alice"
    resolved = pass_priority(current_session, PassPriorityAction(player_id=opponent_id), repository)
    return replace(
        resolved,
        event_log=tuple(event for event in resolved.event_log if event.event_type != "priority_passed"),
    )


def _required_mana_value(repository: CardRepository, oracle_id: str) -> int:
    mana_cost = repository.get(oracle_id).mana_cost
    return sum(int(symbol) if symbol.isdigit() else 1 for symbol in mana_cost.replace("{", " ").replace("}", " ").split())


def _select_land_ids_for_spell(session, repository: CardRepository, land_ids: list[str], creature_id: str) -> list[str]:
    mana_cost = repository.get(session.state.objects[creature_id].oracle_id).mana_cost
    requirements = _mana_requirements(mana_cost)
    chosen_ids: list[str] = []
    remaining_ids = list(land_ids)

    for symbol in ("W", "U", "B", "R", "G"):
        for _ in range(requirements[symbol]):
            match_id = next(
                instance_id
                for instance_id in remaining_ids
                if repository.get(session.state.objects[instance_id].oracle_id).produced_mana == (symbol,)
            )
            chosen_ids.append(match_id)
            remaining_ids.remove(match_id)

    chosen_ids.extend(remaining_ids[: requirements["generic"]])
    return chosen_ids


def _mana_requirements(mana_cost: str) -> dict[str, int]:
    requirements = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "generic": 0}
    for symbol in mana_cost.replace("{", " ").replace("}", " ").split():
        if symbol in requirements:
            requirements[symbol] += 1
        elif symbol.isdigit():
            requirements["generic"] += int(symbol)
    return requirements


def _advance_to_next_turn(session, repository: CardRepository):
    active_player = session.state.turn.active_player
    defending_player = "bob" if active_player == "alice" else "alice"
    session = pass_priority(session, PassPriorityAction(player_id=active_player), repository)
    session = declare_attackers(
        session,
        DeclareAttackersAction(player_id=active_player, attacker_ids=()),
        repository,
    )
    session = pass_priority(session, PassPriorityAction(player_id=active_player), repository)
    session = pass_priority(session, PassPriorityAction(player_id=defending_player), repository)
    session = declare_blockers(
        session,
        DeclareBlockersAction(player_id=defending_player, blockers={}),
        repository,
    )
    session = resolve_combat_damage(session, repository)
    session = advance_to_cleanup(session)
    return start_next_turn(session)


def _advance_to_player_main_phase(session, repository: CardRepository, player_id: str):
    current_session = session
    while current_session.state.turn.active_player != player_id:
        current_session = _advance_to_next_turn(current_session, repository)
    return current_session


if __name__ == "__main__":
    unittest.main()
