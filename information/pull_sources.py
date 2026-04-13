#!/usr/bin/env python3
"""Pull the active support-slice card artifacts and current rules snapshot."""

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

import yaml

SCHEMA_VERSION = 1
SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search?q="
WIZARDS_RULES_PAGE_URL = "https://magic.wizards.com/en/rules"
DEFAULT_USER_AGENT = "mtg-harness/0.1 (information pull workflow; repo-local development)"
DEFAULT_ACCEPT = "application/json"
DEFAULT_IMAGE_VARIANT = "normal"
DEFAULT_IMAGE_FORMAT = "jpg"
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CardTarget:
    set_code: str
    oracle_id: str


def load_active_support_slice_targets() -> tuple[CardTarget, ...]:
    slices_dir = REPO_ROOT / "docs" / "coverage" / "slices"
    manifests = sorted(slices_dir.glob("*.yaml"))
    if not manifests:
        raise ValueError(f"no support-slice manifests found under {slices_dir}")

    active_payloads = []
    for manifest_path in manifests:
        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if payload.get("status") == "active":
            active_payloads.append(payload)

    if not active_payloads:
        raise ValueError(f"no active support slice found under {slices_dir}")
    if len(active_payloads) != 1:
        active_keys = ", ".join(payload["slice_key"] for payload in active_payloads)
        raise ValueError(f"expected exactly one active support slice, found: {active_keys}")

    active_slice = active_payloads[0]
    if "card_entries" in active_slice:
        return tuple(
            CardTarget(
                set_code=entry["set_code"],
                oracle_id=entry["oracle_id"],
            )
            for entry in active_slice["card_entries"]
        )

    set_code = active_slice["set_code"]
    card_keys = tuple(active_slice["card_keys"])
    return tuple(CardTarget(set_code=set_code, oracle_id=oracle_id) for oracle_id in card_keys)


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


def build_support_slice_query(targets: tuple[CardTarget, ...]) -> str:
    by_set: dict[str, list[str]] = {}
    for target in targets:
        by_set.setdefault(target.set_code, []).append(target.oracle_id)

    set_clauses = []
    for set_code, oracle_ids in by_set.items():
        oracle_clauses = " or ".join(f"oracleid:{oracle_id}" for oracle_id in oracle_ids)
        set_clauses.append(f"set:{set_code} ({oracle_clauses})")
    return " or ".join(f"({clause})" for clause in set_clauses)


def build_scryfall_search_url(targets: tuple[CardTarget, ...]) -> str:
    return SCRYFALL_SEARCH_URL + quote(build_support_slice_query(targets))


def validate_card_scope(card: dict, target: CardTarget) -> None:
    if card.get("set") != target.set_code:
        raise ValueError(f"{target.oracle_id} returned unexpected set {card.get('set')!r}")
    if card.get("oracle_id") != target.oracle_id:
        raise ValueError(
            f"{target.oracle_id} returned unexpected oracle_id {card.get('oracle_id')!r}"
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
    targets = load_active_support_slice_targets()
    fetched_at = utc_now_iso()
    written_paths: list[Path] = []

    for target in targets:
        request_url = build_scryfall_search_url((target,))
        search_payload = json_fetcher(request_url, build_headers())
        cards = search_payload["data"]
        if len(cards) != 1:
            raise ValueError(f"Expected exactly one card in Scryfall response for {target.oracle_id}")
        card = cards[0]
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
        help="Pull only the active support-slice card artifacts",
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
