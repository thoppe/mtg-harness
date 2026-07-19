"""Stateful facade for a legal, interactive game session."""

from __future__ import annotations

from dataclasses import dataclass, field

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
