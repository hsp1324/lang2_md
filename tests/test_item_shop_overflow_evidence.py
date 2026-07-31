import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/item_shop_overflow_regression.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ItemShopOverflowEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_root_cause_and_fixed_layout_match_builder(self) -> None:
        self.assertEqual(self.model["status"], "reviewed_pass")
        cause = self.model["root_cause"]
        fix = self.model["fix"]
        self.assertEqual(cause["item"], "넥클리스")
        self.assertEqual(cause["glyph"], "클")
        self.assertEqual(cause["token"], 68)
        self.assertEqual(cause["old_vram"], "0xB600")
        self.assertEqual(builder.ITEM_DESCRIPTION_VRAM_BASE, 0x5400)
        self.assertEqual(builder.ITEM_NAME_OVERFLOW_VRAM_BASE, 0xA700)
        self.assertEqual(builder.ITEM_NAME_OVERFLOW_VRAM_LIMIT, 0xB400)
        cluster_vram = (
            builder.ITEM_NAME_OVERFLOW_VRAM_BASE
            + (cause["token"] - builder.ITEM_NAME_GLYPH_PRIMARY_COUNT)
            * builder.ITEM_GLYPH_VRAM_BYTES
        )
        self.assertEqual(fix["new_cluster_vram"], f"0x{cluster_vram:04X}")
        self.assertEqual(cluster_vram, 0xA900)

    def test_both_live_shop_captures_are_hash_locked(self) -> None:
        rows = self.model["runtime_evidence"]
        self.assertEqual([row["item_id"] for row in rows], [27, 28])
        for row in rows:
            with self.subTest(item=row["selected"]):
                self.assertEqual(row["review"], "pass")
                self.assertEqual(sha256(ROOT / row["path"]), row["sha256"])
                self.assertEqual(row["visible_rows"], ["크로스", "넥클리스"])

        old = self.model["candidate_builds"]
        current = self.model["current_candidate_applicability"]
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                previous_path = ROOT / old[profile]["path"]
                current_path = ROOT / current[profile]["path"]
                previous = previous_path.read_bytes()
                candidate = current_path.read_bytes()
                changed = [
                    f"0x{offset:06X}"
                    for offset, (before, after) in enumerate(
                        zip(previous, candidate)
                    )
                    if before != after
                ]
                self.assertEqual(
                    changed,
                    current[profile][
                        "changed_from_runtime_evidence_candidate"
                    ],
                )
                self.assertEqual(changed, ["0x00018F", "0x2B7121"])
                self.assertEqual(
                    sha256(current_path),
                    current[profile]["sha256"],
                )
                self.assertEqual(
                    f"{builder.be16(candidate, 0x18E):04X}",
                    current[profile]["md_checksum"],
                )
                self.assertEqual(previous[0x2B7121], 0x00)
                self.assertEqual(candidate[0x2B7121], 0xB0)

    def test_release_was_not_promoted(self) -> None:
        self.assertEqual(
            self.model["release_status"], "candidate_only_not_promoted"
        )


if __name__ == "__main__":
    unittest.main()
