import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/class_change_mercenary_glyph_regression.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ClassChangeMercenaryGlyphRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_class_change_mercenary_renderer_uses_preparation_lookup(self) -> None:
        self.assertEqual(self.model["status"], "reviewed_pass")
        fix = self.model["fix"]
        self.assertEqual(
            fix["new_lookup"],
            "BYTE_UI_PREP_LOCAL_TILE_LOOKUP_ROUTINE",
        )
        renderer = builder._build_byte_ui_tile_renderer()
        prep_call = (
            bytes.fromhex("4E B9")
            + builder.BYTE_UI_PREP_LOCAL_TILE_LOOKUP_ROUTINE.to_bytes(4, "big")
        )
        static_call = (
            bytes.fromhex("4E B9")
            + builder.BYTE_UI_LOCAL_TILE_LOOKUP_ROUTINE.to_bytes(4, "big")
        )
        self.assertIn(prep_call, renderer)
        self.assertNotIn(static_call, renderer)
        for offset in (0x02C004, 0x02C040):
            self.assertIn(offset, builder.BYTE_UI_TILE_RENDER_CALLS)

    def test_reported_shared_glyph_is_in_the_dynamic_pool(self) -> None:
        report = self.model["reported_capture"]
        self.assertEqual(report["shared_corrupted_glyph"], "스")
        self.assertEqual(report["visible_failure"], ["팔랑크스", "발리스타"])
        self.assertIn("스", builder.BYTE_UI_PREP_DYNAMIC_CHARS)

    def test_normal_and_hard_capture_sets_are_hash_locked(self) -> None:
        evidence = self.model["runtime_evidence"]
        normal_hashes = []
        hard_hashes = []
        for profile, hashes in (("normal", normal_hashes), ("hard", hard_hashes)):
            rows = evidence[profile]
            self.assertEqual(
                [row["candidate"] for row in rows],
                ["그랑나이트", "실버나이트", "아크메이지"],
            )
            for row in rows:
                actual = sha256(ROOT / row["path"])
                self.assertEqual(actual, row["sha256"])
                hashes.append(actual)
        self.assertTrue(evidence["normal_hard_pairs_byte_identical"])
        self.assertEqual(normal_hashes, hard_hashes)

    def test_failure_capture_is_retained_and_release_is_not_promoted(self) -> None:
        failing = self.model["reproduction"]["failing_capture"]
        self.assertEqual(sha256(ROOT / failing["path"]), failing["sha256"])
        self.assertFalse(self.model["fix"]["release_promoted"])


if __name__ == "__main__":
    unittest.main()
