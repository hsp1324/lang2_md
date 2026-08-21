from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import generate_byte_ui_slot_inventory as inventory_builder


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "localization/byte_ui_slot_inventory.json"


class ByteUiSlotInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.inventory = inventory_builder.build_inventory(cls.source)

    def test_checked_in_inventory_is_current(self):
        expected = inventory_builder.json.dumps(
            self.inventory,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
        self.assertEqual(INVENTORY.read_text(encoding="utf-8"), expected)

    def test_every_local_index_and_extension_tile_is_unique(self):
        indexes = self.inventory["local_indexes"]
        self.assertEqual(len(indexes), 174)
        self.assertEqual(
            len({entry["local_index"] for entry in indexes}),
            len(indexes),
        )
        self.assertEqual(
            len({entry["vram_tile"] for entry in indexes}),
            len(indexes),
        )
        extension = self.inventory["extension_slots"]
        self.assertEqual(len(extension), 118)
        self.assertEqual(
            len({entry["vram_tile"] for entry in extension}),
            len(extension),
        )

    def test_retired_tiles_carry_explicit_runtime_hazard_reasons(self):
        retired = {
            entry["vram_tile"]: (entry["char"], entry["reason"])
            for entry in self.inventory["extension_slots"]
            if entry["status"] == "retired_unsafe"
        }
        self.assertEqual(
            set(retired),
            {"0x039C", "0x03A9", "0x0443", "0x0444", "0x0499", "0x049A"},
        )
        self.assertEqual(retired["0x039C"][0], "비")
        self.assertIn("battle animation", retired["0x039C"][1])
        self.assertEqual(retired["0x03A9"][0], "린")
        self.assertIn("magic-miss", retired["0x03A9"][1])

    def test_heavy_horseman_uses_battle_stable_bi_tile(self):
        by_char = {
            entry["char"]: entry
            for entry in self.inventory["local_indexes"]
        }
        self.assertEqual(by_char["비"]["vram_tile"], "0x05F5")
        self.assertEqual(by_char["비"]["allocation"], "battle_stable")
        self.assertEqual(by_char["적"]["vram_tile"], "0x00A6")
        self.assertEqual(by_char["적"]["allocation"], "dynamic_scratch")

    def test_magic_miss_keeps_its_two_original_font_tiles(self):
        by_char = {
            entry["char"]: entry
            for entry in self.inventory["local_indexes"]
        }
        self.assertEqual(by_char["프"]["byte_code"], "0xF7")
        self.assertEqual(by_char["프"]["vram_tile"], "0x03F7")
        self.assertEqual(by_char["린"]["byte_code"], "0xF8")
        self.assertEqual(by_char["린"]["vram_tile"], "0x03F8")


if __name__ == "__main__":
    unittest.main()
