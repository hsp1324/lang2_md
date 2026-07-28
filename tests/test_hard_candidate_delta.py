import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools import verify_hard_candidate_delta as verifier


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/hard_mode_candidate_delta.json"
HARD_BUILD = (
    ROOT
    / "roms/builds/Langrisser II (Korean Hard T1.0.0 B1.0.0).md"
)


class HardCandidateDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))
        cls.hard = HARD_BUILD.read_bytes()

    def test_current_build_identity_is_hash_locked(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.hard).hexdigest(),
            self.model["after"]["sha256"],
        )
        self.assertEqual(self.model["after"]["md_checksum"], "8674")

    def test_delta_is_ui_and_sprite_only(self) -> None:
        delta = self.model["delta"]
        self.assertEqual(
            self.model["status"],
            "verified_ui_sprite_only_delta",
        )
        self.assertEqual(delta["changed_byte_count"], 365)
        self.assertEqual(delta["outside_owned_ranges"], 0)
        self.assertEqual(delta["unexpected_offsets"], [])
        self.assertEqual(delta["balance_event_ai_changed_bytes"], 0)
        self.assertTrue(delta["sram_descriptor_unchanged"])
        self.assertEqual(
            sum(delta["categories"].values()),
            delta["changed_byte_count"],
        )

    def test_manifest_matches_fresh_classification(self) -> None:
        fresh = verifier.build_model(
            verifier.DEFAULT_BEFORE,
            verifier.DEFAULT_AFTER,
        )
        self.assertEqual(fresh, self.model)

    def test_unowned_change_is_rejected(self) -> None:
        before = verifier.DEFAULT_BEFORE.read_bytes()
        after = bytearray(before)
        after[0x1802D8] ^= 0x01
        after[0x18E:0x190] = verifier.rom_update.md_checksum(after).to_bytes(
            2,
            "big",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            before_path = Path(directory) / "before.md"
            after_path = Path(directory) / "after.md"
            before_path.write_bytes(before)
            after_path.write_bytes(after)
            with self.assertRaisesRegex(
                ValueError,
                "outside owned ranges",
            ):
                verifier.build_model(before_path, after_path)


if __name__ == "__main__":
    unittest.main()
