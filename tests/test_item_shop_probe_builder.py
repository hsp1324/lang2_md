from pathlib import Path
import unittest

from tools import build_item_shop_probe_rom as probe_builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class ItemShopProbeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()

    def test_source_all_item_list_contains_every_item_once(self):
        self.assertEqual(
            probe_builder.validate_all_item_list(self.source),
            list(range(1, 38)),
        )

    def test_source_and_production_keep_stock_selector(self):
        offset = probe_builder.SHOP_LIST_SELECTOR_OFFSET
        expected = probe_builder.SHOP_LIST_SELECTOR_SOURCE
        for data in (self.source, self.production):
            self.assertEqual(data[offset : offset + len(expected)], expected)

    def test_probe_changes_only_selector_and_checksum(self):
        probe = bytearray(self.production)
        checksum = probe_builder.patch_probe(probe, self.source)
        self.assertEqual(checksum, int.from_bytes(probe[0x18E:0x190], "big"))
        offset = probe_builder.SHOP_LIST_SELECTOR_OFFSET
        replacement = probe_builder.SHOP_LIST_SELECTOR_PATCH
        self.assertEqual(probe[offset : offset + len(replacement)], replacement)
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, probe))
            if before != after
        }
        allowed = {0x18E, 0x18F, *range(offset, offset + len(replacement))}
        self.assertLessEqual(changed, allowed)

    def test_source_and_input_mutations_are_rejected(self):
        offset = probe_builder.SHOP_LIST_SELECTOR_OFFSET
        source = bytearray(self.source)
        source[offset] ^= 1
        with self.assertRaisesRegex(ValueError, "Japanese shop-list"):
            probe_builder.patch_probe(bytearray(self.production), bytes(source))

        probe = bytearray(self.production)
        probe[offset] ^= 1
        with self.assertRaisesRegex(ValueError, "input shop-list"):
            probe_builder.patch_probe(probe, self.source)

    def test_changed_all_item_table_is_rejected(self):
        source = bytearray(self.source)
        pointer = int.from_bytes(
            source[
                probe_builder.SHOP_LIST_POINTER_TABLE
                + probe_builder.ALL_ITEM_LIST_INDEX * 4 :
                probe_builder.SHOP_LIST_POINTER_TABLE
                + probe_builder.ALL_ITEM_LIST_INDEX * 4
                + 4
            ],
            "big",
        )
        source[pointer + 5] = 0xFF
        with self.assertRaisesRegex(ValueError, "all-item shop list changed"):
            probe_builder.patch_probe(bytearray(self.production), bytes(source))


if __name__ == "__main__":
    unittest.main()
