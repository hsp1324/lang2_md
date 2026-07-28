import unittest

from scripts import build_korean_jp_probe as builder


class MapSpriteGraySourceRemapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = builder.IN_ROM.read_bytes()
        cls.patched = bytearray(cls.original)
        builder.expand_rom(cls.patched)
        builder.patch_map_sprite_gray_source_remap(
            cls.patched, cls.original
        )
        cls.mapping = builder.custom_map_sprite_gray_source_map(
            cls.original
        )

    def test_all_expansion_backed_map_sprites_are_covered(self) -> None:
        first = min(self.mapping)
        last = max(self.mapping)
        self.assertEqual(first, builder.BALD_CUSTOM_SPRITE_ID)
        self.assertEqual(last, builder.AI_CLASS_MAP_SPRITE_SPECS[-1][2])
        self.assertEqual(len(self.mapping), 53)
        self.assertEqual(
            set(self.mapping),
            set(range(first, last + 1)),
        )

    def test_shaman_and_lord_restore_their_stock_gray_sources(self) -> None:
        hein_shaman = builder.SHAMAN_COMMANDER_CUSTOM_SPRITE_IDS[5]
        self.assertEqual(
            self.mapping[hein_shaman],
            builder.SHAMAN_COMMANDER_SOURCE_SPRITE_IDS[5],
        )

        hein_lord = next(
            custom_sprite_id
            for commander_id, class_id, custom_sprite_id in (
                builder.AI_CLASS_MAP_SPRITE_SPECS
            )
            if commander_id == 5 and class_id == 0x0B
        )
        source_record = builder.commander_sprite_record_offset(
            self.original, 5, 0x0B
        )
        self.assertEqual(
            self.mapping[hein_lord],
            builder.be16(self.original, source_record + 1),
        )

    def test_remap_table_contains_each_stock_silhouette_id(self) -> None:
        first = min(self.mapping)
        for custom_sprite_id, source_sprite_id in self.mapping.items():
            offset = (
                builder.MAP_SPRITE_GRAY_SOURCE_REMAP_TABLE
                + (custom_sprite_id - first) * 2
            )
            self.assertEqual(
                builder.be16(self.patched, offset),
                source_sprite_id,
            )

    def test_gray_source_entry_redirects_to_expansion_routine(self) -> None:
        hook = builder.MAP_SPRITE_GRAY_SOURCE_HOOK
        self.assertEqual(
            bytes(self.patched[hook:hook + 6]),
            bytes.fromhex("4E F9")
            + builder.MAP_SPRITE_GRAY_SOURCE_REMAP_ROUTINE.to_bytes(
                4, "big"
            ),
        )
        routine = builder._build_map_sprite_gray_source_remap_routine(
            min(self.mapping), max(self.mapping)
        )
        start = builder.MAP_SPRITE_GRAY_SOURCE_REMAP_ROUTINE
        self.assertEqual(
            bytes(self.patched[start:start + len(routine)]),
            routine,
        )
        self.assertLessEqual(
            start + len(routine),
            builder.MAP_SPRITE_GRAY_SOURCE_REMAP_ROUTINE_LIMIT,
        )

    def test_unpatched_word_multiply_would_read_unrelated_data(self) -> None:
        custom_sprite_id = builder.SHAMAN_COMMANDER_CUSTOM_SPRITE_IDS[5]
        source_sprite_id = builder.SHAMAN_COMMANDER_SOURCE_SPRITE_IDS[5]
        mask_base = 0x0510C0
        wrapped = mask_base + ((custom_sprite_id << 6) & 0xFFFF)
        expected = mask_base + source_sprite_id * 0x40
        self.assertNotEqual(wrapped, expected)
        self.assertNotEqual(
            self.original[wrapped:wrapped + 0x40],
            self.original[expected:expected + 0x40],
        )

    def test_patch_rejects_occupied_remap_area(self) -> None:
        data = bytearray(self.original)
        builder.expand_rom(data)
        data[builder.MAP_SPRITE_GRAY_SOURCE_REMAP_TABLE] = 0
        with self.assertRaisesRegex(ValueError, "table is not blank"):
            builder.patch_map_sprite_gray_source_remap(
                data, self.original
            )


if __name__ == "__main__":
    unittest.main()
