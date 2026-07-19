from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.midgame_scenarios import (
    create_midgame_session,
    list_midgame_scenarios,
)
from mtg_engine.services import SessionRejection


INFO = Path(__file__).resolve().parents[2] / "information"


class MidgameScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFO)

    def _actions(self, name: str, player_id: str):
        result = create_midgame_session(self.repository, name).legal_actions_api(player_id)
        self.assertNotIsInstance(result, SessionRejection)
        assert not isinstance(result, SessionRejection)
        return result

    def test_catalog_is_stable_and_rain_is_explicitly_rules_harness_only(self) -> None:
        scenarios = list_midgame_scenarios()
        self.assertEqual(
            [scenario.name for scenario in scenarios],
            [
                "combat-attackers",
                "combat-blockers",
                "combat-lethal",
                "forked-lightning-targets",
                "mystic-denial-response",
                "private-choice",
                "cleanup-expiry",
                "rain-of-daggers-harness",
            ],
        )
        rain = next(scenario for scenario in scenarios if scenario.name == "rain-of-daggers-harness")
        self.assertTrue(rain.rules_harness_only)
        self.assertTrue(all(
            not scenario.rules_harness_only
            for scenario in scenarios if scenario.name != rain.name
        ))
        self.assertEqual({scenario.category for scenario in scenarios}, {"rules_harness"})

    def test_combat_scenarios_are_scoped_to_the_player_with_the_decision(self) -> None:
        attackers_session = create_midgame_session(self.repository, "combat-attackers")
        attackers = self._actions("combat-attackers", "alice")
        attack = next(action for action in attackers.actions if action.kind == "DeclareAttackersAction")
        candidates = attackers_session.valid_targets_api(
            "alice", attack.action_id, "attacker_ids",
        )
        self.assertNotIsInstance(candidates, SessionRejection)
        assert not isinstance(candidates, SessionRejection)
        self.assertEqual({candidate.value for candidate in candidates.candidates}, {"alice:1", "alice:2"})
        self.assertEqual(self._actions("combat-attackers", "bob").actions, ())

        blockers = self._actions("combat-blockers", "bob")
        block = next(action for action in blockers.actions if action.kind == "DeclareBlockersAction")
        self.assertEqual(block.player_id, "bob")
        self.assertEqual(self._actions("combat-blockers", "alice").actions, ())

    def test_combat_lethal_offers_an_unblocked_lethal_attacker(self) -> None:
        session = create_midgame_session(self.repository, "combat-lethal")
        actions = self._actions("combat-lethal", "alice")
        attack = next(action for action in actions.actions if action.kind == "DeclareAttackersAction")
        candidates = session.valid_targets_api("alice", attack.action_id, "attacker_ids")
        self.assertNotIsInstance(candidates, SessionRejection)
        assert not isinstance(candidates, SessionRejection)
        self.assertEqual([candidate.label for candidate in candidates.candidates], ["Charging Rhino (4/4)"])
        self.assertEqual(session.state.players["bob"].life_total, 4)

    def test_forked_lightning_exposes_only_current_creature_targets_and_allocations(self) -> None:
        session = create_midgame_session(self.repository, "forked-lightning-targets")
        actions = self._actions("forked-lightning-targets", "alice")
        spell = next(action for action in actions.actions if action.kind == "CastNonCreatureSpellAction")
        slots = {slot.name: slot for slot in spell.parameters}
        self.assertEqual((slots["target_instance_ids"].minimum, slots["target_instance_ids"].maximum), (1, 2))
        self.assertEqual((slots["damage_assignments"].minimum, slots["damage_assignments"].maximum), (1, 2))

        targets = session.valid_targets_api("alice", spell.action_id, "target_instance_ids")
        self.assertNotIsInstance(targets, SessionRejection)
        assert not isinstance(targets, SessionRejection)
        self.assertEqual({candidate.value for candidate in targets.candidates}, {"bob:1", "bob:2"})
        remaining = session.valid_targets_api(
            "alice", spell.action_id, "target_instance_ids", {"target_instance_ids": ["bob:1"]},
        )
        self.assertNotIsInstance(remaining, SessionRejection)
        assert not isinstance(remaining, SessionRejection)
        self.assertEqual([candidate.value for candidate in remaining.candidates], ["bob:2"])

    def test_mystic_denial_response_targets_only_the_visible_stack_spell(self) -> None:
        session = create_midgame_session(self.repository, "mystic-denial-response")
        actions = self._actions("mystic-denial-response", "bob")
        denial = next(action for action in actions.actions if action.kind == "CastNonCreatureSpellAction")
        self.assertEqual(denial.source.label if denial.source else None, "Mystic Denial")
        targets = session.valid_targets_api("bob", denial.action_id, "target_instance_ids")
        self.assertNotIsInstance(targets, SessionRejection)
        assert not isinstance(targets, SessionRejection)
        self.assertEqual([candidate.value for candidate in targets.candidates], ["alice:1"])
        self.assertEqual(self._actions("mystic-denial-response", "alice").actions, ())

    def test_private_choice_never_grants_bob_a_descriptor_or_target_query(self) -> None:
        session = create_midgame_session(self.repository, "private-choice")
        alice = self._actions("private-choice", "alice")
        choice = next(action for action in alice.actions if action.kind == "ResolveChoiceAction")
        candidates = session.valid_targets_api("alice", choice.action_id, "selected_instance_ids")
        self.assertNotIsInstance(candidates, SessionRejection)
        assert not isinstance(candidates, SessionRejection)
        self.assertEqual({candidate.value for candidate in candidates.candidates}, {"alice:2", "alice:3"})
        self.assertEqual(self._actions("private-choice", "bob").actions, ())
        rejected = session.valid_targets_api("bob", choice.action_id, "selected_instance_ids")
        self.assertIsInstance(rejected, SessionRejection)
        self.assertEqual(rejected.code, "unknown_descriptor")  # type: ignore[union-attr]

    def test_rain_of_daggers_is_available_only_through_its_named_harness_state(self) -> None:
        actions = self._actions("rain-of-daggers-harness", "alice")
        rain = next(action for action in actions.actions if action.kind == "CastNonCreatureSpellAction")
        self.assertEqual(rain.source.label if rain.source else None, "Rain of Daggers")

    def test_cleanup_expiry_starts_at_a_live_turn_advance_and_clears_turn_effects(self) -> None:
        session = create_midgame_session(self.repository, "cleanup-expiry")
        actions = self._actions("cleanup-expiry", "alice")
        advance = next(action for action in actions.actions if action.kind == "AdvanceTurnAction")
        submitted = session.submit_descriptor("alice", advance.action_id, {}, actions.state_revision)
        self.assertTrue(submitted.accepted)
        self.assertEqual(session.state.turn.turn_number, 6)
        self.assertEqual(session.state.temporary_effects, ())
        self.assertEqual(session.state.delayed_turn_effects, ())

    def test_blocker_choice_resolves_combat_into_a_live_next_turn(self) -> None:
        session = create_midgame_session(self.repository, "combat-blockers")
        blockers = self._actions("combat-blockers", "bob")
        declaration = next(action for action in blockers.actions if action.kind == "DeclareBlockersAction")
        submitted = session.submit_descriptor(
            "bob", declaration.action_id,
            {"blockers": (("alice:1", ("bob:1",)),)},
            blockers.state_revision,
        )

        self.assertTrue(submitted.accepted)
        self.assertEqual(session.state.turn.priority_player, "alice")
        continuation = session.legal_actions_api("alice")
        self.assertNotIsInstance(continuation, SessionRejection)
        assert not isinstance(continuation, SessionRejection)
        advance = next(action for action in continuation.actions if action.kind == "AdvanceTurnAction")
        advanced = session.submit_descriptor("alice", advance.action_id, {}, continuation.state_revision)
        self.assertTrue(advanced.accepted)
        self.assertEqual(session.state.outcome.status, "in_progress")
        self.assertEqual((session.state.turn.turn_number, session.state.turn.active_player), (6, "bob"))
        next_actions = session.legal_actions_api("bob")
        self.assertNotIsInstance(next_actions, SessionRejection)
        assert not isinstance(next_actions, SessionRejection)
        self.assertTrue(next_actions.actions)

    def test_unknown_scenario_is_a_launcher_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown mid-game scenario"):
            create_midgame_session(self.repository, "not-a-scenario")
