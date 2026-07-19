from pathlib import Path
import unittest

from tools.jp_ui_surface_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class JapaneseUiSurfaceInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes(), KO_ROM.read_bytes())

    def test_declared_patch_baseline(self):
        self.assertEqual(self.result["declared_patch_count"], 120)
        self.assertEqual(self.result["modified_patch_count"], 119)
        name_rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"].startswith("name_entry_")
        ]
        self.assertEqual(len(name_rows), 6)
        self.assertTrue(all(row["reviewed"] for row in name_rows))
        self.assertTrue(all(row["live_verified"] for row in name_rows))

    def test_title_load_and_save_fixed_records_are_live_verified(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"] == "title_load_slot_records"
        ]
        self.assertEqual(len(rows), 5)
        by_target = {row["target_korean"]: row for row in rows}
        self.assertTrue(by_target["이어하기"]["live_verified"])
        self.assertTrue(by_target["시나리오"]["live_verified"])
        self.assertTrue(by_target["손상된 데이터"]["live_verified"])
        self.assertTrue(by_target["데이터 없음"]["live_verified"])
        self.assertTrue(by_target["다음 시나리오"]["live_verified"])
        self.assertTrue(all(row["reviewed"] for row in rows))
        self.assertTrue(all(row["modified"] for row in rows))

        save_headers = [
            row
            for row in self.result["declared_patches"]
            if row["group"] == "title_save_header"
        ]
        self.assertEqual(len(save_headers), 1)
        self.assertTrue(save_headers[0]["live_verified"])

    def test_title_credit_and_main_menu_are_live_verified(self):
        title_groups = {
            "title_main_menu_record",
            "title_credit_font_load_hook",
            "title_credit_render_hook",
            "title_credit_font_load_routine",
            "title_credit_render_routine",
            "title_credit_text_record",
            "title_credit_resource_pointer",
        }
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"] in title_groups
        ]
        self.assertEqual({row["group"] for row in rows}, title_groups)
        self.assertTrue(all(row["modified"] for row in rows))
        self.assertTrue(all(row["reviewed"] for row in rows))
        self.assertTrue(all(row["live_verified"] for row in rows))

    def test_ending_status_labels_are_declared(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["address"] == "0x089146"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_korean"], "격파횟수퇴각횟수")
        self.assertTrue(rows[0]["modified"])
        self.assertTrue(rows[0]["reviewed"])
        self.assertTrue(rows[0]["live_verified"])

    def test_battle_result_header_is_live_verified(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["address"] == "0x0A2D88"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_korean"], "전과보고")
        self.assertTrue(rows[0]["modified"])
        self.assertTrue(rows[0]["reviewed"])
        self.assertTrue(rows[0]["live_verified"])

    def test_compressed_byte_font_is_relocated(self):
        font = self.result["compressed_byte_ui_font"]
        self.assertEqual(font["table_entry"], "0x0B0004")
        self.assertEqual(font["original_pointer"], "0x0B0A84")
        self.assertEqual(font["current_pointer"], "0x290000")
        self.assertTrue(font["relocated"])

    def test_inline_discard_prompt_is_declared_without_runtime_overclaim(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"].startswith("inline_discard_prompt_")
        ]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["modified"] for row in rows))
        self.assertTrue(all(row["reviewed"] for row in rows))
        self.assertTrue(all(not row["live_verified"] for row in rows))

    def test_hidden_sound_test_is_declared_and_live_verified(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"].startswith("sound_test_")
        ]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["modified"] for row in rows))
        self.assertTrue(all(row["reviewed"] for row in rows))
        self.assertTrue(all(row["live_verified"] for row in rows))

    def test_shop_inventory_full_message_is_live_verified(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"].startswith("shop_inventory_full_")
        ]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["modified"] for row in rows))
        self.assertTrue(all(row["reviewed"] for row in rows))
        self.assertTrue(all(row["live_verified"] for row in rows))

    def test_stage_one_keeps_explicit_unknowns(self):
        self.assertGreaterEqual(len(self.result["remaining_inventory_gaps"]), 6)
        class_change_gaps = [
            gap
            for gap in self.result["remaining_inventory_gaps"]
            if "class-change" in gap
        ]
        self.assertEqual(
            class_change_gaps,
            [
                "natural active-commander and save-persistence verification "
                "for class-change paths beyond the two natural Elwin and "
                "Hein proofs"
            ],
        )
        self.assertIn(
            "magic/summon targeting and result paths beyond the "
            "production-faithful Magic Arrow and diagnostic Attack/Elemental probes",
            self.result["remaining_inventory_gaps"],
        )
        self.assertIn(
            "ending and credits UI variants outside the verified Scenario 27, "
            "all-epilogue, ending-visit, and final-credit paths",
            self.result["remaining_inventory_gaps"],
        )
        self.assertNotIn(
            "all equipment and shop variants beyond declared Scenario 1 paths",
            self.result["remaining_inventory_gaps"],
        )


if __name__ == "__main__":
    unittest.main()
