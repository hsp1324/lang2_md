from pathlib import Path
import unittest

from tools.item_data import (
    ITEM_COUNT,
    ITEM_EFFECT_TABLE,
    ITEM_PRICE_TABLE,
    ItemEffect,
    ItemRecord,
    patch_items,
    read_item,
    read_items,
    special_behavior,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class ItemDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()

    def test_known_source_item_prices_and_effects(self):
        knife = read_item(self.source, 1)
        self.assertEqual(knife.price_units, 5)
        self.assertEqual(knife.effects[0], ItemEffect(0, 1))

        true_langrisser = read_item(self.source, 9)
        self.assertEqual(
            true_langrisser.effects,
            (
                ItemEffect(0, 9),
                ItemEffect(1, 2),
                ItemEffect(4, 3),
                ItemEffect(5, 1),
            ),
        )

        crown = read_item(self.source, 31)
        self.assertEqual(
            crown.effects[:3],
            (ItemEffect(3, 2), ItemEffect(4, 3), ItemEffect(5, 2)),
        )
        self.assertEqual(special_behavior(26), ("LV10에서 최하위 클래스로 복귀",))

    def test_all_item_records_are_structurally_valid(self):
        records = read_items(self.source)
        self.assertEqual(len(records), ITEM_COUNT)
        self.assertEqual(ITEM_EFFECT_TABLE, 0x060530)
        self.assertEqual(ITEM_PRICE_TABLE, 0x0A1D32)
        self.assertEqual([record.item_id for record in records], list(range(1, 38)))

    def test_patch_round_trip_and_changed_fields_only(self):
        records = list(read_items(self.source))
        records[0] = ItemRecord(
            item_id=1,
            price_units=77,
            effects=(
                ItemEffect(0, 5),
                ItemEffect(1, -2),
                ItemEffect(0xFF, 0),
                ItemEffect(0xFF, 0),
            ),
        )
        patched = bytearray(self.source)
        patch_items(patched, tuple(records))

        self.assertEqual(read_item(patched, 1), records[0])
        changed = {
            index for index, (before, after) in enumerate(zip(self.source, patched))
            if before != after
        }
        expected = {
            ITEM_EFFECT_TABLE + 9,
            ITEM_EFFECT_TABLE + 10,
            ITEM_EFFECT_TABLE + 11,
            ITEM_PRICE_TABLE + 1,
        }
        self.assertEqual(changed, expected)

    def test_rejects_invalid_shape_ids_and_values(self):
        records = list(read_items(self.source))
        with self.assertRaisesRegex(ValueError, "expected 37"):
            patch_items(bytearray(self.source), records[:-1])

        bad = list(records)
        bad[0] = ItemRecord(2, 5, records[0].effects)
        with self.assertRaisesRegex(ValueError, "ordered"):
            patch_items(bytearray(self.source), bad)

        bad = list(records)
        bad[0] = ItemRecord(
            1, 5, (ItemEffect(0, 128),) + records[0].effects[1:]
        )
        with self.assertRaisesRegex(ValueError, "-128..127"):
            patch_items(bytearray(self.source), bad)


if __name__ == "__main__":
    unittest.main()
