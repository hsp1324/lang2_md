import hashlib
import json
from pathlib import Path
import unittest

from tools import rom_update


ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "localization/ai_class_release_delta.json"
HARD_ROM = (
    ROOT
    / "roms/releases/Langrisser II (Korean Hard T1.0.0 B1.0.0).md"
)
NORMAL_ROM = (
    ROOT / "roms/releases/Langrisser II (Korean ko-99fd).md"
)
NORMAL_SHA256 = (
    "526237277c8f46a4400c00980da704e6ebea23e74d967d89b6d223db28dd54d3"
)


class AiClassReleaseDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.hard = HARD_ROM.read_bytes()
        cls.normal = NORMAL_ROM.read_bytes()

    def test_current_hard_identity_is_hash_locked(self) -> None:
        current = self.model["after"]
        self.assertEqual(
            hashlib.sha256(self.hard).hexdigest(),
            current["sha256"],
        )
        self.assertEqual(
            f"{rom_update.md_header_checksum(self.hard):04X}",
            current["md_checksum"],
        )
        self.assertEqual(
            rom_update.md_checksum(self.hard),
            rom_update.md_header_checksum(self.hard),
        )

    def test_predecessor_reproduction_is_hash_locked(self) -> None:
        self.assertEqual(
            self.model["reproduction"]["predecessor_commit"],
            "1360b69",
        )
        self.assertEqual(
            self.model["before"]["sha256"],
            self.model["reproduction"]["expected_predecessor_sha256"],
        )
        self.assertEqual(self.model["before"]["md_checksum"], "0718")

    def test_delta_is_limited_to_declared_cosmetic_ownership(self) -> None:
        delta = self.model["delta"]
        categories = delta["categories"]
        self.assertEqual(self.model["status"], "verified_cosmetic_only_delta")
        self.assertEqual(delta["changed_byte_count"], 10266)
        self.assertEqual(categories["outside_owned_ranges"], 0)
        self.assertEqual(delta["unexpected_offsets"], [])
        self.assertEqual(delta["balance_event_ai_changed_bytes"], 0)
        self.assertTrue(delta["sram_descriptor_unchanged"])
        self.assertEqual(
            sum(categories.values()),
            delta["changed_byte_count"],
        )

    def test_all_promoted_records_and_frames_are_in_the_delta(self) -> None:
        self.assertEqual(
            self.model["ownership"]["promoted_mapping_records"],
            40,
        )
        self.assertEqual(
            self.model["ownership"]["promoted_animation_frames"],
            80,
        )
        self.assertEqual(len(self.model["mappings"]), 40)
        self.assertEqual(len(self.model["frames"]), 80)
        self.assertEqual(
            len({
                row["record_offset"] for row in self.model["mappings"]
            }),
            40,
        )
        self.assertEqual(
            len({row["offset"] for row in self.model["frames"]}),
            80,
        )

    def test_normal_release_remains_immutable(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.normal).hexdigest(),
            NORMAL_SHA256,
        )
        self.assertEqual(
            f"{rom_update.md_header_checksum(self.normal):04X}",
            "99FD",
        )


if __name__ == "__main__":
    unittest.main()
