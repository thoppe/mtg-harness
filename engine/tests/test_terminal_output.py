from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console

from mtg_engine.actions.models import DeclareAttackersAction, DeclareBlockersAction, PassPriorityAction
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.turns import advance_to_begin_combat, declare_attackers, declare_blockers, pass_priority, resolve_combat_damage
from mtg_engine.output.terminal import print_game_snapshot, print_recent_events

from test_combat import INFORMATION_DIR, _state_with_muck_rats_blocker_ready


class TerminalOutputTests(unittest.TestCase):
    def test_game_snapshot_includes_key_cards(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_muck_rats_blocker_ready(repository)

        output = io.StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        print_game_snapshot(console, session.state, repository, title="Before Combat")

        rendered = output.getvalue()
        self.assertIn("Before Combat", rendered)
        self.assertIn("Border Guard", rendered)
        self.assertIn("Muck Rats", rendered)
        self.assertIn("precombat_main_step", rendered)

    def test_recent_events_reports_lethal_damage_flow(self) -> None:
        repository = CardRepository.from_information_directory(INFORMATION_DIR)
        session = _state_with_muck_rats_blocker_ready(repository)
        session = advance_to_begin_combat(session)
        session = declare_attackers(
            session,
            DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
            repository,
        )
        session = pass_priority(session, PassPriorityAction(player_id="alice"), repository)
        session = pass_priority(session, PassPriorityAction(player_id="bob"), repository)
        session = declare_blockers(
            session,
            DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:2",)}),
            repository,
        )
        result = resolve_combat_damage(session, repository)

        output = io.StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        print_recent_events(console, result.event_log[-6:], repository, title="Combat Result", state=result.state)

        rendered = output.getvalue()
        self.assertIn("Combat Result", rendered)
        self.assertIn("state_based_actions_checked", rendered)
        self.assertIn("permanent_destroyed", rendered)
        self.assertIn("graveyard", rendered)
        self.assertIn("Muck Rats", rendered)
        self.assertIn("lethal damage", rendered)
