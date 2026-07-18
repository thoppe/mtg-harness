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
    "cbc9c731-181a-4f00-a7b0-eb7e56eac2ea": "return_target_creature_card_from_your_graveyard",
    "8a922366-ee2a-4ddb-a904-683dcf4f191a": "return_target_card_from_your_graveyard",
    "7416c8db-ec33-4d92-866c-b7fdc69c8b41": "untap_all_creatures_you_control",
    "6b315dc3-c330-4b30-b6ad-4da12ccf6ca3": "tap_all_nonwhite_creatures",
    "e4bcd4ea-e7cd-4471-8f3b-18bb51d3d70c": "damage_all_creatures_2",
    "1f513d1e-03ca-4e0f-af48-6490d71d5c41": "damage_all_flying_creatures_4",
    "2894ef5e-738b-4ece-b143-6662d9453295": "damage_nonblack_creature_3_gain_3",
    "b701378f-681b-4840-bd11-1a97c2a675f2": "damage_target_opponent_2_gain_2",
    "eda60752-d225-4fd0-9f0f-9b99e321b8fa": "target_creature_gets_4_power_until_end_of_turn",
    "4527c622-cebe-41eb-9178-4895cccffe99": "target_creature_gets_2_power_and_takes_2",
    "35a05836-38d7-45c7-ac9a-996a682c2129": "target_creature_gets_4_4_until_end_of_turn",
    "d119ca9a-ee82-42c2-81e6-684205ca5183": "destroy_all_green_creatures",
    "fc070e97-73ac-4028-9432-ff2012f2e778": "destroy_all_white_creatures",
    "7421b711-81a4-4042-b024-f55bf9ff203f": "destroy_all_islands",
    "c281f436-8c77-48f7-b31c-d40cd7f9ed6a": "destroy_all_plains",
    "980a9957-6b52-45c6-b847-f84974d5a653": "damage_all_creatures_and_players_1",
    "ede6a352-52de-4ae0-816f-50140033dedf": "damage_all_creatures_and_players_6",
    "9c021685-4017-49c7-9f58-2ae0243361a0": "damage_all_flying_creatures_and_players_x",
    "0c3bf4e1-d91e-4dd3-a800-e40971222c71": "damage_target_creature_per_mountain",
    "5f3ef680-90f4-487f-b44b-db25e29e57ce": "gain_life_per_forest",
    "54ea46ea-7c83-44a9-85b0-eff9745c6ffa": "gain_life_per_opponent_mountain",
    "008011e2-7b82-4962-af6e-be627112f37f": "draw_per_tapped_creature_target_opponent_controls",
    "1980ca2e-a415-4de1-ac30-7055507e82a2": "damage_any_target_4_gain_4",
    "30d9e200-b944-43ff-89b8-a550a788ae03": "return_target_creature_card_from_your_graveyard_to_battlefield",
    "7408b9c5-7266-4627-be4e-b691cf5c622c": "return_target_sorcery_card_from_your_graveyard",
    "90f54959-2c9b-4b8a-84c9-d6893eb43553": "tutor_sorcery_to_top",
    "935e0cac-51ee-4cb7-a209-f085e0f099ed": "tutor_creature_to_top",
    "e5df4597-1647-4ac2-bdb3-a517598d1431": "additional_three_land_plays",
    "ad218276-a44b-4a61-8e42-26a27929bbbb": "all_able_creatures_block_target_this_turn",
    "d3758fca-0522-4b5a-a1cc-3b2b3ab299ba": "target_creature_gets_3_3_and_flying_until_end_of_turn",
    "cb4baf53-51ed-468b-a468-5d7d45a6dc26": "target_creature_gains_flying_and_draw_one",
    "8f8dfc24-f466-4607-8991-acbcbb415db3": "controlled_creatures_get_0_3_until_end_of_turn",
    "5cf28c04-76af-4eb8-9969-366dc8e04690": "controlled_creatures_get_1_1_until_end_of_turn",
    "1f51fea2-ce19-44ef-a330-65cc0fafcd64": "white_creatures_get_2_0_until_end_of_turn",
    "bb493c95-5f6d-405b-aac6-c56fe6b6f42f": "green_controlled_creatures_gain_forestwalk_until_end_of_turn",
    "6b7933b3-821a-4d64-9a10-af8a69fa008e": "black_controlled_creatures_only_blockable_by_black_until_end_of_turn",
    "f215d0f9-a53e-431a-a70d-9dc4e3caa41e": "controlled_creatures_gain_reach_until_end_of_turn",
}


def effect_key_for(oracle_id: str) -> str | None:
    return IMPLEMENTATIONS.get(oracle_id)
