import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_status_dynamic_glyphs.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PreparationStatusDynamicGlyphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_candidate_and_runtime_evidence_are_hash_locked(self) -> None:
        candidate = self.model["candidate"]
        self.assertEqual(sha256(ROOT / candidate["path"]), candidate["sha256"])
        for row in self.model["runtime"]:
            with self.subTest(surface=row["surface"]):
                self.assertEqual(row["result"], "pass")
                self.assertEqual(
                    sha256(ROOT / row["capture"]),
                    row["sha256"],
                )
                if "gst" in row:
                    self.assertEqual(
                        sha256(ROOT / row["gst"]),
                        row["gst_sha256"],
                    )

    def test_runtime_model_matches_builder_slot_ownership(self) -> None:
        scope = self.model["scope"]
        self.assertEqual(
            scope["map_cache_slots_unchanged"],
            len(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS),
        )
        self.assertEqual(
            scope["preparation_extra_chars"],
            list(builder.BYTE_UI_PREP_DYNAMIC_CHARS[-7:]),
        )
        self.assertEqual(
            scope["preparation_extra_tiles"],
            [f"0x{tile:04X}" for tile in builder.BYTE_UI_PREP_EXTRA_TILE_IDS],
        )


if __name__ == "__main__":
    unittest.main()
