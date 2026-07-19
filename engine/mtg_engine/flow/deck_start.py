"""Legal-deck startup, deliberately separate from explicit test harness setup."""

from __future__ import annotations

from dataclasses import dataclass, replace
import random

from mtg_engine.cards.repository import CardRepository
from mtg_engine.decks.models import DeckList, DeckProfile, PORTAL_CONSTRUCTED_V0
from mtg_engine.decks.validation import validate_deck
from mtg_engine.events.log import EventLog
from mtg_engine.state.models import CardInstance, GameState, MulliganState, PlayerState, TurnState

from .setup import GameBootstrap


@dataclass(frozen=True)
class DeckGameInput:
    """Private replay input for beginning a legal two-player deck game."""

    game_id: str
    players: tuple[str, str]
    starting_player: str
    decks: dict[str, DeckList]
    rng_seed: int
    profile: DeckProfile = PORTAL_CONSTRUCTED_V0


def initialize_deck_game(input: DeckGameInput, card_repository: CardRepository) -> GameBootstrap:
    """Validate, shuffle, and draw opening hands without leaking identities.

    Unlike :class:`SetupInput`, this is a legal-game boundary.  It never
    accepts prearranged libraries or hands, and it starts in the explicit
    London-mulligan procedure rather than ``opening_hand_ready``.
    """
    _validate_input(input, card_repository)
    event_log = EventLog(game_id=input.game_id)
    event_log.append(
        event_type="game_initialized",
        active_player=input.starting_player,
        payload={
            "players": list(input.players),
            "starting_player": input.starting_player,
            "rng_seed": input.rng_seed,
            "deck_profile": input.profile.key,
            "mulligan_policy": input.profile.mulligan_policy,
        },
    )
    cursor = 0
    shuffled_decks: dict[str, tuple[str, ...]] = {}
    for player_id in input.players:
        shuffled = list(input.decks[player_id].oracle_ids)
        random.Random(input.rng_seed + cursor).shuffle(shuffled)
        event_log.append(
            event_type="library_shuffled",
            active_player=player_id,
            payload={
                "player_id": player_id,
                "algorithm": "python_random_mt19937_v1",
                "rng_cursor_before": cursor,
                "rng_cursor_after": cursor + 1,
                "count": len(shuffled),
                "reason": "opening_game_shuffle",
            },
        )
        shuffled_decks[player_id] = tuple(shuffled)
        cursor += 1

    objects: dict[str, CardInstance] = {}
    players: dict[str, PlayerState] = {}
    for player_id in input.players:
        library = shuffled_decks[player_id]
        hand_size = input.profile.opening_hand_size
        hand_ids: list[str] = []
        library_ids: list[str] = []
        for index, oracle_id in enumerate(library, start=1):
            instance_id = f"{player_id}:{index}"
            zone = "hand" if index <= hand_size else "library"
            objects[instance_id] = CardInstance(
                instance_id=instance_id,
                oracle_id=oracle_id,
                owner_id=player_id,
                controller_id=player_id,
                zone=zone,
            )
            (hand_ids if zone == "hand" else library_ids).append(instance_id)
        players[player_id] = PlayerState(
            player_id=player_id,
            life_total=input.profile.starting_life_total,
            library=tuple(library_ids), hand=tuple(hand_ids), battlefield=(),
            graveyard=(), mana_pool=(), lands_played_this_turn=0,
        )
        event_log.append(
            event_type="opening_hand_assigned",
            active_player=player_id,
            payload={"player_id": player_id, "count": hand_size, "remaining_library_size": len(library_ids)},
        )
    state = GameState(
        game_id=input.game_id, rng_seed=input.rng_seed, rng_cursor=cursor,
        players=players, objects=objects, stack=(),
        turn=TurnState(1, input.starting_player, input.players[0], "mulligan_decision"),
        mulligan=MulliganState(input.players, tuple((player_id, 0) for player_id in input.players)),
    )
    return GameBootstrap(state=state, event_log=event_log.events)


def take_london_mulligan(session: GameBootstrap, player_id: str) -> GameBootstrap:
    """Shuffle a player's current opening hand back, then draw seven anew."""
    state, mulligan = _require_mulligan_player(session, player_id)
    player = state.players[player_id]
    all_library_ids = player.hand + player.library
    shuffled = list(all_library_ids)
    cursor = state.rng_cursor
    random.Random(state.rng_seed + cursor).shuffle(shuffled)
    hand_ids = tuple(shuffled[:7])
    library_ids = tuple(shuffled[7:])
    objects = dict(state.objects)
    for instance_id in hand_ids:
        objects[instance_id] = replace(objects[instance_id], zone="hand")
    for instance_id in library_ids:
        objects[instance_id] = replace(objects[instance_id], zone="library")
    updated = replace(state, objects=objects, rng_cursor=cursor + 1)
    updated = _with_player(updated, replace(player, hand=hand_ids, library=library_ids))
    counts = tuple((pid, count + 1 if pid == player_id else count) for pid, count in mulligan.mulligan_counts)
    updated = replace(updated, mulligan=replace(mulligan, mulligan_counts=counts))
    log = EventLog.from_events(state.game_id, session.event_log)
    log.append(event_type="library_shuffled", active_player=player_id, payload={
        "player_id": player_id, "algorithm": "python_random_mt19937_v1",
        "rng_cursor_before": cursor, "rng_cursor_after": cursor + 1,
        "count": len(shuffled), "reason": "london_mulligan",
    })
    log.append(event_type="london_mulligan_taken", active_player=player_id, payload={"player_id": player_id, "mulligan_count": mulligan.count_for(player_id) + 1})
    return GameBootstrap(updated, log.events)


def keep_london_hand(session: GameBootstrap, player_id: str, bottom_instance_ids: tuple[str, ...] = ()) -> GameBootstrap:
    """Keep the current seven, placing exactly the mulligan count on bottom.

    ``bottom_instance_ids`` is ordered from the prior-bottom side toward the
    new absolute bottom.  It is intentionally absent from public events.
    """
    state, mulligan = _require_mulligan_player(session, player_id)
    required = mulligan.count_for(player_id)
    if len(bottom_instance_ids) != required or len(set(bottom_instance_ids)) != required:
        raise ValueError("London mulligan bottom selection must contain exactly the mulligan count once")
    player = state.players[player_id]
    if not set(bottom_instance_ids).issubset(player.hand):
        raise ValueError("London mulligan bottom selection must be from the player's hand")
    remaining_hand = tuple(card_id for card_id in player.hand if card_id not in bottom_instance_ids)
    library = player.library + tuple(bottom_instance_ids)
    objects = dict(state.objects)
    for instance_id in bottom_instance_ids:
        card = objects[instance_id]
        objects[instance_id] = replace(card, zone="library", zone_change_counter=card.zone_change_counter + 1)
    updated = _with_player(replace(state, objects=objects), replace(player, hand=remaining_hand, library=library))
    remaining = mulligan.remaining_player_ids[1:]
    log = EventLog.from_events(state.game_id, session.event_log)
    log.append(event_type="london_hand_kept", active_player=player_id, payload={"player_id": player_id, "mulligan_count": required, "bottom_count": required})
    if remaining:
        updated = replace(updated, mulligan=replace(mulligan, remaining_player_ids=remaining), turn=replace(updated.turn, priority_player=remaining[0]))
    else:
        updated = replace(updated, mulligan=None, turn=replace(updated.turn, priority_player=updated.turn.active_player, step="opening_hand_ready"))
        log.append(event_type="opening_hands_ready", active_player=updated.turn.active_player, payload={"players": list(state.players)})
    return GameBootstrap(updated, log.events)


def _require_mulligan_player(session: GameBootstrap, player_id: str) -> tuple[GameState, MulliganState]:
    state = session.state
    mulligan = state.mulligan
    if state.turn.step != "mulligan_decision" or mulligan is None:
        raise ValueError("London mulligan procedure is not active")
    if not mulligan.remaining_player_ids or mulligan.remaining_player_ids[0] != player_id:
        raise ValueError("player is not the current London mulligan chooser")
    return state, mulligan


def _with_player(state: GameState, player: PlayerState) -> GameState:
    players = dict(state.players)
    players[player.player_id] = player
    return replace(state, players=players)


def _validate_input(input: DeckGameInput, card_repository: CardRepository) -> None:
    if len(input.players) != 2 or len(set(input.players)) != 2:
        raise ValueError("deck game requires exactly two distinct players")
    if input.starting_player not in input.players:
        raise ValueError("starting_player must be one of the deck-game players")
    if set(input.decks) != set(input.players):
        raise ValueError("deck game must supply exactly one deck for each player")
    if input.profile.mulligan_policy != "london":
        raise ValueError("legal deck game startup requires the London mulligan profile")
    for player_id in input.players:
        validate_deck(input.decks[player_id], input.profile, card_repository)
