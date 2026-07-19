from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.repository import CardRepository
from mtg_engine.cli import run_cli
from mtg_engine.flow.midgame_scenarios import create_midgame_session
from mtg_engine.services import (
    DescriptorSubmission,
    GameSession,
    LegalActionDescriptor,
    LegalActionsResponse,
    SessionRejection,
)
from mtg_engine.state.models import TurnState


INFORMATION_DIR = Path(__file__).resolve().parents[2] / "information"


class _LivenessGuard:
    """Fail quickly if a terminal auto-chain revisits state instead of prompting.

    The real session still owns every legal-action and submission decision.  This
    wrapper merely makes an accidental unbounded CLI loop a deterministic test
    failure rather than a hung test run.
    """

    def __init__(self, session: GameSession, *, action_query_limit: int = 4) -> None:
        self._session = session
        self._action_query_limit = action_query_limit
        self.action_revisions: list[str] = []
        self.submission_revisions: list[tuple[str, str]] = []

    @property
    def state(self):
        return self._session.state

    @property
    def card_repository(self):
        return self._session.card_repository

    def legal_actions_api(self, player_id: str):
        if len(self.action_revisions) >= self._action_query_limit:
            raise AssertionError("terminal auto-progression exceeded its liveness bound")
        response = self._session.legal_actions_api(player_id)
        if not isinstance(response, SessionRejection):
            self.action_revisions.append(response.state_revision)
        return response

    def valid_targets_api(self, player_id: str, action_id: str, slot: str, partial_selection=None):
        return self._session.valid_targets_api(player_id, action_id, slot, partial_selection)

    def submit_descriptor(self, player_id: str, action_id: str, parameters: dict[str, object], revision: str):
        before = self._session.revision
        submission = self._session.submit_descriptor(player_id, action_id, parameters, revision)
        if submission.accepted:
            self.submission_revisions.append((before, self._session.revision))
        return submission


class _RejectedForcedProgressionSession:
    """Descriptor-only session whose forced action is rejected without mutation."""

    def __init__(self) -> None:
        self.state = SimpleNamespace(
            outcome=SimpleNamespace(status="in_progress"),
            turn=SimpleNamespace(priority_player="alice"),
        )
        self.submissions = 0
        self.action_queries = 0
        self._action = LegalActionDescriptor(
            action_id="AdvanceTurnAction:forced",
            kind="AdvanceTurnAction",
            player_id="alice",
            source=None,
            parameters=(),
        )

    def legal_actions_api(self, player_id: str) -> LegalActionsResponse:
        self.action_queries += 1
        if self.action_queries > 3:
            raise AssertionError("rejected automatic action was retried without reaching a prompt")
        return LegalActionsResponse(
            schema_version="v0",
            game_id="rejected-forced-progression",
            state_revision="unchanged-revision",
            player_id=player_id,
            actions=(self._action,),
        )

    def submit_descriptor(
        self, player_id: str, action_id: str, parameters: dict[str, object], revision: str
    ) -> DescriptorSubmission:
        self.submissions += 1
        return DescriptorSubmission(
            False,
            "unchanged-revision",
            SessionRejection("forced_action_rejected", "unchanged-revision"),
        )


class TerminalLivenessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CardRepository.from_information_directory(INFORMATION_DIR)

    def test_cleanup_expiry_auto_chain_is_bounded_and_reaches_a_live_prompt(self) -> None:
        """A forced cleanup transition must not spin through future turns unseen."""
        session = _LivenessGuard(create_midgame_session(self.repository, "cleanup-expiry"))
        lines: list[str] = []
        prompts: list[str] = []

        def quit_at_first_live_choice(prompt: str) -> str:
            prompts.append(prompt)
            return "q"

        run_cli(session, input_fn=quit_at_first_live_choice, output=lines.append)  # type: ignore[arg-type]

        self.assertEqual(prompts, ["Choose action number (q to quit): "])
        self.assertEqual(len(session.submission_revisions), 1)
        self.assertEqual(len(session.action_revisions), 2)
        self.assertEqual(len(set(session.action_revisions)), len(session.action_revisions))
        self.assertTrue(all(before != after for before, after in session.submission_revisions))
        self.assertEqual((session.state.turn.turn_number, session.state.turn.active_player), (6, "bob"))
        self.assertEqual(session.state.outcome.status, "in_progress")
        self.assertIn("Auto-advancing: resolve combat damage and begin the next turn.", lines)

    def test_lone_optional_attacker_reaches_an_explicit_prompt_without_auto_retry(self) -> None:
        """One available attacker is not a unique declaration: no attacks remains legal."""
        real_session = create_midgame_session(self.repository, "cleanup-expiry")
        real_session.result = replace(
            real_session.result,
            state=replace(
                real_session.state,
                combat=None,
                turn=TurnState(5, "alice", "alice", "declare_attackers_step"),
            ),
        )
        session = _LivenessGuard(real_session)
        lines: list[str] = []
        prompts: list[str] = []

        run_cli(
            session,  # type: ignore[arg-type]
            input_fn=lambda prompt: prompts.append(prompt) or "q",
            output=lines.append,
        )

        self.assertEqual(prompts, ["Choose action number (q to quit): "])
        self.assertEqual(session.submission_revisions, [])
        self.assertEqual(session.state.turn.step, "declare_attackers_step")
        self.assertIsNone(session.state.combat)
        self.assertNotIn("Auto-selecting", "\n".join(lines))

    def test_rejected_automatic_action_is_not_retried_without_a_player_prompt(self) -> None:
        """A non-mutating rejection must disable that auto attempt for its revision."""
        session = _RejectedForcedProgressionSession()
        lines: list[str] = []
        prompts: list[str] = []

        with patch("mtg_engine.cli._print_public_state"):
            run_cli(
                session,  # type: ignore[arg-type]
                input_fn=lambda prompt: prompts.append(prompt) or "q",
                output=lines.append,
            )

        self.assertEqual(session.submissions, 1)
        self.assertEqual(prompts, ["Choose action number (q to quit): "])
        self.assertIn(
            "Automatic action rejected: forced_action_rejected; choose a legal action explicitly.",
            lines,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
