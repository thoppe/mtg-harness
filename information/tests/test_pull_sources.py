from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pull_sources


def sample_card(*, name: str, oracle_id: str, card_id: str, collector_number: str, set_code: str = "por") -> dict:
    return {
        "id": card_id,
        "oracle_id": oracle_id,
        "name": name,
        "set": set_code,
        "collector_number": collector_number,
        "uri": f"https://api.scryfall.com/cards/{card_id}",
        "image_uris": {
            "normal": f"https://cards.scryfall.io/normal/front/{card_id}.jpg",
        },
    }


class PullSourcesTests(unittest.TestCase):
    def test_load_active_support_slice_targets_reads_manifest_scope(self) -> None:
        targets = pull_sources.load_active_support_slice_targets()

        self.assertEqual(targets[0].set_code, "por")
        self.assertEqual(targets[0].oracle_id, "1ef5003c-f540-4cdc-913f-7d5280ad9f62")
        self.assertEqual(targets[-1].oracle_id, "91c0a76e-3992-437f-b85a-97b0b4adbb84")
        self.assertIn("c9ed8b01-959a-47d6-891e-0abbdccf6e4f", [target.oracle_id for target in targets])
        self.assertIn("e2048201-6dc9-4cf5-916f-1d867ae8dbdd", [target.oracle_id for target in targets])
        self.assertIn("b7593cf8-4dcb-473b-a2ef-180fffe66738", [target.oracle_id for target in targets])
        self.assertIn("f097a059-5505-4c3c-b879-7853ab6972ed", [target.oracle_id for target in targets])
        self.assertIn("d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca", [target.oracle_id for target in targets])
        self.assertIn("45b94e3c-a905-435b-aee5-bec9239fd24c", [target.oracle_id for target in targets])
        self.assertIn("000d5588-5a4c-434e-988d-396632ade42c", [target.oracle_id for target in targets])
        self.assertIn("0ace32d6-7261-447c-9ee2-e03febaab91b", [target.oracle_id for target in targets])
        self.assertIn("3eff03f1-2c5f-4c59-b465-a8c4cd05e1ba", [target.oracle_id for target in targets])
        self.assertIn("dc45b2e3-272b-479b-8e3b-36eead606a3a", [target.oracle_id for target in targets])
        self.assertIn("30870ee5-6ad7-48a9-983e-d3b018f2344f", [target.oracle_id for target in targets])
        self.assertIn("be738992-77fe-498d-b219-e5da4ce5bf07", [target.oracle_id for target in targets])

    def test_pull_cards_writes_canonical_paths_and_provenance(self) -> None:
        cards = [
            sample_card(
                name="Border Guard",
                oracle_id="1ef5003c-f540-4cdc-913f-7d5280ad9f62",
                card_id="985af775-2036-459d-83c6-31ac84a0ffb1",
                collector_number="9",
            ),
            sample_card(
                name="Foot Soldiers",
                oracle_id="a768ba13-4d1c-4dce-a4a6-86a39c069c3f",
                card_id="458ddb33-66c4-4753-b1eb-8937ab812a81",
                collector_number="16",
            ),
            sample_card(
                name="Plains",
                oracle_id="bc71ebf6-2056-41f7-be35-b2e5c34afa99",
                card_id="90d35453-7fe3-4053-aad9-a124ecc7dcf0",
                collector_number="196",
            ),
            sample_card(
                name="Muck Rats",
                oracle_id="bca13a12-6723-4a5e-8f1b-21646a8b3e7e",
                card_id="d4041226-7ce2-46d1-8844-20fa50b6568a",
                collector_number="102",
            ),
            sample_card(
                name="Wind Drake",
                oracle_id="d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca",
                card_id="5486d2dc-9a5d-4f58-a5ec-d94de54b852f",
                collector_number="77",
            ),
            sample_card(
                name="Bog Imp",
                oracle_id="45b94e3c-a905-435b-aee5-bec9239fd24c",
                card_id="8681b3fd-33e5-4a45-8650-a4a142405096",
                collector_number="81",
            ),
            sample_card(
                name="Storm Crow",
                oracle_id="000d5588-5a4c-434e-988d-396632ade42c",
                card_id="dfe87b59-b456-4532-a695-0dea3110d878",
                collector_number="69",
            ),
            sample_card(
                name="Vengeance",
                oracle_id="1d001145-5d14-43a9-bf3b-3ce5c20b2a46",
                card_id="c91c249b-157c-4f1d-8171-29d1e75b1c9f",
                collector_number="36",
            ),
            sample_card(
                name="Path of Peace",
                oracle_id="b7593cf8-4dcb-473b-a2ef-180fffe66738",
                card_id="a1f3e1c9-bfad-49a1-b171-6fa344ef2eef",
                collector_number="21",
            ),
            sample_card(
                name="Touch of Brilliance",
                oracle_id="6365aba1-78d3-416c-89cd-9449578eedbf",
                card_id="196474ce-e28e-48f0-b407-dc5535adf1b6",
                collector_number="76",
            ),
            sample_card(
                name="Time Ebb",
                oracle_id="30cc8f7b-3c28-40f5-8f8f-157e8212280b",
                card_id="e5fd26ca-dc7d-453d-8653-7f967e8f6dc7",
                collector_number="75",
            ),
            sample_card(
                name="Armored Pegasus",
                oracle_id="f097a059-5505-4c3c-b879-7853ab6972ed",
                card_id="a81b61af-cdb7-468f-9ff0-db82aa084023",
                collector_number="6",
            ),
            sample_card(
                name="Armageddon",
                oracle_id="c9ed8b01-959a-47d6-891e-0abbdccf6e4f",
                card_id="2073ca8b-2bca-4539-94d7-989da157e4b8",
                collector_number="5",
            ),
            sample_card(
                name="Rain of Daggers",
                oracle_id="e2048201-6dc9-4cf5-916f-1d867ae8dbdd",
                card_id="f48b345f-c814-4f89-9bff-078d0ec5acfc",
                collector_number="94",
                set_code="me4",
            ),
            sample_card(
                name="Swamp",
                oracle_id="56719f6a-1a6c-4c0a-8d21-18f7d7350b68",
                card_id="ec0da69e-4ab6-4ef1-a7ae-4d6c47172c81",
                collector_number="204",
            ),
            sample_card(
                name="Forest",
                oracle_id="b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6",
                card_id="40146f61-d3f0-45e7-82b5-788ff7b0e520",
                collector_number="212",
            ),
            sample_card(
                name="Island",
                oracle_id="b2c6aa39-2d2a-459c-a555-fb48ba993373",
                card_id="e98d1e6f-5902-4e67-91a6-30eb5c3ce4a1",
                collector_number="200",
            ),
            sample_card(
                name="Mountain",
                oracle_id="a3fb7228-e76b-4e96-a40e-20b5fed75685",
                card_id="17cf7ce4-d5d7-49f2-a7e4-021d1a2d58c5",
                collector_number="208",
            ),
        ]

        def json_fetcher(url: str, headers: dict[str, str]) -> dict:
            self.assertIn("User-Agent", headers)
            self.assertEqual(headers["Accept"], "application/json")
            decoded_url = unquote(url)
            for card in cards:
                if card["oracle_id"] in decoded_url:
                    return {"data": [card]}
            oracle_match = re.search(r"oracleid:([0-9a-f-]+)", decoded_url)
            set_match = re.search(r"set:([a-z0-9]+)", decoded_url)
            if oracle_match and set_match:
                oracle_id = oracle_match.group(1)
                set_code = set_match.group(1)
                return {
                    "data": [
                        sample_card(
                            name=f"Card {oracle_id}",
                            oracle_id=oracle_id,
                            card_id=f"{oracle_id}-print",
                            collector_number="0",
                            set_code=set_code,
                        )
                    ]
                }
            self.fail(f"unexpected card query URL: {url}")

        def bytes_fetcher(url: str, headers: dict[str, str]) -> bytes:
            self.assertEqual(headers["Accept"], "image/jpeg")
            return f"image:{url}".encode("utf-8")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            written = pull_sources.pull_cards(
                root,
                json_fetcher=json_fetcher,
                bytes_fetcher=bytes_fetcher,
                sleep_seconds=0,
            )

            self.assertEqual(len(written), len(pull_sources.load_active_support_slice_targets()) * 3)
            metadata_path = root / "cards" / "data" / "1ef5003c-f540-4cdc-913f-7d5280ad9f62.json"
            image_path = root / "cards" / "images" / "1ef5003c-f540-4cdc-913f-7d5280ad9f62.jpg"
            image_provenance_path = (
                root / "cards" / "images" / "1ef5003c-f540-4cdc-913f-7d5280ad9f62.jpg.provenance.json"
            )

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            image_provenance = json.loads(image_provenance_path.read_text(encoding="utf-8"))

            self.assertEqual(metadata["artifact_type"], "scryfall_card_snapshot")
            self.assertEqual(metadata["canonical_card_id"], "1ef5003c-f540-4cdc-913f-7d5280ad9f62")
            self.assertEqual(metadata["source_record"]["name"], "Border Guard")
            self.assertEqual(image_path.read_bytes(), b"image:https://cards.scryfall.io/normal/front/985af775-2036-459d-83c6-31ac84a0ffb1.jpg")
            self.assertEqual(image_provenance["artifact_type"], "scryfall_card_image_snapshot")
            self.assertEqual(image_provenance["image_variant"], "normal")

    def test_pull_cards_can_limit_to_single_active_oracle_id(self) -> None:
        requested_oracle_id = "1ef5003c-f540-4cdc-913f-7d5280ad9f62"
        card = sample_card(
            name="Border Guard",
            oracle_id=requested_oracle_id,
            card_id="985af775-2036-459d-83c6-31ac84a0ffb1",
            collector_number="9",
        )
        requested_urls: list[str] = []

        def json_fetcher(url: str, headers: dict[str, str]) -> dict:
            requested_urls.append(unquote(url))
            return {"data": [card]}

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            written = pull_sources.pull_cards(
                root,
                json_fetcher=json_fetcher,
                bytes_fetcher=lambda url, headers: b"image",
                sleep_seconds=0,
                oracle_ids=(requested_oracle_id,),
            )

            self.assertEqual(len(written), 3)
            self.assertEqual(len(requested_urls), 1)
            self.assertIn(requested_oracle_id, requested_urls[0])

    def test_pull_cards_rejects_unknown_oracle_id_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                pull_sources.pull_cards(
                    Path(tmpdir),
                    json_fetcher=lambda url, headers: {"data": []},
                    bytes_fetcher=lambda url, headers: b"unused",
                    sleep_seconds=0,
                    oracle_ids=("00000000-0000-0000-0000-000000000000",),
                )

    def test_pull_cards_rejects_scope_mismatch(self) -> None:
        bad_cards = [
            sample_card(
                name="Border Guard",
                oracle_id="wrong-oracle-id",
                card_id="985af775-2036-459d-83c6-31ac84a0ffb1",
                collector_number="9",
            ),
            sample_card(
                name="Foot Soldiers",
                oracle_id="a768ba13-4d1c-4dce-a4a6-86a39c069c3f",
                card_id="458ddb33-66c4-4753-b1eb-8937ab812a81",
                collector_number="16",
            ),
            sample_card(
                name="Plains",
                oracle_id="bc71ebf6-2056-41f7-be35-b2e5c34afa99",
                card_id="90d35453-7fe3-4053-aad9-a124ecc7dcf0",
                collector_number="196",
            ),
            sample_card(
                name="Muck Rats",
                oracle_id="bca13a12-6723-4a5e-8f1b-21646a8b3e7e",
                card_id="d4041226-7ce2-46d1-8844-20fa50b6568a",
                collector_number="102",
            ),
            sample_card(
                name="Wind Drake",
                oracle_id="d6ffdaf0-ac08-4de9-bbce-2eab2f86bcca",
                card_id="5486d2dc-9a5d-4f58-a5ec-d94de54b852f",
                collector_number="77",
            ),
            sample_card(
                name="Bog Imp",
                oracle_id="45b94e3c-a905-435b-aee5-bec9239fd24c",
                card_id="8681b3fd-33e5-4a45-8650-a4a142405096",
                collector_number="81",
            ),
            sample_card(
                name="Storm Crow",
                oracle_id="000d5588-5a4c-434e-988d-396632ade42c",
                card_id="dfe87b59-b456-4532-a695-0dea3110d878",
                collector_number="69",
            ),
            sample_card(
                name="Vengeance",
                oracle_id="1d001145-5d14-43a9-bf3b-3ce5c20b2a46",
                card_id="c91c249b-157c-4f1d-8171-29d1e75b1c9f",
                collector_number="36",
            ),
            sample_card(
                name="Path of Peace",
                oracle_id="b7593cf8-4dcb-473b-a2ef-180fffe66738",
                card_id="a1f3e1c9-bfad-49a1-b171-6fa344ef2eef",
                collector_number="21",
            ),
            sample_card(
                name="Touch of Brilliance",
                oracle_id="6365aba1-78d3-416c-89cd-9449578eedbf",
                card_id="196474ce-e28e-48f0-b407-dc5535adf1b6",
                collector_number="76",
            ),
            sample_card(
                name="Time Ebb",
                oracle_id="30cc8f7b-3c28-40f5-8f8f-157e8212280b",
                card_id="e5fd26ca-dc7d-453d-8653-7f967e8f6dc7",
                collector_number="75",
            ),
            sample_card(
                name="Armored Pegasus",
                oracle_id="f097a059-5505-4c3c-b879-7853ab6972ed",
                card_id="a81b61af-cdb7-468f-9ff0-db82aa084023",
                collector_number="6",
            ),
            sample_card(
                name="Armageddon",
                oracle_id="c9ed8b01-959a-47d6-891e-0abbdccf6e4f",
                card_id="2073ca8b-2bca-4539-94d7-989da157e4b8",
                collector_number="5",
            ),
            sample_card(
                name="Rain of Daggers",
                oracle_id="e2048201-6dc9-4cf5-916f-1d867ae8dbdd",
                card_id="f48b345f-c814-4f89-9bff-078d0ec5acfc",
                collector_number="94",
                set_code="me4",
            ),
            sample_card(
                name="Swamp",
                oracle_id="56719f6a-1a6c-4c0a-8d21-18f7d7350b68",
                card_id="ec0da69e-4ab6-4ef1-a7ae-4d6c47172c81",
                collector_number="204",
            ),
            sample_card(
                name="Forest",
                oracle_id="b34bb2dc-c1af-4d77-b0b3-a0fb342a5fc6",
                card_id="40146f61-d3f0-45e7-82b5-788ff7b0e520",
                collector_number="212",
            ),
            sample_card(
                name="Island",
                oracle_id="b2c6aa39-2d2a-459c-a555-fb48ba993373",
                card_id="e98d1e6f-5902-4e67-91a6-30eb5c3ce4a1",
                collector_number="200",
            ),
            sample_card(
                name="Mountain",
                oracle_id="a3fb7228-e76b-4e96-a40e-20b5fed75685",
                card_id="17cf7ce4-d5d7-49f2-a7e4-021d1a2d58c5",
                collector_number="208",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                pull_sources.pull_cards(
                    Path(tmpdir),
                    json_fetcher=lambda url, headers: {
                        "data": [card for card in bad_cards if card["oracle_id"] in url] or bad_cards[:1]
                    },
                    bytes_fetcher=lambda url, headers: b"unused",
                    sleep_seconds=0,
                )

    def test_pull_rules_writes_versioned_snapshot_and_provenance(self) -> None:
        rules_html = """
        <p><a class="cta" href="https://media.wizards.com/2026/downloads/MagicCompRules 20260227.txt">TXT</a></p>
        """
        rules_text = "Comprehensive Rules\n"

        def text_fetcher(url: str, headers: dict[str, str]) -> str:
            if url == pull_sources.WIZARDS_RULES_PAGE_URL:
                self.assertEqual(headers["Accept"], "text/html")
                return rules_html
            self.assertEqual(headers["Accept"], "text/plain")
            return rules_text

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            written = pull_sources.pull_rules(root, text_fetcher=text_fetcher)

            text_path = root / "rules" / "raw" / "comprehensive_rules_2026-02-27.txt"
            provenance_path = (
                root / "rules" / "raw" / "comprehensive_rules_2026-02-27.txt.provenance.json"
            )
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

            self.assertEqual(written, [text_path, provenance_path])
            self.assertEqual(text_path.read_text(encoding="utf-8"), rules_text)
            self.assertEqual(provenance["artifact_type"], "wizards_comprehensive_rules_snapshot")
            self.assertEqual(provenance["effective_date"], "2026-02-27")


if __name__ == "__main__":
    unittest.main()
