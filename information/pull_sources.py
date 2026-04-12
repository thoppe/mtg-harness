#!/usr/bin/env python3
"""Pull the declared micro-universe card artifacts and current rules snapshot."""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

SCHEMA_VERSION = 1
SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search?q="
WIZARDS_RULES_PAGE_URL = "https://magic.wizards.com/en/rules"
DEFAULT_USER_AGENT = "mtg-harness/0.1 (information pull workflow; repo-local development)"
DEFAULT_ACCEPT = "application/json"
DEFAULT_IMAGE_VARIANT = "normal"
DEFAULT_IMAGE_FORMAT = "jpg"


@dataclass(frozen=True)
class CardTarget:
    name: str
    set_code: str
    oracle_id: str


MICRO_UNIVERSE = (
    CardTarget(
        name="Border Guard",
        set_code="por",
        oracle_id="1ef5003c-f540-4cdc-913f-7d5280ad9f62",
    ),
    CardTarget(
        name="Foot Soldiers",
        set_code="por",
        oracle_id="a768ba13-4d1c-4dce-a4a6-86a39c069c3f",
    ),
    CardTarget(
        name="Muck Rats",
        set_code="por",
        oracle_id="bca13a12-6723-4a5e-8f1b-21646a8b3e7e",
    ),
    CardTarget(
        name="Vengeance",
        set_code="por",
        oracle_id="1d001145-5d14-43a9-bf3b-3ce5c20b2a46",
    ),
    CardTarget(
        name="Swamp",
        set_code="por",
        oracle_id="56719f6a-1a6c-4c0a-8d21-18f7d7350b68",
    ),
    CardTarget(
        name="Forest",
        set_code="por",
        oracle_id="b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6",
    ),
    CardTarget(
        name="Island",
        set_code="por",
        oracle_id="b2c6aa39-2d2a-459c-a555-fb48ba993373",
    ),
    CardTarget(
        name="Mountain",
        set_code="por",
        oracle_id="a3fb7228-e76b-4e96-a40e-20b5fed75685",
    ),
    CardTarget(
        name="Plains",
        set_code="por",
        oracle_id="bc71ebf6-2056-41f7-be35-b2e5c34afa99",
    ),
)


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_headers(*, accept: str = DEFAULT_ACCEPT) -> dict[str, str]:
    return {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": accept,
    }


def fetch_json(url: str, *, headers: dict[str, str]) -> dict:
    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str, *, headers: dict[str, str]) -> str:
    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return response.read().decode("utf-8")


def fetch_bytes(url: str, *, headers: dict[str, str]) -> bytes:
    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return response.read()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_micro_universe_query(targets: tuple[CardTarget, ...] = MICRO_UNIVERSE) -> str:
    clauses = [f'name:"{target.name}"' for target in targets]
    set_code = targets[0].set_code
    return f'set:{set_code} ({ " or ".join(clauses) })'


def build_scryfall_search_url(targets: tuple[CardTarget, ...] = MICRO_UNIVERSE) -> str:
    return SCRYFALL_SEARCH_URL + quote(build_micro_universe_query(targets))


def validate_card_scope(card: dict, target: CardTarget) -> None:
    if card.get("set") != target.set_code:
        raise ValueError(f"{target.name} returned unexpected set {card.get('set')!r}")
    if card.get("oracle_id") != target.oracle_id:
        raise ValueError(
            f"{target.name} returned unexpected oracle_id {card.get('oracle_id')!r}"
        )


def card_metadata_path(root: Path, oracle_id: str) -> Path:
    return root / "cards" / "data" / f"{oracle_id}.json"


def card_image_path(root: Path, oracle_id: str) -> Path:
    return root / "cards" / "images" / f"{oracle_id}.{DEFAULT_IMAGE_FORMAT}"


def card_image_provenance_path(root: Path, oracle_id: str) -> Path:
    return root / "cards" / "images" / f"{oracle_id}.{DEFAULT_IMAGE_FORMAT}.provenance.json"


def build_card_artifact(card: dict, *, fetched_at: str, request_url: str) -> dict:
    return {
        "artifact_type": "scryfall_card_snapshot",
        "schema_version": SCHEMA_VERSION,
        "canonical_card_id": card["oracle_id"],
        "name": card["name"],
        "provenance": {
            "source_name": "scryfall_api",
            "source_url": card["uri"],
            "fetched_at": fetched_at,
            "request_url": request_url,
            "requested_set_code": card["set"],
            "scryfall_id": card["id"],
            "oracle_id": card["oracle_id"],
            "set_code": card["set"],
            "collector_number": card.get("collector_number"),
            "image_uri_normal": card["image_uris"][DEFAULT_IMAGE_VARIANT],
        },
        "source_record": card,
    }


def build_image_provenance(card: dict, *, fetched_at: str) -> dict:
    return {
        "artifact_type": "scryfall_card_image_snapshot",
        "schema_version": SCHEMA_VERSION,
        "canonical_card_id": card["oracle_id"],
        "image_format": DEFAULT_IMAGE_FORMAT,
        "image_variant": DEFAULT_IMAGE_VARIANT,
        "source_name": "scryfall_image_host",
        "source_url": card["image_uris"][DEFAULT_IMAGE_VARIANT],
        "fetched_at": fetched_at,
        "scryfall_id": card["id"],
        "oracle_id": card["oracle_id"],
        "set_code": card["set"],
    }


def extract_rules_text_url(page_html: str) -> str:
    match = re.search(r'https://media\.wizards\.com/[^"]+MagicCompRules[^"]+\.txt', page_html)
    if not match:
        raise ValueError("Could not locate a Comprehensive Rules text URL on the Wizards rules page")
    return match.group(0)


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    normalized_path = quote(parts.path, safe="/:")
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, parts.query, parts.fragment))


def extract_effective_date(download_url: str) -> str:
    match = re.search(r"(\d{8})(?=\.txt$)", download_url)
    if not match:
        raise ValueError(f"Could not extract effective date from {download_url}")
    yyyymmdd = match.group(1)
    return f"{yyyymmdd[0:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def rules_text_path(root: Path, effective_date: str) -> Path:
    return root / "rules" / "raw" / f"comprehensive_rules_{effective_date}.txt"


def rules_provenance_path(root: Path, effective_date: str) -> Path:
    return root / "rules" / "raw" / f"comprehensive_rules_{effective_date}.txt.provenance.json"


def build_rules_provenance(
    *,
    effective_date: str,
    filename: str,
    fetched_at: str,
    source_download_url: str,
) -> dict:
    return {
        "artifact_type": "wizards_comprehensive_rules_snapshot",
        "schema_version": SCHEMA_VERSION,
        "source_name": "wizards_rules_page",
        "source_page_url": WIZARDS_RULES_PAGE_URL,
        "source_download_url": source_download_url,
        "fetched_at": fetched_at,
        "effective_date": effective_date,
        "filename": filename,
    }


def pull_cards(
    root: Path,
    *,
    json_fetcher: Callable[[str, dict[str, str]], dict],
    bytes_fetcher: Callable[[str, dict[str, str]], bytes],
    sleep_seconds: float = 0.1,
) -> list[Path]:
    request_url = build_scryfall_search_url()
    fetched_at = utc_now_iso()
    search_payload = json_fetcher(request_url, build_headers())
    cards_by_name = {card["name"]: card for card in search_payload["data"]}
    written_paths: list[Path] = []

    for target in MICRO_UNIVERSE:
        card = cards_by_name.get(target.name)
        if card is None:
            raise ValueError(f"Missing card in Scryfall response: {target.name}")
        validate_card_scope(card, target)

        metadata_path = card_metadata_path(root, target.oracle_id)
        image_path = card_image_path(root, target.oracle_id)
        image_provenance = card_image_provenance_path(root, target.oracle_id)

        write_json(
            metadata_path,
            build_card_artifact(card, fetched_at=fetched_at, request_url=request_url),
        )

        image_bytes = bytes_fetcher(
            card["image_uris"][DEFAULT_IMAGE_VARIANT],
            build_headers(accept="image/jpeg"),
        )
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(image_bytes)
        write_json(image_provenance, build_image_provenance(card, fetched_at=fetched_at))

        written_paths.extend((metadata_path, image_path, image_provenance))
        time.sleep(sleep_seconds)

    return written_paths


def pull_rules(
    root: Path,
    *,
    text_fetcher: Callable[[str, dict[str, str]], str],
) -> list[Path]:
    fetched_at = utc_now_iso()
    page_html = text_fetcher(WIZARDS_RULES_PAGE_URL, build_headers(accept="text/html"))
    download_url = normalize_url(extract_rules_text_url(page_html))
    effective_date = extract_effective_date(download_url)
    rules_text = text_fetcher(download_url, build_headers(accept="text/plain"))

    text_path = rules_text_path(root, effective_date)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(rules_text, encoding="utf-8")

    provenance_path = rules_provenance_path(root, effective_date)
    write_json(
        provenance_path,
        build_rules_provenance(
            effective_date=effective_date,
            filename=text_path.name,
            fetched_at=fetched_at,
            source_download_url=download_url,
        ),
    )
    return [text_path, provenance_path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing the cards/ and rules/ folders",
    )
    parser.add_argument(
        "--cards-only",
        action="store_true",
        help="Pull only the declared micro-universe card artifacts",
    )
    parser.add_argument(
        "--rules-only",
        action="store_true",
        help="Pull only the current official rules text snapshot",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.cards_only and args.rules_only:
        raise SystemExit("Choose at most one of --cards-only or --rules-only")

    root = args.output_root.resolve()
    written_paths: list[Path] = []

    try:
        if not args.rules_only:
            written_paths.extend(
                pull_cards(
                    root,
                    json_fetcher=lambda url, headers: fetch_json(url, headers=headers),
                    bytes_fetcher=lambda url, headers: fetch_bytes(url, headers=headers),
                )
            )

        if not args.cards_only:
            written_paths.extend(
                pull_rules(
                    root,
                    text_fetcher=lambda url, headers: fetch_text(url, headers=headers),
                )
            )
    except (HTTPError, URLError, ValueError, KeyError) as exc:
        raise SystemExit(f"pull failed: {exc}") from exc

    for path in written_paths:
        print(path.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
