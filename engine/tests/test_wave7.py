from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mtg_engine.cards.implementations import effect_key_for
from mtg_engine.cards.repository import CardRepository


INFO = Path(__file__).resolve().parents[2] / "information"

# This is deliberately an identity-level assertion: source text can be
# reformatted upstream without accidentally enabling a different card.
WAVE_SEVEN_IDS = {
    "76da2150-34b9-4483-99df-131e1c5468d5", "70e0b676-61a2-4dcf-8f61-d9281467ed43", "09fe624f-c66a-46e4-a9af-7e3c3ca1a4e3", "0c67133b-be15-47d7-8cf6-79987a42044d", "6cccf44e-c05e-4239-b643-54b559c98552", "fd57dfa5-f29d-4b79-8748-c34a73efb7f0", "3f01f627-9fbd-470b-8001-974784ccf421", "05e61628-cdae-4664-b866-be438fb3a6ba", "bd73ab86-0ac9-4ce0-be41-f4ad257e74f6", "12e4d2bd-83e9-4120-a2e8-0645c0ed2387", "9f31dbb1-c350-46f8-bd1d-9f23a073d2f1", "349d8ef9-e07a-416f-a5b1-2c2be6bb322d", "5bd806e7-3f9b-4bb4-9708-f87a578f531e", "e96542ed-1931-4da1-9d9e-d10878c4ae6b", "1a2030cc-d7ee-4059-b2d7-fb95ea8e267b", "fe4bee2c-f03f-44a4-94a4-55a06bcd0ad8", "73ea2949-5812-478d-8f09-00743ce4d40f", "4e3f89e2-2be6-4b96-b81c-007b6840af82", "67a3541c-8408-40c8-b44f-90035b860f57", "ed5429bb-233a-4528-bf7d-df5f6b192b1c", "d2bd23a6-4f77-4d6e-bf8f-339cb7a4184d", "2fdc484e-b3c3-4f4e-99a1-26a1134aa1cd", "099a5835-da6c-4e03-ad3e-aeb448897fed", "ad07cb55-cc4f-40be-b16a-bd3d3ca94249", "e822bf3d-3a29-4a02-9ae8-e2830ce70f15", "f4170db0-3adf-4744-b0ec-e889c713bb93", "db025c94-1182-412e-9665-b5ae89d26616", "0c7239bf-dc8a-4d79-867e-7a4225568c49", "3bc7d3a7-ddb4-4eaa-882e-404d8f2926fb", "fe249f27-db6c-4826-836e-a04efb1a3eaa", "d03860b4-c663-4230-9200-6b89fa849ae7", "00602959-e9a1-4706-a1cb-70156a6fc713", "9542bd7f-bb99-4b59-a4e3-b88ed9f798bf", "cdab50a8-1e02-4ba5-8c09-e2837e7652f7", "58fa33fd-02a4-4ec9-9226-82594cfec363", "5ae03181-a436-4bad-be3a-6c9f6c0ed4d6", "5c5cfa6d-857f-44a9-80f7-46f016ef71e4", "8973bd99-20f8-4867-90ef-50392147ee1b",
}


class WaveSevenIdentityTests(unittest.TestCase):
    def test_every_wave_seven_oracle_identity_has_one_registered_effect(self) -> None:
        repo = CardRepository.from_information_directory(INFO)
        self.assertEqual(len(WAVE_SEVEN_IDS), 38)
        self.assertTrue(all(repo.has(oracle_id) and effect_key_for(oracle_id) for oracle_id in WAVE_SEVEN_IDS))

