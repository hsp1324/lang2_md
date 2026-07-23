import unittest

from scripts import build_korean_jp_probe as builder


class BaldMapSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = bytearray(builder.IN_ROM.read_bytes())
        cls.patched = bytearray(cls.original)
        builder.expand_rom(cls.patched)
        builder.patch_bald_map_sprite(cls.patched)

    def test_only_bald_class_uses_custom_sprite_id(self) -> None:
        table = builder.GENERIC_CLASS_SPRITE_TABLE
        fighter_2d = builder.be16(self.patched, table + 0x2D * 2)
        bald_2e = builder.be16(self.patched, table + 0x2E * 2)
        self.assertEqual(fighter_2d, builder.BALD_SOURCE_SPRITE_ID)
        self.assertEqual(bald_2e, builder.BALD_CUSTOM_SPRITE_ID)

    def test_custom_frames_are_aligned_and_inside_blank_expansion(self) -> None:
        for target in builder.BALD_CUSTOM_FRAME_OFFSETS:
            self.assertEqual(
                (target - builder.MAP_SPRITE_FRAME_BASES[0])
                % builder.MAP_SPRITE_BYTES,
                0,
            )
            self.assertLessEqual(
                target + builder.MAP_SPRITE_BYTES,
                builder.EXPANDED_ROM_SIZE,
            )
            self.assertEqual(
                bytes(self.original[target : target + builder.MAP_SPRITE_BYTES]),
                b"",
            )

    def test_both_animation_frames_use_the_same_index_remap(self) -> None:
        changed_indexes = set()
        for frame_base, target in zip(
            builder.MAP_SPRITE_FRAME_BASES,
            builder.BALD_CUSTOM_FRAME_OFFSETS,
        ):
            source = (
                frame_base
                + builder.BALD_SOURCE_SPRITE_ID * builder.MAP_SPRITE_BYTES
            )
            source_payload = self.original[
                source : source + builder.MAP_SPRITE_BYTES
            ]
            target_payload = self.patched[
                target : target + builder.MAP_SPRITE_BYTES
            ]
            self.assertEqual(len(target_payload), builder.MAP_SPRITE_BYTES)
            for source_byte, target_byte in zip(source_payload, target_payload):
                for shift in (4, 0):
                    source_index = (source_byte >> shift) & 0x0F
                    target_index = (target_byte >> shift) & 0x0F
                    expected = builder.BALD_SPRITE_COLOR_INDEX_REMAP.get(
                        source_index, source_index
                    )
                    self.assertEqual(target_index, expected)
                    if source_index != target_index:
                        changed_indexes.add(source_index)
        self.assertEqual(
            changed_indexes,
            set(builder.BALD_SPRITE_COLOR_INDEX_REMAP),
        )

    def test_patch_rejects_reuse_of_custom_frame_area(self) -> None:
        data = bytearray(self.original)
        builder.expand_rom(data)
        data[builder.BALD_CUSTOM_FRAME_OFFSETS[0]] = 0
        with self.assertRaisesRegex(ValueError, "is not blank"):
            builder.patch_bald_map_sprite(data)


if __name__ == "__main__":
    unittest.main()
