from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cli import run_cli
from mtg_engine.services import (
    DescriptorSubmission,
    LegalActionDescriptor,
    LegalActionsResponse,
    ParameterSlot,
    SessionRejection,
    TargetCandidate,
    ValidTargetsResponse,
)


@dataclass
class _DescriptorSession:
    """Small black-box session double for the descriptor terminal boundary."""

    descriptors: tuple[LegalActionDescriptor, ...]
    candidates_by_slot: dict[str, tuple[TargetCandidate, ...]]
    reject_first_submission: bool = False

    def __post_init__(self) -> None:
        self.state = SimpleNamespace(
            outcome=SimpleNamespace(status="running"),
            turn=SimpleNamespace(priority_player="alice"),
        )
        self.revision = "revision-1"
        self.legal_action_calls: list[str] = []
        self.target_calls: list[tuple[str, str, dict[str, object]]] = []
        self.submissions: list[tuple[str, str, dict[str, object], str]] = []

    def legal_actions_api(self, player_id: str) -> LegalActionsResponse:
        self.legal_action_calls.append(player_id)
        return LegalActionsResponse(
            schema_version="v0",
            game_id="descriptor-cli",
            state_revision=self.revision,
            player_id=player_id,
            actions=self.descriptors,
        )

    def valid_targets_api(
        self, player_id: str, action_id: str, slot: str, partial_selection: dict[str, object]
    ) -> ValidTargetsResponse | SessionRejection:
        self.target_calls.append((action_id, slot, dict(partial_selection)))
        descriptor = next(item for item in self.descriptors if item.action_id == action_id)
        parameter = next(item for item in descriptor.parameters if item.name == slot)
        candidates = self.candidates_by_slot[slot]
        # A multi-target prompt must not offer an already selected target.
        selected = partial_selection.get(slot, ())
        if isinstance(selected, (tuple, list)):
            candidates = tuple(item for item in candidates if item.value not in selected)
        return ValidTargetsResponse(
            schema_version="v0",
            game_id="descriptor-cli",
            state_revision=self.revision,
            player_id=player_id,
            action_id=action_id,
            slot=parameter,
            candidates=candidates,
        )

    def submit_descriptor(
        self, player_id: str, action_id: str, parameters: dict[str, object], revision: str
    ) -> DescriptorSubmission:
        self.submissions.append((player_id, action_id, dict(parameters), revision))
        if self.reject_first_submission and len(self.submissions) == 1:
            self.revision = "revision-2"
            return DescriptorSubmission(False, self.revision, SessionRejection("stale_revision", self.revision))
        self.state.outcome.status = "completed"
        return DescriptorSubmission(True, self.revision)


def _response_descriptor(*parameters: ParameterSlot) -> LegalActionDescriptor:
    return LegalActionDescriptor(
        action_id="CastNonCreatureSpellAction:opaque",
        kind="CastNonCreatureSpellAction",
        player_id="alice",
        source=None,
        parameters=parameters,
    )


class DescriptorCliFlowTests(unittest.TestCase):
    def _run(self, session: _DescriptorSession, answers: tuple[str, ...]) -> list[str]:
        lines: list[str] = []
        iterator = iter(answers)
        # State rendering is separately covered by the legacy CLI tests. These
        # tests intentionally exercise only descriptor interaction and never
        # require a real game state's private zones.
        with patch("mtg_engine.cli._print_public_state"):
            run_cli(session, input_fn=lambda _prompt: next(iterator), output=lines.append)
        return lines

    def test_multi_target_prompt_submits_only_candidates_and_requeries_after_each_pick(self) -> None:
        slot = ParameterSlot("target_instance_ids", "targets", minimum=0, maximum=2, distinct=True)
        public_a = TargetCandidate("player:alice", "alice", "targets", "alice")
        public_b = TargetCandidate("player:bob", "bob", "targets", "bob")
        session = _DescriptorSession((_response_descriptor(slot),), {slot.name: (public_a, public_b)})

        # Select descriptor 1, target 2 then target 1, and finish the optional
        # selection. The terminal receives no way to type an arbitrary object ID.
        lines = self._run(session, ("1", "2", "1", "d"))

        self.assertEqual(
            session.submissions,
            [("alice", "CastNonCreatureSpellAction:opaque", {slot.name: ("bob", "alice")}, "revision-1")],
        )
        self.assertEqual(
            session.target_calls,
            [
                ("CastNonCreatureSpellAction:opaque", slot.name, {slot.name: ()}),
                ("CastNonCreatureSpellAction:opaque", slot.name, {slot.name: ("bob",)}),
            ],
        )
        rendered = "\n".join(lines)
        self.assertIn("bob", rendered)
        self.assertNotIn("player:bob", rendered)

    def test_rejected_descriptor_refreshes_actions_and_reuses_no_stale_submission(self) -> None:
        session = _DescriptorSession((_response_descriptor(),), {}, reject_first_submission=True)

        lines = self._run(session, ("1", "1"))

        self.assertEqual(len(session.legal_action_calls), 2)
        self.assertEqual([item[3] for item in session.submissions], ["revision-1", "revision-2"])
        self.assertIn("Action rejected: stale_revision; refreshing actions.", lines)

    def test_private_candidate_identity_is_never_rendered(self) -> None:
        slot = ParameterSlot("selected_instance_ids", "choice", minimum=0, maximum=1, distinct=True)
        private = TargetCandidate("opaque-choice", "alice:secret-library-card", "choice", "private card")
        session = _DescriptorSession((_response_descriptor(slot),), {slot.name: (private,)})

        lines = self._run(session, ("1", "1", "d"))

        rendered = "\n".join(lines)
        self.assertIn("private card", rendered)
        self.assertNotIn("alice:secret-library-card", rendered)
        self.assertNotIn("opaque-choice", rendered)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
