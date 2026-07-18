from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardImplementation:
    oracle_id: str
    effect_key: str


# Name-scoped v0 implementations deliberately key by canonical oracle identity,
# never by mutable raw oracle-text formatting.
IMPLEMENTATIONS = {
    "1d001145-5d14-43a9-bf3b-3ce5c20b2a46": "destroy_tapped_creature",
    "b7593cf8-4dcb-473b-a2ef-180fffe66738": "destroy_creature_owner_gains_4_life",
    "dc45b2e3-272b-479b-8e3b-36eead606a3a": "destroy_nonblack_creature",
    "6365aba1-78d3-416c-89cd-9449578eedbf": "draw_two_cards",
    "30870ee5-6ad7-48a9-983e-d3b018f2344f": "gain_4_life",
    "30cc8f7b-3c28-40f5-8f8f-157e8212280b": "put_creature_on_top_of_library",
    "98fa5a06-0553-40fd-999c-bc31c9b3f4db": "damage_any_target",
    "387b6b07-a283-412d-94c3-f7f1dc76e858": "damage_target_player",
    "ad44cf74-b717-48fb-9fa2-77512024d76a": "target_player_discards_two",
    "e9b8679d-52a9-4f0f-9365-f3e4b7a69805": "destroy_target_land",
    "1219e330-01ac-405a-b75a-dd4298598167": "destroy_two_target_lands",
    "c44f1a81-269b-4f05-8ff2-e7ce19a93937": "return_creature_to_hand_and_draw_one",
    "be738992-77fe-498d-b219-e5da4ce5bf07": "tap_up_to_three_nonflying_creatures",
    "c9ed8b01-959a-47d6-891e-0abbdccf6e4f": "destroy_all_lands",
    "34515b16-c9a4-4f98-8c77-416a7a523407": "destroy_all_creatures",
    "e2048201-6dc9-4cf5-916f-1d867ae8dbdd": "destroy_all_creatures_target_opponent_you_lose_2_per_creature",
    "72cecab3-519e-4a23-9623-b423a5c5a251": "destroy_target_land",
    "6e880df6-fc00-43d2-a9c8-f575f40b78c6": "destroy_target_land",
    "9342fbb8-ab35-4895-946d-951ba6a2b067": "damage_any_target_1",
    "f637d525-2f29-488a-9269-8e5aa377fbb7": "damage_any_target_2",
    "f7571a2e-aaf3-4148-ab76-2a2e35273c70": "target_player_gains_8_life",
    "91c0a76e-3992-437f-b85a-97b0b4adbb84": "destroy_target_creature_or_land",
}


def effect_key_for(oracle_id: str) -> str | None:
    return IMPLEMENTATIONS.get(oracle_id)
