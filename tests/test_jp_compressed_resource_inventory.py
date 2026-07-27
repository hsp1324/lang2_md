import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.jp_compressed_resource_inventory import (
    DYNAMIC_LOAD_CALL_OWNERS,
    decompress_type1,
    decompress_type2,
    direct_load_calls,
    inventory,
    markdown_report,
    resource_encoded_end,
    resource_output_size,
    resource_pointers,
    verify_source_locks,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
INVENTORY_JSON = ROOT / "localization/compressed_resources.json"
INVENTORY_MARKDOWN = ROOT / "docs/compressed_resource_inventory.md"


class CompressedResourceInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()
        cls.result = inventory(cls.japanese, cls.korean)

    def test_table_boundary_and_count(self):
        pointers = resource_pointers(self.japanese)
        self.assertEqual(len(pointers), 429)
        self.assertEqual(pointers[0], 0x0B06B4)
        self.assertEqual(pointers[-1], 0x13807E)

    def test_encoded_stream_boundaries_are_inside_pointer_allocations(self):
        pointers = resource_pointers(self.japanese)
        encoded_ends = [
            resource_encoded_end(self.japanese, pointer)
            for pointer in pointers
        ]
        allocation_ends = [*pointers[1:], 0x180000]
        self.assertEqual(encoded_ends[-1], 0x138152)
        self.assertTrue(
            all(
                pointer < encoded_end <= allocation_end
                for pointer, encoded_end, allocation_end in zip(
                    pointers, encoded_ends, allocation_ends
                )
            )
        )
        padding = b"".join(
            self.japanese[encoded_end:allocation_end]
            for encoded_end, allocation_end in zip(
                encoded_ends, allocation_ends
            )
        )
        self.assertEqual(len(padding), 294720)
        self.assertEqual(padding.count(0x00), 146)
        self.assertEqual(padding.count(0xFF), 294574)

    def test_checked_in_reports_match_current_rom(self):
        stored = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
        self.assertEqual(stored, self.result)
        self.assertEqual(
            INVENTORY_MARKDOWN.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )

    def test_all_output_sizes_and_decoding_match(self):
        self.assertEqual(self.result["entry_count"], 429)
        self.assertEqual(self.result["type_counts"], {"1": 2, "2": 248, "3": 179})
        self.assertEqual(self.result["decoded_counts"], {"1": 2, "2": 248, "3": 179})
        self.assertEqual(self.result["total_original_output_bytes"], 903296)
        self.assertTrue(
            all(entry["original_output_size"] > 0 for entry in self.result["entries"])
        )
        self.assertTrue(
            all(
                (entry["original_decoded_sha256"] is not None)
                is True
                for entry in self.result["entries"]
            )
        )

    def test_raw_tile_asset_families_and_source_traced_owners_cover_the_table(self):
        self.assertEqual(
            self.result["asset_family_counts"],
            {
                "platform_logo": 1,
                "ui_font": 1,
                "map_tileset": 24,
                "battle_background": 21,
                "combat_sprite": 176,
                "battle_ui": 1,
                "battle_scene_graphics": 7,
                "character_portrait": 132,
                "small_graphic_fragment": 27,
                "world_map_graphics": 1,
                "item_icon_graphics": 1,
                "publisher_logo": 1,
                "title_logo_graphics": 1,
                "opening_ending_graphics": 35,
            },
        )
        self.assertEqual(self.result["raw_tile_visual_reviewed_count"], 429)
        self.assertEqual(self.result["raw_tile_text_signal_count"], 5)
        self.assertEqual(
            {
                entry["index"]: entry["raw_tile_text_signal"]
                for entry in self.result["entries"]
                if entry["raw_tile_text_signal"] is not None
            },
            {
                0: "platform_brand_lettering",
                1: "font_glyphs",
                223: "battle_ui_label_tiles",
                392: "publisher_brand_lettering",
                393: "title_lettering",
            },
        )
        self.assertEqual(self.result["entries"][2]["asset_family"], "map_tileset")
        self.assertEqual(self.result["entries"][46]["asset_family"], "battle_background")
        self.assertEqual(self.result["entries"][47]["asset_family"], "combat_sprite")
        self.assertEqual(
            self.result["entries"][231]["asset_family"], "character_portrait"
        )
        self.assertEqual(
            self.result["entries"][428]["asset_family"], "opening_ending_graphics"
        )
        self.assertEqual(self.result["known_owner_count"], 429)
        self.assertEqual(self.result["unknown_owner_count"], 0)
        self.assertEqual(self.result["source_traced_owner_count"], 421)
        self.assertEqual(self.result["live_verified_owner_count"], 6)
        self.assertEqual(self.result["unreferenced_candidate_count"], 2)
        self.assertEqual(self.result["ownership_record_count"], 763)
        self.assertTrue(
            all(entry["structurally_verified"] for entry in self.result["entries"])
        )

    def test_type1_rle_and_type2_plane_decoder(self):
        pointers = resource_pointers(self.japanese)
        type1 = [index for index, pointer in enumerate(pointers) if self.japanese[pointer] == 1]
        self.assertEqual(type1, [389, 411])
        self.assertEqual([len(decompress_type1(self.japanese, pointers[index])) for index in type1], [384, 224])
        type2_sizes = [
            resource_output_size(self.japanese, pointer)
            for pointer in pointers
            if self.japanese[pointer] == 2
        ]
        self.assertEqual(len(type2_sizes), 248)
        self.assertEqual(sum(type2_sizes), 306272)
        sample = decompress_type2(self.japanese, pointers[29])
        self.assertEqual(len(sample), 3776)
        self.assertEqual(
            self.result["entries"][29]["original_decoded_sha256"],
            "fde977cddd80d58997844e812050c13a9d965d94f97265ec1a5d23d9d98d08bf",
        )

    def test_owned_localized_resources_are_relocated_and_modified(self):
        self.assertEqual(self.result["modified_count"], 3)
        self.assertEqual(self.result["known_owner_count"], 429)
        self.assertEqual(self.result["unknown_owner_count"], 0)
        entry = self.result["entries"][builder.BYTE_UI_FONT_RESOURCE_INDEX]
        self.assertEqual(entry["owner"], "byte_ui_font")
        self.assertEqual(entry["original_pointer"], "0x0B0A84")
        self.assertEqual(entry["current_pointer"], "0x290000")
        self.assertEqual(entry["original_type"], 3)
        self.assertEqual(entry["current_type"], 3)
        self.assertEqual(entry["original_output_size"], 8192)
        self.assertEqual(entry["current_output_size"], 8192)
        self.assertTrue(entry["pointer_modified"])
        self.assertTrue(entry["content_modified"])

        terrain = self.result["entries"][builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX]
        self.assertEqual(terrain["owner"], "battle_ui_terrain")
        self.assertEqual(terrain["original_pointer"], "0x0FEB2A")
        self.assertEqual(terrain["current_pointer"], "0x2E2000")
        self.assertEqual(terrain["original_output_size"], 2368)
        self.assertEqual(terrain["current_output_size"], 2368)
        self.assertTrue(terrain["pointer_modified"])
        self.assertTrue(terrain["content_modified"])
        self.assertTrue(terrain["reviewed"])
        self.assertTrue(terrain["live_verified"])

        logo = self.result["entries"][builder.TITLE_LOGO_RESOURCE_INDEX]
        self.assertEqual(logo["owner"], "title_logo")
        self.assertEqual(logo["original_pointer"], "0x120EEE")
        self.assertEqual(logo["current_pointer"], "0x2E0000")
        self.assertEqual(logo["original_output_size"], 5984)
        self.assertEqual(logo["current_output_size"], 5984)
        self.assertTrue(logo["pointer_modified"])
        self.assertTrue(logo["content_modified"])
        self.assertTrue(logo["reviewed"])
        self.assertTrue(logo["live_verified"])

    def test_stock_boot_brand_graphics_have_exact_live_owners(self):
        sega = self.result["entries"][0]
        self.assertEqual(sega["owner"], "sega_boot_logo")
        self.assertEqual(sega["asset_family"], "platform_logo")
        self.assertTrue(sega["reviewed"])
        self.assertTrue(sega["live_verified"])

        masaya = self.result["entries"][392]
        self.assertEqual(masaya["owner"], "masaya_publisher_logo")
        self.assertEqual(masaya["asset_family"], "publisher_logo")
        self.assertTrue(masaya["reviewed"])
        self.assertTrue(masaya["live_verified"])

    def test_item_icon_resource_owner_matches_the_stock_loader(self):
        entry = self.result["entries"][391]
        self.assertEqual(entry["owner"], "item_icons")
        self.assertEqual(entry["original_pointer"], "0x11FAE4")
        self.assertEqual(entry["original_type"], 3)
        self.assertEqual(entry["original_output_size"], 8192)
        self.assertFalse(entry["modified"])
        self.assertTrue(entry["reviewed"])
        self.assertTrue(entry["live_verified"])
        self.assertEqual(
            entry["direct_immediate_calls"],
            [
                {
                    "call_site": "0x025E62",
                    "immediate_resource": True,
                    "resource_index": 391,
                    "raw_resource_id": "0x8187",
                    "high_bit_flag": True,
                    "destination": "0x4000",
                }
            ],
        )

    def test_direct_loader_calls_are_mapped_without_guessing_dynamic_ids(self):
        calls = direct_load_calls(self.japanese)
        self.assertEqual(len(calls), 75)
        self.assertEqual(sum(call["immediate_resource"] for call in calls), 64)
        self.assertEqual(self.result["dynamic_load_call_count"], 11)
        self.assertEqual(
            self.result["dynamic_load_call_owners"],
            {
                f"0x{call_site:06X}": owner
                for call_site, owner in DYNAMIC_LOAD_CALL_OWNERS.items()
            },
        )
        self.assertEqual(self.result["immediate_referenced_resource_count"], 50)
        font_calls = self.result["entries"][builder.BYTE_UI_FONT_RESOURCE_INDEX][
            "direct_immediate_calls"
        ]
        self.assertEqual(len(font_calls), 6)
        self.assertTrue(all(call["high_bit_flag"] for call in font_calls))

    def test_source_locked_selector_tables_reject_drift(self):
        locks = verify_source_locks(self.japanese)
        self.assertEqual(len(locks), 16)
        self.assertEqual(
            locks["scenario_map_resource_table"]["sha256"],
            "fac42d9dffaca3143d0eb37deace4cf63df6b3f6cd0df868f1dd744eeccc5387",
        )
        changed = bytearray(self.japanese)
        changed[0x061C34] ^= 1
        with self.assertRaisesRegex(
            ValueError, "source lock scenario_map_resource_table changed"
        ):
            verify_source_locks(bytes(changed))

    def test_map_background_and_battle_graphics_have_exact_producers(self):
        unreferenced_map = self.result["entries"][2]
        self.assertEqual(
            unreferenced_map["owner"], "unreferenced_map_graphic_candidate"
        )
        self.assertEqual(unreferenced_map["owner_status"], "unreferenced_candidate")
        self.assertEqual(
            unreferenced_map["ownership_records"][0]["status"],
            "no_reference_found",
        )

        map_resource = self.result["entries"][3]
        self.assertEqual(map_resource["owner"], "scenario_map_tileset")
        self.assertEqual(map_resource["ownership_record_count"], 18)
        self.assertEqual(
            {row["scenario"] for row in map_resource["ownership_records"]},
            {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 18, 21, 24, 25},
        )

        background = self.result["entries"][45]
        self.assertEqual(background["owner"], "battle_background_selector")
        self.assertEqual(background["ownership_records"][0]["selector"], 19)

        shared = self.result["entries"][46]
        self.assertEqual(shared["owner"], "shared_battle_scene_tiles")
        self.assertEqual(shared["ownership_records"][0]["call_site"], "0x01C5F6")

        unreferenced_battle = self.result["entries"][224]
        self.assertEqual(
            unreferenced_battle["owner"],
            "unreferenced_battle_graphic_candidate",
        )
        self.assertEqual(
            unreferenced_battle["owner_status"], "unreferenced_candidate"
        )

        variant = self.result["entries"][228]
        self.assertEqual(variant["owner"], "battle_scene_layout_variant")
        self.assertEqual(
            variant["ownership_records"][0]["condition"], "battle_mode == 4"
        )
        self.assertEqual(
            variant["ownership_records"][0]["loader_calls"][0]["call_site"],
            "0x01E144",
        )

    def test_all_combat_sprite_resources_map_to_classes_or_commanders(self):
        for index in range(47, 223):
            rows = self.result["entries"][index]["ownership_records"]
            self.assertTrue(
                any(
                    row["owner"]
                    in {"generic_combat_sprite", "commander_combat_sprite"}
                    for row in rows
                ),
                index,
            )

        generic = self.result["entries"][47]["ownership_records"][0]
        self.assertEqual(generic["owner"], "generic_combat_sprite")
        self.assertEqual(generic["class_id"], 0x62)
        self.assertEqual(generic["class_ko"], "파이크")

        shared = self.result["entries"][154]
        self.assertTrue(
            any(row["owner"] == "generic_combat_sprite" for row in shared["ownership_records"])
        )
        self.assertTrue(
            any(
                row["owner"] == "commander_combat_sprite"
                and row["commander_name"] == "엘윈"
                for row in shared["ownership_records"]
            )
        )

        final_override = self.result["entries"][222]["ownership_records"][0]
        self.assertEqual(final_override["owner"], "commander_combat_sprite")
        self.assertEqual(final_override["commander_name"], "레스터")
        self.assertEqual(final_override["class_id"], 0x1C)

    def test_portrait_route_and_opening_ending_tables_cover_their_ranges(self):
        for index in range(231, 363):
            self.assertEqual(self.result["entries"][index]["owner"], "character_portrait")
        self.assertEqual(
            self.result["entries"][231]["ownership_records"][0][
                "dynamic_loader_calls"
            ],
            ["0x01B3F2", "0x01CC90", "0x021B8A"],
        )
        self.assertEqual(
            self.result["entries"][362]["ownership_records"][0]["lookup_value"],
            132,
        )

        for index in range(363, 388):
            self.assertEqual(self.result["entries"][index]["owner"], "route_map_fragment")
        self.assertEqual(
            [
                row["route_position"]
                for row in self.result["entries"][387]["ownership_records"]
            ],
            [26, 27, 31],
        )

        for index in range(394, 429):
            self.assertTrue(
                self.result["entries"][index]["owner"].startswith(
                    ("title_screen_group_", "opening_ending_scene_group_")
                )
            )
            self.assertGreater(
                self.result["entries"][index]["direct_immediate_call_count"], 0
            )
        self.assertEqual(
            self.result["entries"][428]["owner"],
            "opening_ending_scene_group_02F17E",
        )


if __name__ == "__main__":
    unittest.main()
