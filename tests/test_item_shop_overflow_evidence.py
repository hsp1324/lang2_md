import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/item_shop_overflow_regression.json"

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
        self.assertEqual(fix["item_name_overflow_vram"], "0xA700..0xB3FF")
        self.assertEqual(fix["shop_reload_hook"], "0x0272D2")
        self.assertEqual(
            fix["forbidden_live_shop_vram"],
            ["0xB400", "0xB700", "0xB800"],
        )
        cluster_vram = (
            builder.ITEM_NAME_OVERFLOW_VRAM_BASE
            + (cause["token"] - builder.ITEM_NAME_GLYPH_PRIMARY_COUNT)
            * builder.ITEM_GLYPH_VRAM_BYTES
        )
        self.assertEqual(fix["new_cluster_vram"], f"0x{cluster_vram:04X}")
        self.assertEqual(cluster_vram, 0xA900)

    def test_historical_report_remains_a_regression_provenance_record(self) -> None:
        rows = self.model["runtime_evidence"]
        self.assertEqual([row["item_id"] for row in rows], [27, 28])
        for row in rows:
            with self.subTest(item=row["selected"]):
                self.assertEqual(row["review"], "pass")
                self.assertEqual(row["visible_rows"], ["크로스", "넥클리스"])

    def test_v139_clean_runtime_evidence_covers_full_shop_and_regressions(self) -> None:
        evidence = self.model["v139_clean_runtime_evidence"]
        self.assertEqual(evidence["normal_rom_md_checksum"], "2E0A")
        self.assertEqual(
            evidence["normal_rom_sha256"],
            "36a857eeef644032eedcdaa2168e81ac1fa39c1dd429f6ec38dcd51aa7b50c71",
        )
        self.assertEqual(evidence["all_item_ids_reviewed"], "1..37")
        self.assertEqual(evidence["preparation_pre_post_pixel_equal_pairs"], 14)
        self.assertEqual(evidence["review"], "pass")
        hashes = evidence["representative_capture_sha256"]
        self.assertEqual(
            set(hashes),
            {
                "item_01_dagger",
                "item_31_crown",
                "item_33_angel_wings",
                "item_35_gleipnir",
                "item_37_mirage_robe",
                "dagger_buy_sell",
                "shop_return",
            },
        )
        self.assertTrue(all(len(value) == 64 for value in hashes.values()))
        self.assertEqual(len(evidence["rejected_symptoms_absent"]), 3)


if __name__ == "__main__":
    unittest.main()
