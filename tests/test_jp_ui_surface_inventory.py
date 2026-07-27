from pathlib import Path
import unittest

from tools.jp_ui_surface_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class JapaneseUiSurfaceInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes(), KO_ROM.read_bytes())

    def test_declared_patch_baseline(self):
        self.assertEqual(self.result["declared_patch_count"], 143)
        self.assertEqual(self.result["modified_patch_count"], 142)
        name_rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"].startswith("name_entry_")
        ]
        self.assertEqual(len(name_rows), 6)
        self.assertTrue(all(row["reviewed"] for row in name_rows))
        self.assertTrue(all(row["live_verified"] for row in name_rows))

    def test_control_settings_rows_are_declared_and_live_verified(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"].startswith("control_settings_")
        ]
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["modified"] for row in rows))
        self.assertTrue(all(row["reviewed"] for row in rows))
        self.assertTrue(all(row["live_verified"] for row in rows))

    def test_spaced_name_prompt_is_live_verified(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["address"] == "0x0A37BE"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_korean"], "이름을 정해주세요")
        self.assertTrue(rows[0]["modified"])
        self.assertTrue(rows[0]["reviewed"])
        self.assertTrue(rows[0]["live_verified"])

    def test_source_reviewed_ending_montage_is_live_verified(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"] == "opening_text_lists"
        ]
        reviewed = [row for row in rows if row["reviewed"]]
        live_verified = [row for row in rows if row["live_verified"]]
        pending_live = [row for row in rows if not row["live_verified"]]
        self.assertEqual(len(reviewed), 12)
        self.assertEqual(len(live_verified), 12)
        self.assertEqual(pending_live, [])
        self.assertNotIn(
            "리아나가 위험해",
            "".join(str(row["target_korean"]) for row in reviewed),
        )

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

    def test_title_logo_resource_and_layout_are_live_verified(self):
        title_groups = {
            "title_logo_original_resource_pointer",
            "title_logo_active_resource_pointer",
            "title_logo_layout_record",
            "title_logo_resource_payload",
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

    def test_battle_ui_terrain_resource_is_live_verified(self):
        terrain_groups = {
            "battle_ui_terrain_original_resource_pointer",
            "battle_ui_terrain_active_resource_pointer",
            "battle_ui_terrain_resource_payload",
        }
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"] in terrain_groups
        ]
        self.assertEqual({row["group"] for row in rows}, terrain_groups)
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

    def test_inline_discard_prompt_is_declared_and_live_verified(self):
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"].startswith("inline_discard_prompt_")
        ]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["modified"] for row in rows))
        self.assertTrue(all(row["reviewed"] for row in rows))
        self.assertTrue(all(row["live_verified"] for row in rows))

    def test_runtime_evidence_closes_stale_ui_statuses_only(self):
        rows = self.result["declared_patches"]
        self.assertEqual(sum(bool(row["reviewed"]) for row in rows), 143)
        self.assertEqual(sum(bool(row["live_verified"]) for row in rows), 142)

        pending_live = [row for row in rows if not row["live_verified"]]
        self.assertEqual(len(pending_live), 1)
        self.assertEqual(pending_live[0]["group"], "title_load_header_fallback")
        self.assertEqual(pending_live[0]["address"], "0x0A3138")
        self.assertNotIn("evidence", pending_live[0])

        evidenced = [row for row in rows if "evidence" in row]
        self.assertEqual(len(evidenced), 74)
        for row in evidenced:
            evidence_path = str(row["evidence"]).split("#", 1)[0]
            self.assertTrue(
                (ROOT / evidence_path).exists(),
                f"missing evidence for {row['address']}: {evidence_path}",
            )

    def test_expanded_discard_ui_is_declared_and_live_verified(self):
        groups = {
            "item_discard_notice_glyph_pointer",
            "item_discard_notice_token_pointer",
            "item_discard_notice_glyphs",
            "item_discard_notice_tokens",
            "shop_item_selection_prompt",
            "item_discard_list_hook",
            "item_discard_list_routine",
            "item_discard_prompt_tokens",
        }
        rows = [
            row
            for row in self.result["declared_patches"]
            if row["group"] in groups
        ]
        self.assertEqual({row["group"] for row in rows}, groups)
        self.assertTrue(all(row["modified"] for row in rows))
        self.assertTrue(all(row["reviewed"] for row in rows))
        self.assertTrue(all(row["live_verified"] for row in rows))

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
                "class-change natural application verification for the "
                "remaining source transitions, plus normal scenario-clear "
                "save persistence beyond Elwin and Hein"
            ],
        )
        self.assertIn(
            "natural magic ownership and application paths beyond the "
            "production-faithful Magic Arrow and Hein Summoner accumulated-"
            "magic proofs; all 22 renderer/application paths are covered by "
            "diagnostic all-magic probes",
            self.result["remaining_inventory_gaps"],
        )
        self.assertFalse(
            any(
                "natural summon ownership" in gap
                for gap in self.result["remaining_inventory_gaps"]
            )
        )
        self.assertIn(
            "ending and credits UI variants outside the verified Scenario 27, "
            "all-epilogue, ending-visit, and final-credit paths",
            self.result["remaining_inventory_gaps"],
        )
        self.assertIn(
            "exact ownership and purpose of 423 compressed resources beyond "
            "SEGA boot-logo resource index 0, byte-font resource index 1, "
            "battle-terrain resource index 223, item-icon resource index 391, "
            "MASAYA publisher-logo resource index 392, and title-logo resource "
            "index 393; broad raw-tile asset families are classified for all 429",
            self.result["remaining_inventory_gaps"],
        )
        self.assertNotIn(
            "all equipment and shop variants beyond declared Scenario 1 paths",
            self.result["remaining_inventory_gaps"],
        )
        self.assertIn(
            "exact ownership of low-signal byte sequences outside the 5,616 reviewed "
            "font/class/sprite/item/name/graphics/system/ending/scenario/text/UI/"
            "compressed-resource/executable-auxiliary/gameplay/renderer/tail candidates: "
            "the one/two-signal scan region-classifies 6,612 candidates, proves "
            "5,615 rows are instruction/bitmap/pointer-boundary/word/graphics/layout/"
            "compressed payload data, and "
            "identifies "
            "retained scenario-level prefix L-; exact ownership of the remaining "
            "996 executable/numeric candidates and base-relative, indexed, or "
            "dynamic access remains open",
            self.result["remaining_inventory_gaps"],
        )


if __name__ == "__main__":
    unittest.main()
