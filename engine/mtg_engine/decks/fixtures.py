"""Small legal Portal decks for local games and end-to-end tests."""

from .models import DeckList


PLAINS = "bc71ebf6-2056-41f7-be35-b2e5c34afa99"
ISLAND = "b2c6aa39-2d2a-459c-a555-fb48ba993373"


def _with_playset_cards(basic_land: str, cards: tuple[str, ...]) -> DeckList:
    return DeckList((basic_land,) * 24 + tuple(card for oracle_id in cards for card in (oracle_id,) * 4))


def portal_white_starter() -> DeckList:
    """A 60-card, all-Portal white creature deck."""
    return _with_playset_cards(PLAINS, (
        "1ef5003c-f540-4cdc-913f-7d5280ad9f62",  # Border Guard
        "a768ba13-4d1c-4dce-a4a6-86a39c069c3f",  # Foot Soldiers
        "f097a059-5505-4c3c-b879-7853ab6972ed",  # Armored Pegasus
        "23625877-b6db-480c-8885-a62b7d0457df",  # Ardent Militia
        "eb098958-50d3-4476-ba74-382033703ff9",  # Wall of Swords
        "6cccf44e-c05e-4239-b643-54b559c98552",  # Charging Paladin
        "5c5cfa6d-857f-44a9-80f7-46f016ef71e4",  # Venerable Monk
        "30870ee5-6ad7-48a9-983e-d3b018f2344f",  # Sacred Nectar
        "b7593cf8-4dcb-473b-a2ef-180fffe66738",  # Path of Peace
    ))


def portal_blue_starter() -> DeckList:
    """A 60-card, all-Portal blue creature deck."""
    return _with_playset_cards(ISLAND, (
        "d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca",  # Wind Drake
        "000d5588-5a4c-434e-988d-396632ade42c",  # Storm Crow
        "10706fd1-7847-4316-be8d-59b56143ce45",  # Coral Eel
        "c181d2a4-5959-4409-9bd3-ecedf8ec9516",  # Giant Octopus
        "9e1a6481-f460-4551-96e8-30b289f2cb92",  # Cloud Spirit
        "e15060c3-3773-4548-8747-ff59dcf2b519",  # Snapping Drake
        "67a3541c-8408-40c8-b44f-90035b860f57",  # Man-o'-War
        "6365aba1-78d3-416c-89cd-9449578eedbf",  # Touch of Brilliance
        "30cc8f7b-3c28-40f5-8f8f-157e8212280b",  # Time Ebb
    ))
