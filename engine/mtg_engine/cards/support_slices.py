from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SupportSlice:
    slice_key: str
    display_name: str
    status: str
    set_code: str | None
    card_keys: tuple[str, ...]
    deck_eligible_card_keys: tuple[str, ...]
    rule_keys: tuple[str, ...]
    source_artifacts: tuple[str, ...]
    notes: str


def load_active_support_slice(repo_root: Path) -> SupportSlice:
    slices_dir = repo_root / "docs" / "coverage" / "slices"
    manifests = sorted(slices_dir.glob("*.yaml"))
    if not manifests:
        raise ValueError(f"no support-slice manifests found under {slices_dir}")

    active_slices: list[SupportSlice] = []
    for manifest_path in manifests:
        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if payload.get("status") != "active":
            continue
        card_entries = payload.get("card_entries")
        if card_entries is not None:
            card_keys = tuple(entry["oracle_id"] for entry in card_entries)
            deck_eligible_card_keys = tuple(
                entry["oracle_id"]
                for entry in card_entries
                if entry.get("deck_eligible", True)
            )
        else:
            card_keys = tuple(payload["card_keys"])
            deck_eligible_card_keys = card_keys

        active_slices.append(
            SupportSlice(
                slice_key=payload["slice_key"],
                display_name=payload["display_name"],
                status=payload["status"],
                set_code=payload.get("set_code"),
                card_keys=card_keys,
                deck_eligible_card_keys=deck_eligible_card_keys,
                rule_keys=tuple(payload["rule_keys"]),
                source_artifacts=tuple(payload["source_artifacts"]),
                notes=payload.get("notes", ""),
            )
        )

    if not active_slices:
        raise ValueError(f"no active support slice found under {slices_dir}")
    if len(active_slices) != 1:
        active_keys = ", ".join(slice_.slice_key for slice_ in active_slices)
        raise ValueError(f"expected exactly one active support slice, found: {active_keys}")
    return active_slices[0]
