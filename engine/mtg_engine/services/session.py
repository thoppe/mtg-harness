"""Stateful facade for a legal, interactive game session."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Mapping

from mtg_engine.actions.dispatch import AcceptedAction, dispatch_action
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.deck_start import (
    DeckGameInput,
    initialize_deck_game,
    keep_london_hand,
    take_london_mulligan,
)
from mtg_engine.flow.priority import enumerate_legal_actions
from mtg_engine.flow.setup import GameBootstrap, SetupInput, initialize_game
from mtg_engine.flow.turns import TurnResult, start_first_turn
from mtg_engine.replay.reducer import ReplayInput
from mtg_engine.services.legal_actions_api import (
    LegalActionApiError,
    LegalActionsResponse,
    ValidTargetsResponse,
    action_for_descriptor,
    build_legal_actions_response,
    state_revision,
    valid_targets_response,
)


@dataclass(frozen=True)
class SessionRejection:
    """A non-mutating, API-safe reason a descriptor request was refused."""

    code: str
    state_revision: str

    def to_payload(self) -> dict[str, object]:
        return {"accepted": False, "code": self.code, "state_revision": self.state_revision}


@dataclass(frozen=True)
class DescriptorSubmission:
    """The structured result of submitting a revision-bound descriptor."""

    accepted: bool
    state_revision: str
    rejection: SessionRejection | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {"accepted": self.accepted, "state_revision": self.state_revision}
        if self.rejection is not None:
            payload["rejection"] = self.rejection.to_payload()
        return payload


def api_payload(value: object) -> object:
    """Convert public API models to JSON-safe primitives without repr leaks."""
    if is_dataclass(value):
        return api_payload(asdict(value))
    if isinstance(value, dict):
        return {str(key): api_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [api_payload(item) for item in value]
    if isinstance(value, list):
        return [api_payload(item) for item in value]
    return value


@dataclass
class GameSession:
    """An action-recording facade over the deterministic rules reducer.

    This takes an explicit setup so the legal deck builder can be layered above
    it and rule-harness tests remain able to construct exact game states.
    """

    setup: SetupInput
    card_repository: CardRepository
    result: TurnResult
    accepted_actions: list[AcceptedAction] = field(default_factory=list)

    @classmethod
    def from_setup(cls, setup: SetupInput, card_repository: CardRepository) -> "GameSession":
        return cls(setup, card_repository, start_first_turn(initialize_game(setup, card_repository)))

    @property
    def state(self):
        return self.result.state

    def legal_actions(self) -> tuple[AcceptedAction, ...]:
        return tuple(enumerate_legal_actions(self.state, self.card_repository))  # type: ignore[return-value]

    @property
    def revision(self) -> str:
        """Opaque revision clients must echo when submitting descriptors."""
        return state_revision(self.state)

    def legal_actions_api(self, player_id: str) -> LegalActionsResponse | SessionRejection:
        """Return only ``player_id``'s descriptors, never another player's actions."""
        try:
            return build_legal_actions_response(
                self.state, self.card_repository, player_id, revision=self.revision
            )
        except LegalActionApiError as error:
            return SessionRejection(error.code, self.revision)

    def valid_targets_api(
        self,
        player_id: str,
        action_id: str,
        slot: str,
        partial_selection: Mapping[str, object] | None = None,
    ) -> ValidTargetsResponse | SessionRejection:
        """Project remaining candidates from the authoritative legal action list."""
        try:
            return valid_targets_response(
                self.state,
                self.card_repository,
                player_id,
                action_id,
                slot,
                partial_selection,
                revision=self.revision,
            )
        except LegalActionApiError as error:
            return SessionRejection(error.code, self.revision)

    def submit_descriptor(
        self,
        player_id: str,
        action_id: str,
        parameters: Mapping[str, object] | None,
        revision: str,
    ) -> DescriptorSubmission:
        """Resolve and dispatch one current descriptor without exposing reducer errors.

        Rejected submissions are entirely read-only.  In particular, a stale
        client cannot consume randomness or alter the action log.
        """
        if revision != self.revision:
            return DescriptorSubmission(False, self.revision, SessionRejection("stale_revision", self.revision))
        try:
            action = action_for_descriptor(
                self.state, self.card_repository, player_id, action_id, parameters
            )
        except LegalActionApiError as error:
            return DescriptorSubmission(False, self.revision, SessionRejection(error.code, self.revision))
        try:
            self.submit(action)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            # This should be unreachable because descriptor conversion returns
            # an enumerated action, but it preserves a safe API boundary.
            return DescriptorSubmission(False, self.revision, SessionRejection("no_longer_legal", self.revision))
        return DescriptorSubmission(True, self.revision)

    def submit(self, action: AcceptedAction) -> TurnResult:
        if self.state.outcome.status == "completed":
            raise ValueError("cannot submit an action after the game has completed")
        if action not in self.legal_actions():
            raise ValueError("action is not currently enumerated as legal")
        self.result = dispatch_action(self.result, action, self.card_repository)
        self.accepted_actions.append(action)
        return self.result

    def replay_input(self) -> ReplayInput:
        return ReplayInput(setup=self.setup, actions=tuple(self.accepted_actions))


@dataclass
class DeckGameSession:
    """Pregame facade for a legal deck game and its London-mulligan choices.

    Once both players keep, ``start`` produces the normal action-recording
    session from the resulting private opening snapshot.  The rules harness
    remains separate: it never receives deck validation or mulligan behavior.
    """

    input: DeckGameInput
    card_repository: CardRepository
    bootstrap: GameBootstrap

    @classmethod
    def from_decks(
        cls, input: DeckGameInput, card_repository: CardRepository
    ) -> "DeckGameSession":
        return cls(input, card_repository, initialize_deck_game(input, card_repository))

    @property
    def state(self):
        return self.bootstrap.state

    def take_mulligan(self, player_id: str) -> None:
        self.bootstrap = take_london_mulligan(self.bootstrap, player_id)

    def keep_hand(self, player_id: str, bottom_instance_ids: tuple[str, ...] = ()) -> None:
        self.bootstrap = keep_london_hand(
            self.bootstrap, player_id, bottom_instance_ids
        )

    def start(self) -> GameSession:
        """Begin ordinary play after both players have kept legal hands."""
        if self.state.mulligan is not None:
            raise ValueError("both players must keep London hands before play begins")
        libraries: dict[str, tuple[str, ...]] = {}
        opening_hands: dict[str, tuple[str, ...]] = {}
        for player_id, player in self.state.players.items():
            opening_hands[player_id] = tuple(
                self.state.objects[instance_id].oracle_id for instance_id in player.hand
            )
            libraries[player_id] = opening_hands[player_id] + tuple(
                self.state.objects[instance_id].oracle_id for instance_id in player.library
            )
        snapshot = SetupInput(
            game_id=self.input.game_id,
            players=self.input.players,
            starting_player=self.input.starting_player,
            libraries=libraries,
            opening_hands=opening_hands,
            rng_seed=self.input.rng_seed,
            starting_life_total=self.input.profile.starting_life_total,
        )
        return GameSession.from_setup(snapshot, self.card_repository)
