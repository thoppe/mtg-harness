import sys
from pathlib import Path
from dataclasses import replace

from rich.console import Console


REPO_ROOT = Path(__file__).resolve().parent
ENGINE_DIR = REPO_ROOT / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from mtg_engine.actions.models import (
    ActivateManaAbilityAction,
    CastCreatureSpellAction,
    CastNonCreatureSpellAction,
    DeclareAttackersAction,
    DeclareBlockersAction,
    PlayLandAction,
)
from mtg_engine.cards.repository import CardRepository
from mtg_engine.flow.setup import SetupInput, initialize_game
from mtg_engine.flow.turns import (
    activate_mana_ability,
    advance_to_begin_combat,
    advance_to_cleanup,
    cast_creature_spell,
    cast_noncreature_spell,
    declare_attackers,
    declare_blockers,
    play_land,
    resolve_combat_damage,
    start_first_turn,
    start_next_turn,
)
from mtg_engine.output import print_action_plan, print_game_snapshot, print_recent_events
from mtg_engine.state.zones import move_object, update_object


INFORMATION_DIR = REPO_ROOT / "information"
SWAMP = "56719f6a-1a6c-4c0a-8d21-18f7d7350b68"
PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
BORDER_GUARD = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
MUCK_RATS = "bca13a12-6723-4a5e-8f1b-21646a8b3e7e"
VENGEANCE = "1d001145-5d14-43a9-bf3b-3ce5c20b2a46"


def build_lethal_damage_demo_state(repository):
    setup = SetupInput(
        game_id="demo-lethal-damage",
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
        rng_seed=99,
    )

    session = start_first_turn(initialize_game(setup, repository))
    session = develop_creature(session, repository, player_id="alice", creature_id="alice:4")
    session = advance_to_player_main_phase(
        finish_turn_and_start_next(session, repository),
        repository,
        player_id="bob",
    )
    session = develop_creature(session, repository, player_id="bob", creature_id="bob:2")
    return advance_to_player_main_phase(
        finish_turn_and_start_next(session, repository),
        repository,
        player_id="alice",
    )


def run_lethal_damage_sequence(session, repository):
    session = advance_to_begin_combat(session)
    session = declare_attackers(
        session,
        DeclareAttackersAction(player_id="alice", attacker_ids=("alice:4",)),
        repository,
    )
    session = declare_blockers(
        session,
        DeclareBlockersAction(player_id="bob", blockers={"alice:4": ("bob:2",)}),
        repository,
    )
    return resolve_combat_damage(session, repository)


def build_vengeance_demo_state(repository):
    setup = SetupInput(
        game_id="demo-vengeance",
        players=("alice", "bob"),
        starting_player="alice",
        libraries={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, VENGEANCE),
            "bob": (SWAMP, MUCK_RATS),
        },
        opening_hands={
            "alice": (PLAINS, PLAINS, PLAINS, PLAINS, VENGEANCE),
            "bob": (SWAMP, MUCK_RATS),
        },
        rng_seed=101,
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
        instance_id="bob:2",
        from_zone="hand",
        to_zone="battlefield",
        player_id="bob",
    )
    current_state = update_object(
        current_state,
        replace(current_state.objects["bob:2"], tapped=True),
    )
    return replace(session, state=current_state)


def run_vengeance_sequence(session, repository):
    for source_instance_id in session.state.players["alice"].battlefield:
        current_card = session.state.objects[source_instance_id]
        if not repository.get(current_card.oracle_id).is_land:
            continue
        session = activate_mana_ability(
            session,
            ActivateManaAbilityAction(player_id="alice", source_instance_id=source_instance_id),
            repository,
        )

    return cast_noncreature_spell(
        session,
        CastNonCreatureSpellAction(
            player_id="alice",
            card_instance_id="alice:5",
            target_instance_id="bob:2",
        ),
        repository,
    )


def develop_creature(
    session,
    repository,
    *,
    player_id,
    creature_id,
):
    current_session = advance_to_player_main_phase(session, repository, player_id=player_id)
    land_ids = [instance_id for instance_id in current_session.state.players[player_id].hand if instance_id != creature_id]

    for index, land_id in enumerate(land_ids, start=1):
        current_session = play_land(
            current_session,
            PlayLandAction(player_id=player_id, card_instance_id=land_id),
            repository,
        )
        if index != len(land_ids):
            current_session = advance_to_player_main_phase(
                finish_turn_and_start_next(current_session, repository),
                repository,
                player_id=player_id,
            )

    for source_instance_id in current_session.state.players[player_id].battlefield:
        current_session = activate_mana_ability(
            current_session,
            ActivateManaAbilityAction(player_id=player_id, source_instance_id=source_instance_id),
            repository,
        )

    return cast_creature_spell(
        current_session,
        CastCreatureSpellAction(player_id=player_id, card_instance_id=creature_id),
        repository,
    )


def advance_to_player_main_phase(
    session,
    repository,
    *,
    player_id,
):
    current_session = session
    while current_session.state.turn.active_player != player_id or current_session.state.turn.step != "precombat_main_step":
        if current_session.state.turn.step == "precombat_main_step":
            current_session = finish_turn_and_start_next(current_session, repository)
            continue
        if current_session.state.turn.step == "end_combat_step":
            current_session = advance_to_cleanup(current_session)
            continue
        if current_session.state.turn.step == "cleanup_step":
            current_session = start_next_turn(current_session)
            continue
        raise ValueError(f"cannot advance from unsupported step {current_session.state.turn.step}")
    return current_session


def finish_turn_and_start_next(session, repository):
    current_session = session
    if current_session.state.turn.step == "precombat_main_step":
        current_session = advance_to_begin_combat(current_session)
    if current_session.state.turn.step == "declare_attackers_step":
        current_session = declare_attackers(
            current_session,
            DeclareAttackersAction(
                player_id=current_session.state.turn.active_player,
                attacker_ids=(),
            ),
            repository,
        )
    if current_session.state.turn.step == "declare_blockers_step":
        defending_player = current_session.state.turn.priority_player
        current_session = declare_blockers(
            current_session,
            DeclareBlockersAction(player_id=defending_player, blockers={}),
            repository,
        )
    if current_session.state.turn.step == "combat_damage_step":
        current_session = resolve_combat_damage(current_session, repository)
    if current_session.state.turn.step == "end_combat_step":
        current_session = advance_to_cleanup(current_session)
    if current_session.state.turn.step != "cleanup_step":
        raise ValueError(f"cannot finish turn from step {current_session.state.turn.step}")
    return start_next_turn(current_session)


console = Console()
repository = CardRepository.from_information_directory(INFORMATION_DIR)

before_combat = build_lethal_damage_demo_state(repository)
print_game_snapshot(console, before_combat.state, repository, title="Board State Before Combat")
print_action_plan(
    console,
    "Combat Script",
    [
        "Alice advances to combat.",
        "Alice attacks with Border Guard.",
        "Bob blocks with Muck Rats.",
        "Combat damage resolves and state-based actions are checked.",
    ],
)

after_combat = run_lethal_damage_sequence(before_combat, repository)
print_game_snapshot(console, after_combat.state, repository, title="Board State After Combat")
print_recent_events(console, after_combat.event_log[-8:], repository, title="Recent Events", state=after_combat.state)

before_vengeance = build_vengeance_demo_state(repository)
print_game_snapshot(console, before_vengeance.state, repository, title="Board State Before Vengeance")
print_action_plan(
    console,
    "Vengeance Script",
    [
        "Scenario setup places four Plains under Alice and a tapped Muck Rats under Bob.",
        "Alice taps four Plains for mana.",
        "Alice casts Vengeance targeting the tapped Muck Rats.",
    ],
)

after_vengeance = run_vengeance_sequence(before_vengeance, repository)
print_game_snapshot(console, after_vengeance.state, repository, title="Board State After Vengeance")
print_recent_events(console, after_vengeance.event_log[-8:], repository, title="Recent Events", state=after_vengeance.state)
