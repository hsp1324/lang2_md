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


class ShamanMapSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = bytearray(builder.IN_ROM.read_bytes())
        cls.patched = bytearray(cls.original)
        builder.expand_rom(cls.patched)
        builder.patch_shaman_map_sprite(cls.patched)

    def test_only_shaman_0a_uses_the_lavender_custom_sprite(self) -> None:
        table = builder.GENERIC_CLASS_SPRITE_TABLE
        shaman = builder.be16(self.patched, table + 0x0A * 2)
        priest = builder.be16(self.patched, table + 0x9C * 2)
        self.assertEqual(shaman, builder.SHAMAN_CUSTOM_SPRITE_ID)
        self.assertEqual(priest, builder.SHAMAN_SOURCE_SPRITE_ID)
        self.assertNotEqual(shaman, priest)

    def test_commander_shaman_entries_use_character_specific_custom_sprites(
        self,
    ) -> None:
        for commander_id, custom_sprite_id in (
            builder.SHAMAN_COMMANDER_CUSTOM_SPRITE_IDS.items()
        ):
            record = builder.commander_sprite_record_offset(
                self.patched, commander_id, builder.SHAMAN_CLASS_ID
            )
            self.assertEqual(
                builder.be16(self.patched, record + 1),
                custom_sprite_id,
            )

    def test_all_shaman_frames_recolor_only_the_lower_blue_robe_ramp(
        self,
    ) -> None:
        self.assertEqual(
            builder.SHAMAN_SPRITE_COLOR_INDEX_REMAP,
            {0x4: 0xE, 0x5: 0x2, 0xF: 0x3},
        )
        changed_indexes = set()
        protected_blue_pixels = 0
        variants = [
            (
                builder.SHAMAN_SOURCE_SPRITE_ID,
                builder.SHAMAN_CUSTOM_SPRITE_ID,
                builder.SHAMAN_SPRITE_COLOR_INDEX_REMAP,
            ),
            *[
                (
                    source_sprite_id,
                    builder.SHAMAN_COMMANDER_CUSTOM_SPRITE_IDS[
                        commander_id
                    ],
                    builder.SHAMAN_COMMANDER_COLOR_INDEX_REMAPS[
                        commander_id
                    ],
                )
                for commander_id, source_sprite_id in (
                    builder.SHAMAN_COMMANDER_SOURCE_SPRITE_IDS.items()
                )
            ],
        ]
        expected_changed_indexes = set()
        for source_sprite_id, custom_sprite_id, color_index_remap in variants:
            expected_changed_indexes.update(color_index_remap)
            for frame_base in builder.MAP_SPRITE_FRAME_BASES:
                source = (
                    frame_base
                    + source_sprite_id * builder.MAP_SPRITE_BYTES
                )
                target = (
                    frame_base
                    + custom_sprite_id * builder.MAP_SPRITE_BYTES
                )
                source_payload = self.original[
                    source : source + builder.MAP_SPRITE_BYTES
                ]
                target_payload = self.patched[
                    target : target + builder.MAP_SPRITE_BYTES
                ]
                for tile_index in range(4):
                    tile_x = (tile_index // 2) * 8
                    tile_y = (tile_index % 2) * 8
                    tile_offset = tile_index * 32
                    for y in range(8):
                        for pair_x in range(4):
                            offset = tile_offset + y * 4 + pair_x
                            source_byte = source_payload[offset]
                            target_byte = target_payload[offset]
                            for nibble, shift in enumerate((4, 0)):
                                source_index = (
                                    source_byte >> shift
                                ) & 0x0F
                                target_index = (
                                    target_byte >> shift
                                ) & 0x0F
                                expected = source_index
                                x = tile_x + pair_x * 2 + nibble
                                in_robe = (
                                    tile_y + y
                                    >= builder.SHAMAN_ROBE_MIN_Y
                                    and builder.SHAMAN_ROBE_MIN_X
                                    <= x
                                    <= builder.SHAMAN_ROBE_MAX_X
                                )
                                if in_robe:
                                    expected = (
                                        color_index_remap.get(
                                            source_index, source_index
                                        )
                                    )
                                self.assertEqual(target_index, expected)
                                if source_index != target_index:
                                    changed_indexes.add(source_index)
                                if (
                                    not in_robe
                                    and source_index
                                    in color_index_remap
                                ):
                                    protected_blue_pixels += 1
        self.assertEqual(
            changed_indexes,
            expected_changed_indexes,
        )
        self.assertGreater(protected_blue_pixels, 0)

    def test_shaman_custom_frames_use_separate_blank_expansion(self) -> None:
        occupied = set(builder.BALD_CUSTOM_FRAME_OFFSETS)
        occupied.update(builder.LOREN_CUSTOM_FRAME_OFFSETS)
        shaman_targets = set(builder.SHAMAN_CUSTOM_FRAME_OFFSETS)
        for targets in (
            builder.SHAMAN_COMMANDER_CUSTOM_FRAME_OFFSETS.values()
        ):
            shaman_targets.update(targets)
        self.assertTrue(
            shaman_targets.isdisjoint(occupied)
        )
        self.assertEqual(len(shaman_targets), 16)
        for target in shaman_targets:
            self.assertLessEqual(
                target + builder.MAP_SPRITE_BYTES,
                builder.EXPANDED_ROM_SIZE,
            )
            self.assertEqual(
                bytes(
                    self.original[
                        target : target + builder.MAP_SPRITE_BYTES
                    ]
                ),
                b"",
            )

    def test_shaman_patch_rejects_reuse_of_custom_frame_area(self) -> None:
        data = bytearray(self.original)
        builder.expand_rom(data)
        data[builder.SHAMAN_CUSTOM_FRAME_OFFSETS[0]] = 0
        with self.assertRaisesRegex(ValueError, "is not blank"):
            builder.patch_shaman_map_sprite(data)


class LorenMapSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = bytearray(builder.IN_ROM.read_bytes())
        cls.patched = bytearray(cls.original)
        builder.expand_rom(cls.patched)
        builder.patch_bald_map_sprite(cls.patched)
        builder.patch_shaman_map_sprite(cls.patched)
        builder.patch_loren_map_sprite(cls.patched)

    def test_only_loren_9b_uses_the_custom_high_lord_sprite(self) -> None:
        table = builder.GENERIC_CLASS_SPRITE_TABLE
        patched_9b = builder.be16(self.patched, table + 0x9B * 2)
        stock_npc_99 = builder.be16(self.patched, table + 0x99 * 2)
        self.assertEqual(stock_npc_99, builder.LOREN_SOURCE_SPRITE_ID)
        self.assertEqual(patched_9b, builder.LOREN_CUSTOM_SPRITE_ID)
        self.assertNotEqual(patched_9b, stock_npc_99)

    def test_loren_recolors_only_armor_and_preserves_blade(self) -> None:
        self.assertEqual(
            builder.LOREN_SPRITE_COLOR_INDEX_REMAP,
            {0x1: 0x6, 0xE: 0x7},
        )
        self.assertEqual(
            set(builder.LOREN_SPRITE_COLOR_INDEX_REMAP.values()),
            {0x6, 0x7},
        )
        changed_indexes = set()
        for frame_base, target, blade_coords in zip(
            builder.MAP_SPRITE_FRAME_BASES,
            builder.LOREN_CUSTOM_FRAME_OFFSETS,
            builder.LOREN_BLADE_COORDS_BY_FRAME,
        ):
            source = (
                frame_base
                + builder.LOREN_SOURCE_SPRITE_ID
                * builder.MAP_SPRITE_BYTES
            )
            source_payload = self.original[
                source : source + builder.MAP_SPRITE_BYTES
            ]
            target_payload = self.patched[
                target : target + builder.MAP_SPRITE_BYTES
            ]
            for tile_index in range(4):
                tile_x = (tile_index // 2) * 8
                tile_y = (tile_index % 2) * 8
                tile_offset = tile_index * 32
                for y in range(8):
                    for pair_x in range(4):
                        offset = tile_offset + y * 4 + pair_x
                        source_byte = source_payload[offset]
                        target_byte = target_payload[offset]
                        for nibble, shift in enumerate((4, 0)):
                            source_index = (source_byte >> shift) & 0x0F
                            target_index = (target_byte >> shift) & 0x0F
                            coords = (
                                tile_x + pair_x * 2 + nibble,
                                tile_y + y,
                            )
                            expected = (
                                source_index
                                if coords in blade_coords
                                else builder.LOREN_SPRITE_COLOR_INDEX_REMAP.get(
                                    source_index, source_index
                                )
                            )
                            self.assertEqual(target_index, expected)
                            if source_index != target_index:
                                changed_indexes.add(source_index)
                            if coords in blade_coords:
                                self.assertEqual(
                                    target_index, source_index
                                )
        self.assertEqual(
            changed_indexes,
            {
                source_index
                for source_index, target_index in (
                    builder.LOREN_SPRITE_COLOR_INDEX_REMAP.items()
                )
                if source_index != target_index
            },
        )


class PairedNpcMapSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = bytearray(builder.IN_ROM.read_bytes())
        cls.patched = bytearray(cls.original)
        builder.expand_rom(cls.patched)
        builder.patch_bald_map_sprite(cls.patched)
        builder.patch_shaman_map_sprite(cls.patched)
        builder.patch_loren_map_sprite(cls.patched)
        builder.patch_paired_npc_map_sprites(cls.patched)

    def test_each_paired_npc_class_uses_its_own_custom_sprite(self) -> None:
        table = builder.GENERIC_CLASS_SPRITE_TABLE
        custom_ids = set()
        for class_id, spec in builder.PAIRED_NPC_MAP_SPRITES.items():
            actual = builder.be16(self.patched, table + class_id * 2)
            expected = int(spec["custom_sprite_id"])
            self.assertEqual(actual, expected)
            custom_ids.add(actual)
        self.assertEqual(len(custom_ids), len(builder.PAIRED_NPC_MAP_SPRITES))
        self.assertNotIn(builder.LOREN_CUSTOM_SPRITE_ID, custom_ids)
        self.assertNotIn(builder.SHAMAN_CUSTOM_SPRITE_ID, custom_ids)
        self.assertNotIn(builder.BALD_CUSTOM_SPRITE_ID, custom_ids)

    def test_paired_npc_frames_apply_expected_live_palette_indexes(
        self,
    ) -> None:
        for spec in builder.PAIRED_NPC_MAP_SPRITES.values():
            source_sprite_id = int(spec["source_sprite_id"])
            custom_sprite_id = int(spec["custom_sprite_id"])
            remap = dict(spec["color_index_remap"])
            for frame_index, (frame_base, protected_coords) in enumerate(
                zip(
                    builder.MAP_SPRITE_FRAME_BASES,
                    spec["protected_coords"],
                )
            ):
                source = (
                    frame_base
                    + source_sprite_id * builder.MAP_SPRITE_BYTES
                )
                target = (
                    frame_base
                    + custom_sprite_id * builder.MAP_SPRITE_BYTES
                )
                source_payload = self.original[
                    source:source + builder.MAP_SPRITE_BYTES
                ]
                target_payload = self.patched[
                    target:target + builder.MAP_SPRITE_BYTES
                ]
                self.assertEqual(len(target_payload), builder.MAP_SPRITE_BYTES)
                for tile_index in range(4):
                    tile_x = (tile_index // 2) * 8
                    tile_y = (tile_index % 2) * 8
                    tile_offset = tile_index * 32
                    for y in range(8):
                        for pair_x in range(4):
                            offset = tile_offset + y * 4 + pair_x
                            source_byte = source_payload[offset]
                            target_byte = target_payload[offset]
                            for nibble, shift in enumerate((4, 0)):
                                source_index = (source_byte >> shift) & 0x0F
                                target_index = (target_byte >> shift) & 0x0F
                                coords = (
                                    tile_x + pair_x * 2 + nibble,
                                    tile_y + y,
                                )
                                expected = (
                                    source_index
                                    if coords in protected_coords
                                    else remap.get(source_index, source_index)
                                )
                                self.assertEqual(
                                    target_index,
                                    expected,
                                    (
                                        f"{spec['label']} frame {frame_index} "
                                        f"pixel {coords}"
                                    ),
                                )

    def test_paired_palette_roles_match_the_editor_design(self) -> None:
        self.assertEqual(
            builder.PAIRED_NPC_MAP_SPRITES[0x99]["color_index_remap"],
            {0x1: 0x6, 0xE: 0x7},
        )
        self.assertEqual(
            builder.PAIRED_NPC_MAP_SPRITES[0x9A]["color_index_remap"],
            {0x1: 0xF},
        )
        self.assertEqual(
            builder.PAIRED_NPC_MAP_SPRITES[0x9C]["color_index_remap"],
            {0x1: 0x6, 0x4: 0x3, 0x5: 0x6, 0xE: 0x7, 0xF: 0x7},
        )

    def test_all_custom_sprite_frames_use_distinct_blank_slots(self) -> None:
        occupied = {
            *builder.BALD_CUSTOM_FRAME_OFFSETS,
            *builder.LOREN_CUSTOM_FRAME_OFFSETS,
            *builder.SHAMAN_CUSTOM_FRAME_OFFSETS,
        }
        for targets in builder.SHAMAN_COMMANDER_CUSTOM_FRAME_OFFSETS.values():
            occupied.update(targets)
        paired_targets = set()
        for spec in builder.PAIRED_NPC_MAP_SPRITES.values():
            for frame_base in builder.MAP_SPRITE_FRAME_BASES:
                target = (
                    frame_base
                    + int(spec["custom_sprite_id"])
                    * builder.MAP_SPRITE_BYTES
                )
                self.assertNotIn(target, occupied)
                self.assertNotIn(target, paired_targets)
                self.assertLessEqual(
                    target + builder.MAP_SPRITE_BYTES,
                    builder.EXPANDED_ROM_SIZE,
                )
                self.assertEqual(
                    self.original[target:target + builder.MAP_SPRITE_BYTES],
                    b"",
                )
                paired_targets.add(target)


if __name__ == "__main__":
    unittest.main()
