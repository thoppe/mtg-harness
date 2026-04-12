from __future__ import annotations

from dataclasses import dataclass

from mtg_engine.cards.repository import CardRepository
from mtg_engine.events.log import EventLog
from mtg_engine.state.models import CardInstance, GameState, PlayerState, TurnState

ALLOWED_MULLIGAN_POLICIES = {"v0_no_mulligan"}


@dataclass(frozen=True)
class SetupInput:
    game_id: str
    players: tuple[str, str]
    starting_player: str
    libraries: dict[str, tuple[str, ...]]
    opening_hands: dict[str, tuple[str, ...]]
    rng_seed: int
    starting_life_total: int = 20
    mulligan_policy: str = "v0_no_mulligan"


@dataclass(frozen=True)
class GameBootstrap:
    state: GameState
    event_log: tuple


def initialize_game(setup: SetupInput, card_repository: CardRepository) -> GameBootstrap:
    _validate_setup(setup, card_repository)

    objects: dict[str, CardInstance] = {}
    players: dict[str, PlayerState] = {}
    event_log = EventLog(game_id=setup.game_id)

    event_log.append(
        event_type="game_initialized",
        active_player=setup.starting_player,
        payload={
            "players": list(setup.players),
            "starting_player": setup.starting_player,
            "rng_seed": setup.rng_seed,
            "mulligan_policy": setup.mulligan_policy,
        },
    )

    for player_id in setup.players:
        opening_hand = setup.opening_hands[player_id]
        library = setup.libraries[player_id]
        remaining_library = library[len(opening_hand) :]

        hand_instance_ids = []
        library_instance_ids = []

        for index, oracle_id in enumerate(library, start=1):
            instance_id = f"{player_id}:{index}"
            zone = "hand" if index <= len(opening_hand) else "library"
            objects[instance_id] = CardInstance(
                instance_id=instance_id,
                oracle_id=oracle_id,
                owner_id=player_id,
                controller_id=player_id,
                zone=zone,
            )
            if zone == "hand":
                hand_instance_ids.append(instance_id)
            else:
                library_instance_ids.append(instance_id)

        players[player_id] = PlayerState(
            player_id=player_id,
            life_total=setup.starting_life_total,
            library=tuple(library_instance_ids),
            hand=tuple(hand_instance_ids),
            battlefield=(),
            graveyard=(),
            mana_pool=(),
            lands_played_this_turn=0,
        )

        event_log.append(
            event_type="opening_hand_assigned",
            active_player=player_id,
            payload={
                "player_id": player_id,
                "opening_hand": list(opening_hand),
                "remaining_library_size": len(remaining_library),
            },
        )

    state = GameState(
        game_id=setup.game_id,
        rng_seed=setup.rng_seed,
        players=players,
        objects=objects,
        stack=(),
        turn=TurnState(
            turn_number=1,
            active_player=setup.starting_player,
            priority_player=setup.starting_player,
            step="opening_hand_ready",
        ),
    )
    return GameBootstrap(state=state, event_log=event_log.events)


def _validate_setup(setup: SetupInput, card_repository: CardRepository) -> None:
    if len(setup.players) != 2:
        raise ValueError("setup requires exactly two players")
    if len(set(setup.players)) != 2:
        raise ValueError("player identifiers must be distinct")
    if setup.starting_player not in setup.players:
        raise ValueError("starting_player must be one of the setup players")
    if setup.mulligan_policy not in ALLOWED_MULLIGAN_POLICIES:
        raise ValueError(f"unsupported mulligan policy: {setup.mulligan_policy}")

    for player_id in setup.players:
        if player_id not in setup.libraries:
            raise ValueError(f"missing library for player {player_id}")
        if player_id not in setup.opening_hands:
            raise ValueError(f"missing opening hand for player {player_id}")

        library = setup.libraries[player_id]
        opening_hand = setup.opening_hands[player_id]
        if library[: len(opening_hand)] != opening_hand:
            raise ValueError(f"opening hand must match the top of library for player {player_id}")

    all_cards = [oracle_id for player_id in setup.players for oracle_id in setup.libraries[player_id]]
    if not all_cards:
        raise ValueError("setup must include at least one card")
    if not set(all_cards).issubset(card_repository.allowed_oracle_ids):
        raise ValueError(
            f"setup must use only card identities from the active support slice {card_repository.support_slice_key}"
        )

    for oracle_id in all_cards:
        if not card_repository.has(oracle_id):
            raise ValueError(f"unknown card oracle_id in setup: {oracle_id}")
