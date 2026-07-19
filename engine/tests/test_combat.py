from __future__ import annotations

from dataclasses import replace
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
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
from mtg_engine.flow.priority import enumerate_legal_actions
from mtg_engine.flow.turns import (
    activate_mana_ability,
    advance_turn,
    advance_to_cleanup,
    advance_to_begin_combat,
    cast_creature_spell,
    cast_noncreature_spell,
    declare_attackers,
    declare_blockers,
    pass_priority,
    play_land,
    resolve_combat_damage,
    resolve_pending_choice,
    start_first_turn,
    start_next_turn,
)
from mtg_engine.state.zones import move_object
from mtg_engine.state.models import GameOutcome


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
FOREST = "b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"
MOUNTAIN = "a3fb7228-e76b-4e96-a40e-20b5fed75685"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
FOOT_SOLDIERS = "a768ba13-4d1c-4dce-a4a6-86a39c069c3f"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
ARMORED_PEGASUS = "f097a059-5505-4c3c-b879-7853ab6972ed"
WIND_DRAKE = "d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca"
KEEN_EYED_ARCHERS = "0ace32d6-7261-447c-9ee2-e03febaab91b"
ANACONDA = "3eff03f1-2c5f-4c59-b465-a8c4cd05e1ba"
WALL_OF_GRANITE = "8445094f-008b-491a-977c-e8582d5ab72c"
DEEP_WOOD = "3f01f627-9fbd-470b-8001-974784ccf421"
HARSH_JUSTICE = "fe4bee2c-f03f-44a4-94a4-55a06bcd0ad8"
FALSE_PEACE = "7962db58-dbd9-4b94-8a21-a1625da4c384"
TAUNT = "24cf7fad-233b-49fd-b2a1-a29e3e30041c"


class CombatTests(unittest.TestCase):
    def test_pending_multi_block_order_is_a_barrier_to_damage_and_turn_handoff(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_multiple_blockers_ready(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(session, DeclareAttackersAction("alice", ("alice:4",)), repository)
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction("bob", {"alice:4": ("bob:4", "bob:6")}),
            repository,
        )
        before = session

        with self.assertRaisesRegex(ValueError, "pending decision"):
            resolve_combat_damage(session, repository)
        with self.assertRaisesRegex(ValueError, "end_combat_step"):
            advance_to_cleanup(session)

        self.assertEqual(session, before)
        self.assertEqual(session.state.turn.step, "combat_damage_step")
        self.assertEqual(session.state.pending_decision.kind, "combat_damage_order")

    def test_attacked_player_mana_and_instant_reset_priority_before_blockers(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _attacked_player_instant_fixture(repository, DEEP_WOOD, (FOREST, FOREST))
        session = advance_to_begin_combat(session)
        session = declare_attackers(session, DeclareAttackersAction("alice", ("alice:1",)), repository)
        session = pass_priority(session, PassPriorityAction("alice"), repository)
        self.assertEqual(session.state.turn.priority_player, "bob")

        session = activate_mana_ability(session, ActivateManaAbilityAction("bob", "bob:2"), repository)
        session = activate_mana_ability(session, ActivateManaAbilityAction("bob", "bob:3"), repository)
        self.assertEqual(session.state.consecutive_passes, 0)
        session = cast_noncreature_spell(session, CastNonCreatureSpellAction("bob", "bob:1"), repository)
        self.assertEqual(session.state.turn.priority_player, "bob")
        self.assertEqual(session.state.consecutive_passes, 0)

        session = pass_priority(session, PassPriorityAction("bob"), repository)
        self.assertEqual(session.state.turn.priority_player, "alice")
        session = pass_priority(session, PassPriorityAction("alice"), repository)
        self.assertEqual(session.state.turn.priority_player, "alice")
        self.assertEqual(session.state.turn.step, "declare_attackers_step")
        self.assertTrue(any(effect.kind == "prevent_attacking_damage" for effect in session.state.delayed_turn_effects))
        session = _pass_attackers_window(session, repository)
        self.assertEqual(session.state.turn.step, "declare_blockers_step")

    def test_deep_wood_prevents_harsh_justice_retaliation_and_both_expire_at_cleanup(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _attacked_player_instant_fixture(repository, DEEP_WOOD, (FOREST, FOREST, PLAINS, PLAINS, PLAINS))
        session = advance_to_begin_combat(session)
        session = declare_attackers(session, DeclareAttackersAction("alice", ("alice:1",)), repository)
        session = pass_priority(session, PassPriorityAction("alice"), repository)
        for source_id in ("bob:2", "bob:3"):
            session = activate_mana_ability(session, ActivateManaAbilityAction("bob", source_id), repository)
        session = cast_noncreature_spell(session, CastNonCreatureSpellAction("bob", "bob:1"), repository)
        session = pass_priority(session, PassPriorityAction("bob"), repository)
        session = pass_priority(session, PassPriorityAction("alice"), repository)
        session = pass_priority(session, PassPriorityAction("alice"), repository)
        for source_id in ("bob:4", "bob:5", "bob:6"):
            session = activate_mana_ability(session, ActivateManaAbilityAction("bob", source_id), repository)
        session = cast_noncreature_spell(session, CastNonCreatureSpellAction("bob", "bob:7"), repository)
        session = pass_priority(session, PassPriorityAction("bob"), repository)
        session = pass_priority(session, PassPriorityAction("alice"), repository)
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(session, DeclareBlockersAction("bob", {}), repository)
        session = resolve_combat_damage(session, repository)

        self.assertEqual(session.state.players["bob"].life_total, 20)
        self.assertEqual(session.state.players["alice"].life_total, 20)
        self.assertFalse(session.state.stack_entries)
        self.assertIn("damage_prevented", [event.event_type for event in session.event_log])
        self.assertNotIn("triggered_ability_put_on_stack", [event.event_type for event in session.event_log[-4:]])
        session = advance_to_cleanup(session)
        self.assertFalse(session.state.delayed_turn_effects)

    def test_taunt_marker_expires_when_false_peace_skips_its_target_turn_combat(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _taunt_false_peace_fixture(repository)
        for source_id in ("alice:3", "alice:4"):
            session = activate_mana_ability(session, ActivateManaAbilityAction("alice", source_id), repository)
        session = cast_noncreature_spell(session, CastNonCreatureSpellAction("alice", "alice:1", target_instance_id="bob"), repository)
        session = _resolve_stack(session, repository)
        session = cast_noncreature_spell(session, CastNonCreatureSpellAction("alice", "alice:2", target_instance_id="bob"), repository)
        session = _resolve_stack(session, repository)
        self.assertEqual({effect.kind for effect in session.state.delayed_turn_effects}, {"skip_combat", "must_attack_source"})

        session = _finish_turn_without_attackers(session, repository)
        self.assertEqual(session.state.turn.active_player, "bob")
        skipped = advance_to_begin_combat(session)
        self.assertEqual(skipped.state.turn.step, "end_combat_step")
        self.assertFalse(any(effect.kind == "skip_combat" for effect in skipped.state.delayed_turn_effects))
        finished = advance_to_cleanup(skipped)
        self.assertFalse(finished.state.delayed_turn_effects)

        session = start_next_turn(finished)
        self.assertEqual(session.state.turn.active_player, "alice")
        session = advance_to_begin_combat(session)
        declare_attackers(session, DeclareAttackersAction("alice", ()), repository)

    def test_false_peace_skipped_combat_exposes_and_accepts_turn_handoff(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _taunt_false_peace_fixture(repository)
        for source_id in ("alice:3", "alice:4"):
            session = activate_mana_ability(session, ActivateManaAbilityAction("alice", source_id), repository)
        session = cast_noncreature_spell(
            session,
            CastNonCreatureSpellAction("alice", "alice:1", target_instance_id="bob"),
            repository,
        )
        session = _resolve_stack(session, repository)
        session = _finish_turn_without_attackers(session, repository)

        skipped = advance_to_begin_combat(session)
        self.assertEqual(skipped.state.turn.step, "end_combat_step")
        self.assertEqual(
            enumerate_legal_actions(skipped.state, repository),
            (AdvanceTurnAction("bob"),),
        )

        continued = advance_turn(skipped, AdvanceTurnAction("bob"), repository)
        self.assertEqual(continued.state.turn.active_player, "alice")
        self.assertEqual(continued.state.turn.step, "precombat_main_step")
        self.assertEqual(continued.state.outcome.status, "in_progress")
    def test_life_zero_state_based_action_ends_game(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_creatures_ready_to_fight(repository, include_blocker=False)
        low_life_state = replace(
            session.state,
            outcome=GameOutcome(),
            players={
                **session.state.players,
                "bob": replace(session.state.players["bob"], life_total=1),
            },
        )
        session = replace(session, state=low_life_state)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.outcome.status, "completed")
        self.assertEqual(result.state.outcome.winner_id, "alice")
        self.assertEqual(result.state.outcome.loser_ids, ("bob",))
        self.assertEqual(result.state.outcome.reason, "life_total_zero_or_less")
        self.assertIn("game_ended", [event.event_type for event in result.event_log])

    def test_unblocked_border_guard_deals_life_damage(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_creatures_ready_to_fight(repository, include_blocker=False)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 19)
        self.assertEqual(result.state.turn.step, "end_combat_step")
        self.assertEqual(result.event_log[-4].event_type, "combat_damage_applied")
        self.assertEqual(result.event_log[-3].event_type, "life_total_changed")
        self.assertEqual(result.event_log[-2].event_type, "state_based_actions_checked")

    def test_foot_soldiers_attacks_after_normal_cast_and_deals_printed_power(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_foot_soldiers_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:5",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.objects["alice:5"].oracle_id, FOOT_SOLDIERS)
        self.assertEqual(result.state.players["bob"].life_total, 18)
        attackers_event = next(
            event
            for event in reversed(result.event_log)
            if event.event_type == "attackers_declared"
        )
        self.assertEqual(attackers_event.payload["attacker_ids"], ["alice:5"])
        self.assertEqual(
            [event.event_type for event in result.event_log[-6:]],
            [
                "blockers_declared",
                "step_changed",
                "combat_damage_applied",
                "life_total_changed",
                "state_based_actions_checked",
                "step_changed",
            ],
        )

    def test_blocked_combat_records_assignment_and_keeps_creatures_alive(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_creatures_ready_to_fight(repository, include_blocker=True)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:4",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:4"].zone, "battlefield")
        self.assertEqual(
            [event.event_type for event in result.event_log[-6:]],
            [
                "blockers_declared",
                "step_changed",
                "combat_damage_assigned",
                "combat_damage_applied",
                "state_based_actions_checked",
                "step_changed",
            ],
        )

    def test_multiple_blockers_on_one_attacker_are_supported(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_multiple_blockers_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:4", "bob:6")}),
            repository,
        )
        decision = session.state.pending_decision
        self.assertEqual(decision.chooser_id, "alice")
        self.assertEqual(decision.kind, "combat_damage_order")
        session = resolve_pending_choice(
            session,
            ResolveChoiceAction(
                player_id="alice",
                decision_id=decision.decision_id,
                ordered_instance_ids=("bob:6", "bob:4"),
            ),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.objects["alice:4"].damage_marked, 2)
        self.assertEqual(result.state.objects["bob:4"].damage_marked, 0)
        self.assertEqual(result.state.objects["bob:6"].zone, "graveyard")
        self.assertEqual(result.state.turn.step, "end_combat_step")
        combat_assignment = next(
            event for event in result.event_log if event.event_type == "combat_damage_assigned"
        )
        self.assertEqual(
            combat_assignment.payload["assignments"],
            [
                {"blocker_id": "bob:6", "attacker_damage": 1, "blocker_damage": 1},
                {"blocker_id": "bob:4", "attacker_damage": 0, "blocker_damage": 1},
            ],
        )

    def test_multiple_blockers_receive_lethal_damage_in_declared_order(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_anaconda_blockable(repository)
        state_with_second_blocker = move_object(
            session.state,
            instance_id="bob:3",
            from_zone="hand",
            to_zone="battlefield",
            player_id="bob",
        )
        muck_rat_blockers = {
            **state_with_second_blocker.objects,
            "bob:2": replace(state_with_second_blocker.objects["bob:2"], oracle_id=MUCK_RATS),
            "bob:3": replace(state_with_second_blocker.objects["bob:3"], oracle_id=MUCK_RATS),
        }
        session = replace(session, state=replace(state_with_second_blocker, objects=muck_rat_blockers))
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:5",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:5": ("bob:2", "bob:3")}),
            repository,
        )
        decision = session.state.pending_decision
        session = resolve_pending_choice(
            session,
            ResolveChoiceAction(
                player_id="alice",
                decision_id=decision.decision_id,
                ordered_instance_ids=("bob:2", "bob:3"),
            ),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        combat_assignment = next(
            event for event in result.event_log if event.event_type == "combat_damage_assigned"
        )
        self.assertEqual(
            combat_assignment.payload["assignments"],
            [
                {"blocker_id": "bob:2", "attacker_damage": 1, "blocker_damage": 1},
                {"blocker_id": "bob:3", "attacker_damage": 1, "blocker_damage": 1},
            ],
        )

    def test_damage_order_choice_enumerates_attacker_owned_permutations(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_multiple_blockers_ready(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction("alice", ("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction("bob", {"alice:4": ("bob:4", "bob:6")}),
            repository,
        )

        decision = session.state.pending_decision
        actions = enumerate_legal_actions(session.state, repository)
        self.assertEqual(
            {action.ordered_instance_ids for action in actions},
            {("bob:4", "bob:6"), ("bob:6", "bob:4")},
        )
        self.assertTrue(all(action.player_id == "alice" for action in actions))
        with self.assertRaises(ValueError):
            resolve_pending_choice(
                session,
                ResolveChoiceAction(
                    "bob",
                    decision.decision_id,
                    ordered_instance_ids=("bob:4", "bob:6"),
                ),
                repository,
            )

    def test_damage_order_choice_rejects_stale_blocker_identity(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_multiple_blockers_ready(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction("alice", ("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction("bob", {"alice:4": ("bob:4", "bob:6")}),
            repository,
        )
        decision = session.state.pending_decision
        stale_state = move_object(
            session.state,
            instance_id="bob:4",
            from_zone="battlefield",
            to_zone="graveyard",
            player_id="bob",
        )

        with self.assertRaisesRegex(ValueError, "expected battlefield object"):
            resolve_pending_choice(
                replace(session, state=stale_state),
                ResolveChoiceAction(
                    "alice",
                    decision.decision_id,
                    ordered_instance_ids=("bob:4", "bob:6"),
                ),
                repository,
            )

    def test_damage_order_choice_events_redact_order_until_assignment(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_multiple_blockers_ready(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction("alice", ("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction("bob", {"alice:4": ("bob:4", "bob:6")}),
            repository,
        )
        requested = session.event_log[-1]
        decision = session.state.pending_decision
        self.assertEqual(requested.event_type, "choice_requested")
        self.assertEqual(requested.payload["option_count"], 2)
        self.assertNotIn("option_ids", requested.payload)

        session = resolve_pending_choice(
            session,
            ResolveChoiceAction(
                "alice",
                decision.decision_id,
                ordered_instance_ids=("bob:6", "bob:4"),
            ),
            repository,
        )
        resolved = session.event_log[-1]
        self.assertEqual(resolved.event_type, "choice_resolved")
        self.assertEqual(resolved.payload["ordered_count"], 2)
        self.assertNotIn("ordered_instance_ids", resolved.payload)

    def test_multiple_damage_order_choices_queue_in_declared_attacker_order(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_two_multiply_blocked_attackers(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction("alice", ("alice:1", "alice:2")),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(
                "bob",
                {
                    "alice:1": ("bob:1", "bob:2"),
                    "alice:2": ("bob:3", "bob:4"),
                },
            ),
            repository,
        )

        first = session.state.pending_decision
        self.assertEqual(first.source_object_id, session.state.objects["alice:1"].object_id)
        self.assertEqual(first.option_ids, ("bob:1", "bob:2"))
        with self.assertRaisesRegex(ValueError, "pending decision"):
            resolve_combat_damage(session, repository)
        self.assertEqual(
            {action.ordered_instance_ids for action in enumerate_legal_actions(session.state, repository)},
            {("bob:1", "bob:2"), ("bob:2", "bob:1")},
        )

        session = resolve_pending_choice(
            session,
            ResolveChoiceAction(
                "alice",
                first.decision_id,
                ordered_instance_ids=("bob:2", "bob:1"),
            ),
            repository,
        )
        second = session.state.pending_decision
        self.assertEqual(second.source_object_id, session.state.objects["alice:2"].object_id)
        self.assertEqual(second.option_ids, ("bob:3", "bob:4"))
        self.assertEqual(
            [event.event_type for event in session.event_log[-3:]],
            ["choice_requested", "choice_resolved", "choice_requested"],
        )

        session = resolve_pending_choice(
            session,
            ResolveChoiceAction(
                "alice",
                second.decision_id,
                ordered_instance_ids=("bob:4", "bob:3"),
            ),
            repository,
        )
        self.assertIsNone(session.state.pending_decision)
        result = resolve_combat_damage(session, repository)
        assignments = [
            event.payload["assignments"]
            for event in result.event_log
            if event.event_type == "combat_damage_assigned"
        ]
        self.assertEqual(
            [[assignment["blocker_id"] for assignment in group] for group in assignments],
            [["bob:2", "bob:1"], ["bob:4", "bob:3"]],
        )

    def test_state_based_actions_destroy_muck_rats_after_lethal_combat_damage(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_muck_rats_blocker_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:2",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.objects["bob:2"].zone, "graveyard")
        self.assertIn("bob:2", result.state.players["bob"].graveyard)
        self.assertEqual(result.event_log[-4].event_type, "state_based_actions_checked")
        self.assertEqual(result.event_log[-3].event_type, "permanent_destroyed")
        self.assertEqual(result.event_log[-2].event_type, "object_moved_between_zones")

    def test_armored_pegasus_cannot_be_blocked_by_nonflying_creature(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_armored_pegasus_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:3",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)

        with self.assertRaises(ValueError):
            declare_blockers(
                session,
                DeclareBlockersAction(player_id="bob", blockers={"alice:3": ("bob:2",)}),
                repository,
            )

        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 19)
        self.assertEqual(result.state.objects["alice:3"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].zone, "battlefield")

    def test_wind_drake_cannot_be_blocked_by_nonflying_creature(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_wind_drake_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)

        with self.assertRaises(ValueError):
            declare_blockers(
                session,
                DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:2",)}),
                repository,
            )

        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 18)
        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].zone, "battlefield")

    def test_keen_eyed_archers_can_block_armored_pegasus(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_reach_block_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:3",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:3": ("bob:4",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 20)
        self.assertEqual(result.state.objects["alice:3"].zone, "graveyard")
        self.assertEqual(result.state.objects["bob:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:4"].damage_marked, 1)

    def test_anaconda_cannot_be_blocked_when_defending_player_controls_swamp(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_anaconda_swampwalk_locked(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:5",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 17)
        self.assertEqual(result.state.objects["alice:5"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].zone, "battlefield")

    def test_anaconda_can_be_blocked_when_defending_player_lacks_swamp(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_anaconda_blockable(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:5",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:5": ("bob:2",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 20)
        self.assertEqual(result.state.objects["alice:5"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:2"].damage_marked, 3)

    def test_wall_of_granite_cannot_attack(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_wall_of_granite_ready(repository)

        session = advance_to_begin_combat(session)

        with self.assertRaises(ValueError):
            declare_attackers(
                session,
                DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
                repository,
            )

    def test_wall_of_granite_can_block_and_survive_combat(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_wall_of_granite_block_ready(repository)

        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = _pass_attackers_window(session, repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:4",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        self.assertEqual(result.state.players["bob"].life_total, 20)
        self.assertEqual(result.state.objects["alice:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:4"].zone, "battlefield")
        self.assertEqual(result.state.objects["bob:4"].damage_marked, 1)
        self.assertEqual(
            [event.event_type for event in result.event_log[-4:]],
            [
                "combat_damage_assigned",
                "combat_damage_applied",
                "state_based_actions_checked",
                "step_changed",
            ],
        )


def _state_with_creatures_ready_to_fight(repository: CardRepository, *, include_blocker: bool):
    setup = SetupInput(
        game_id="combat-001",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD) if include_blocker else (PLAINS,),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD) if include_blocker else (PLAINS,),
        },
        rng_seed=23,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    if include_blocker:
        session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
        session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _attacked_player_instant_fixture(repository: CardRepository, first_instant: str, lands: tuple[str, ...]):
    """Put a long-established attacker and an attacked-player instant in play."""
    setup = SetupInput(
        game_id="combat-attacked-player-instant",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={"alice": (BORDER_GUARD,), "bob": (first_instant,) + lands + ((HARSH_JUSTICE,) if len(lands) > 2 else ())},
        opening_hands={"alice": (BORDER_GUARD,), "bob": (first_instant,) + lands + ((HARSH_JUSTICE,) if len(lands) > 2 else ())},
        rng_seed=67,
    )
    session = start_first_turn(initialize_game(setup, repository))
    state = move_object(session.state, instance_id="alice:1", from_zone="hand", to_zone="battlefield", player_id="alice")
    for index in range(len(lands)):
        state = move_object(state, instance_id=f"bob:{index + 2}", from_zone="hand", to_zone="battlefield", player_id="bob")
    state = replace(state, objects={**state.objects, "alice:1": replace(state.objects["alice:1"], entered_battlefield_turn=0)})
    return replace(session, state=state)


def _taunt_false_peace_fixture(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-taunt-false-peace",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={"alice": (FALSE_PEACE, TAUNT, PLAINS, ISLAND, PLAINS), "bob": (PLAINS,)},
        opening_hands={"alice": (FALSE_PEACE, TAUNT, PLAINS, ISLAND), "bob": ()},
        rng_seed=71,
    )
    session = start_first_turn(initialize_game(setup, repository))
    state = move_object(session.state, instance_id="alice:3", from_zone="hand", to_zone="battlefield", player_id="alice")
    state = move_object(state, instance_id="alice:4", from_zone="hand", to_zone="battlefield", player_id="alice")
    return replace(session, state=state)


def _resolve_stack(session, repository: CardRepository):
    controller = session.state.turn.priority_player
    session = pass_priority(session, PassPriorityAction(controller), repository)
    return pass_priority(session, PassPriorityAction(session.state.turn.priority_player), repository)


def _finish_turn_without_attackers(session, repository: CardRepository):
    """Advance a precombat-main turn through a declared-empty combat."""
    active = session.state.turn.active_player
    defender = "bob" if active == "alice" else "alice"
    session = advance_to_begin_combat(session)
    session = declare_attackers(session, DeclareAttackersAction(active, ()), repository)
    session = _pass_attackers_window(session, repository)
    session = declare_blockers(session, DeclareBlockersAction(defender, {}), repository)
    session = resolve_combat_damage(session, repository)
    return start_next_turn(advance_to_cleanup(session))


def _state_with_foot_soldiers_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-foot-soldiers",
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
        rng_seed=59,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(
        session,
        repository,
        "alice",
        "alice:5",
    )
    return _advance_to_player_main_phase(
        _advance_to_next_turn(session, repository),
        repository,
        "alice",
    )


def _state_with_multiple_blockers_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-multi-block",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD, SWAMP, MUCK_RATS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (PLAINS, PLAINS, PLAINS, BORDER_GUARD, SWAMP, MUCK_RATS),
        },
        rng_seed=41,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:6")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_two_multiply_blocked_attackers(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-two-multi-blocks",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (BORDER_GUARD, BORDER_GUARD),
            "bob": (MUCK_RATS, MUCK_RATS, MUCK_RATS, MUCK_RATS),
        },
        opening_hands={
            "alice": (BORDER_GUARD, BORDER_GUARD),
            "bob": (MUCK_RATS, MUCK_RATS, MUCK_RATS, MUCK_RATS),
        },
        rng_seed=53,
    )
    session = start_first_turn(initialize_game(setup, repository))
    state = session.state
    for player_id, instance_ids in (
        ("alice", ("alice:1", "alice:2")),
        ("bob", ("bob:1", "bob:2", "bob:3", "bob:4")),
    ):
        for instance_id in instance_ids:
            state = move_object(
                state,
                instance_id=instance_id,
                from_zone="hand",
                to_zone="battlefield",
                player_id=player_id,
            )
    objects = {
        **state.objects,
        **{
            instance_id: replace(state.objects[instance_id], entered_battlefield_turn=0)
            for instance_id in ("alice:1", "alice:2", "bob:1", "bob:2", "bob:3", "bob:4")
        },
    }
    return replace(session, state=replace(state, objects=objects))


def _state_with_muck_rats_blocker_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-lethal-muck-rats",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (SWAMP, MUCK_RATS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (SWAMP, MUCK_RATS),
        },
        rng_seed=43,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:2")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_armored_pegasus_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-armored-pegasus",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (SWAMP, MUCK_RATS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (SWAMP, MUCK_RATS),
        },
        rng_seed=47,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:3")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:2")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_wind_drake_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-wind-drake",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (ISLAND, ISLAND, PLAINS, WIND_DRAKE),
            "bob": (SWAMP, MUCK_RATS),
        },
        opening_hands={
            "alice": (ISLAND, ISLAND, PLAINS, WIND_DRAKE),
            "bob": (SWAMP, MUCK_RATS),
        },
        rng_seed=48,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:2")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_reach_block_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-reach-block",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (PLAINS, PLAINS, ISLAND, KEEN_EYED_ARCHERS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, ARMORED_PEGASUS),
            "bob": (PLAINS, PLAINS, ISLAND, KEEN_EYED_ARCHERS),
        },
        rng_seed=52,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:3")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_anaconda_swampwalk_locked(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-anaconda-swampwalk-locked",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (SWAMP, BORDER_GUARD),
        },
        opening_hands={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (SWAMP, BORDER_GUARD),
        },
        rng_seed=53,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:5")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = play_land(session, PlayLandAction(player_id="bob", card_instance_id="bob:1"), repository)
    session = _advance_to_next_turn(session, repository)
    current_state = move_object(
        session.state,
        instance_id="bob:2",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    session = replace(session, state=current_state)
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_anaconda_blockable(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-anaconda-swampwalk-open",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (PLAINS, BORDER_GUARD, BORDER_GUARD),
        },
        opening_hands={
            "alice": (FOREST, PLAINS, PLAINS, PLAINS, ANACONDA),
            "bob": (PLAINS, BORDER_GUARD, BORDER_GUARD),
        },
        rng_seed=54,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:5")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = play_land(session, PlayLandAction(player_id="bob", card_instance_id="bob:1"), repository)
    session = _advance_to_next_turn(session, repository)
    current_state = move_object(
        session.state,
        instance_id="bob:2",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    session = replace(session, state=current_state)
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_wall_of_granite_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-wall-of-granite-attack",
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
        rng_seed=49,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _state_with_wall_of_granite_block_ready(repository: CardRepository):
    setup = SetupInput(
        game_id="combat-wall-of-granite-block",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (MOUNTAIN, MOUNTAIN, PLAINS, WALL_OF_GRANITE),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, BORDER_GUARD),
            "bob": (MOUNTAIN, MOUNTAIN, PLAINS, WALL_OF_GRANITE),
        },
        rng_seed=50,
    )
    session = start_first_turn(initialize_game(setup, repository))
    session = _develop_creature_through_normal_turns(session, repository, "alice", "alice:4")
    session = _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "bob")
    session = _develop_creature_through_normal_turns(session, repository, "bob", "bob:4")
    return _advance_to_player_main_phase(_advance_to_next_turn(session, repository), repository, "alice")


def _develop_creature_through_normal_turns(session, repository: CardRepository, player_id: str, creature_id: str):
    current_session = _advance_to_player_main_phase(session, repository, player_id)
    land_ids = [instance_id for instance_id in current_session.state.players[player_id].hand if instance_id != creature_id]
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
    return pass_priority(current_session, PassPriorityAction(player_id=opponent_id), repository)


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


def _pass_attackers_window(session, repository: CardRepository):
    active = session.state.turn.active_player
    defender = "bob" if active == "alice" else "alice"
    session = pass_priority(session, PassPriorityAction(player_id=active), repository)
    return pass_priority(session, PassPriorityAction(player_id=defender), repository)


def _advance_to_player_main_phase(session, repository: CardRepository, player_id: str):
    current_session = session
    while current_session.state.turn.active_player != player_id:
        current_session = _advance_to_next_turn(current_session, repository)
    return current_session


if __name__ == "__main__":
    unittest.main()
