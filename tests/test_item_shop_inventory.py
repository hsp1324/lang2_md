import json
from pathlib import Path
import unittest

from tools.item_shop_inventory import inventory, markdown_report


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"
JSON_PATH = ROOT / "localization/item_shop_inventory.json"
MARKDOWN_PATH = ROOT / "docs/item_shop_runtime_matrix.md"


class ItemShopInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes(), KO_ROM.read_bytes())

    def test_checked_in_reports_match_current_rom(self):
        self.assertEqual(
            json.loads(JSON_PATH.read_text(encoding="utf-8")), self.result
        )
        self.assertEqual(
            MARKDOWN_PATH.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )

    def test_complete_secret_list_covers_every_item_id_once(self):
        self.assertEqual(
            self.result["complete_secret_shop_list"]["item_ids"],
            list(range(1, 38)),
        )
        self.assertEqual(len(self.result["items"]), 37)

    def test_icon_selector_is_unchanged_and_ids_are_contiguous(self):
        self.assertTrue(
            self.result["source_tables"]["production_icon_selector_unchanged"]
        )
        for row in self.result["items"]:
            expected = 0x2200 + (row["id"] - 1) * 4
            self.assertEqual(row["icon_tile_base"], f"0x{expected:04X}")
            self.assertEqual(
                row["icon_tile_ids"],
                [f"0x{expected + index:04X}" for index in range(4)],
            )
        resource = self.result["source_tables"]["item_icon_resource"]
        self.assertEqual(resource["index"], 391)
        self.assertEqual(resource["destination"], "0x4000")
        self.assertEqual(resource["item_icon_bytes"], 37 * 0x80)
        self.assertTrue(resource["production_bytes_identical"])

    def test_runtime_acceptance_is_bound_to_the_item_surface_fingerprint(self):
        self.assertEqual(
            self.result["runtime_probe"]["accepted_capture_checksum"], "D304"
        )
        self.assertEqual(self.result["runtime_probe"]["status"], "accepted")
        self.assertEqual(
            self.result["source_tables"]["item_surface_sha256"],
            self.result["runtime_probe"]["accepted_item_surface_sha256"],
        )
        self.assertTrue(
            all(row["runtime_status"] == "accepted" for row in self.result["items"])
        )

    def test_category_boundaries_match_stock_shop_code(self):
        categories = {row["id"]: row["category"] for row in self.result["items"]}
        self.assertEqual(categories[1], "무기")
        self.assertEqual(categories[16], "무기")
        self.assertEqual(categories[17], "방어구")
        self.assertEqual(categories[25], "방어구")
        self.assertEqual(categories[26], "장신구")
        self.assertEqual(categories[37], "장신구")

    def test_only_item_nine_has_stock_dynamic_price_special_case(self):
        special = [
            row["id"]
            for row in self.result["items"]
            if row["expected_purchase_price_p"] is None
        ]
        self.assertEqual(special, [9])
        self.assertEqual(self.result["items"][0]["expected_purchase_price_p"], 50)


if __name__ == "__main__":
    unittest.main()
