import hashlib
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
CURRENT_SHAMAN_INACTIVE_CAPTURE = (
    ROOT / "captures/run/hard_5be8_s03_shaman_inactive_actual.png"
)
CURRENT_SHAMAN_INACTIVE_GST = (
    ROOT / "captures/analysis/hard_5be8_s03_shaman_inactive_actual.gst"
)
CURRENT_SHERRY_SHAMAN_COMMAND_CAPTURE = (
    ROOT / "captures/run/hard_5be8_s05_sherry_shaman_command.png"
)
CURRENT_SHERRY_SHAMAN_INACTIVE_CAPTURE = (
    ROOT / "captures/run/hard_5be8_s05_sherry_shaman_inactive_actual.png"
)
CURRENT_SHERRY_SHAMAN_INACTIVE_GST = (
    ROOT
    / "captures/analysis/hard_5be8_s05_sherry_shaman_inactive_actual.gst"
)
GST_WORK_RAM_OFFSET = 0x2478
GST_VRAM_OFFSET = 0x12478
RUNTIME_GROUP_BASE = 0x603C
RUNTIME_GROUP_SIZE = 0x60
SHERRY_RUNTIME_GROUP = 4
SHAMAN_GRAY_VRAM_OFFSET = 0x9680
SHAMAN_GRAY_BYTES = 0x80
SHAMAN_GRAY_PAYLOAD_SHA256 = (
    "10f15f0c4b9860e2b19cbe717c142b57be31d7bd5fe7bae5dca1e9741b51ea55"
)


class MapSpriteGraySourceRemapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original = builder.IN_ROM.read_bytes()
        cls.patched = bytearray(cls.original)
        builder.expand_rom(cls.patched)
        builder.patch_bald_map_sprite(cls.patched)
        builder.patch_shaman_map_sprite(cls.patched)
        builder.patch_loren_map_sprite(cls.patched)
        builder.patch_paired_npc_map_sprites(cls.patched)
        builder.patch_ai_class_map_sprites(cls.patched)
        cls.expected_masks = builder.custom_map_sprite_gray_masks(
            cls.patched, cls.original
        )
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
        self.assertEqual(len(self.mapping), 144)
        self.assertEqual(
            set(self.mapping),
            set(range(first, last + 1)),
        )

    def test_every_commander_shaman_restores_its_stock_gray_source(self) -> None:
        self.assertEqual(
            set(builder.SHAMAN_COMMANDER_CUSTOM_SPRITE_IDS),
            set(builder.SHAMAN_COMMANDER_SOURCE_SPRITE_IDS),
        )
        for commander_id, custom_sprite_id in (
            builder.SHAMAN_COMMANDER_CUSTOM_SPRITE_IDS.items()
        ):
            with self.subTest(commander_id=commander_id):
                self.assertEqual(
                    self.mapping[custom_sprite_id],
                    builder.SHAMAN_COMMANDER_SOURCE_SPRITE_IDS[commander_id],
                )

    def test_hein_lord_restores_its_stock_gray_source(self) -> None:
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

    def test_mounted_tier_one_aliases_restore_mounted_gray_sources(self) -> None:
        for commander_id, target_class, source_class in (
            (7, 0x01, 0x06),
            (9, 0x01, 0x07),
        ):
            custom_sprite_id = next(
                sprite_id
                for row_commander, row_class, sprite_id in (
                    builder.AI_CLASS_MAP_SPRITE_SPECS
                )
                if (row_commander, row_class)
                == (commander_id, target_class)
            )
            source_record = builder.commander_sprite_record_offset(
                self.original,
                commander_id,
                source_class,
            )
            self.assertEqual(
                self.mapping[custom_sprite_id],
                builder.be16(self.original, source_record + 1),
            )

    def test_current_hard_shaman_inactive_runtime_is_hash_locked(self) -> None:
        self.assertEqual(
            hashlib.sha256(
                CURRENT_SHAMAN_INACTIVE_CAPTURE.read_bytes()
            ).hexdigest(),
            "07be9b8a6dd63b2af53fbdcb732f505df8865ebba33e8bcba57f27bcadcf1de0",
        )
        state = CURRENT_SHAMAN_INACTIVE_GST.read_bytes()
        self.assertEqual(
            hashlib.sha256(state).hexdigest(),
            "a4e6f397730364549c1fb2c63ab51cf686d4274519e524bf55288cc91396eb77",
        )
        start = GST_VRAM_OFFSET + SHAMAN_GRAY_VRAM_OFFSET
        payload = state[start:start + SHAMAN_GRAY_BYTES]
        self.assertEqual(len(payload), SHAMAN_GRAY_BYTES)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            SHAMAN_GRAY_PAYLOAD_SHA256,
        )

    def test_current_hard_sherry_shaman_actual_move_is_hash_locked(self) -> None:
        self.assertEqual(
            hashlib.sha256(
                CURRENT_SHERRY_SHAMAN_COMMAND_CAPTURE.read_bytes()
            ).hexdigest(),
            "bf5199a6690a455b7da5b925db8d081c47e97185a34b15d2eaab5efda8478e08",
        )
        self.assertEqual(
            hashlib.sha256(
                CURRENT_SHERRY_SHAMAN_INACTIVE_CAPTURE.read_bytes()
            ).hexdigest(),
            "7680d7ff90bc9d0944101786552ea1ef1537ad1ae82b5e220f289d0e6d6e9a1e",
        )
        state = CURRENT_SHERRY_SHAMAN_INACTIVE_GST.read_bytes()
        self.assertEqual(
            hashlib.sha256(state).hexdigest(),
            "c739109a1458a281b5c6f7da886042821b5f06ada4f6b31b518e308228753458",
        )
        start = (
            GST_WORK_RAM_OFFSET
            + RUNTIME_GROUP_BASE
            + SHERRY_RUNTIME_GROUP * RUNTIME_GROUP_SIZE
        )
        record = state[start:start + RUNTIME_GROUP_SIZE]
        self.assertEqual(record[0], builder.SHAMAN_CLASS_ID)
        self.assertEqual(record[1], 0x04)
        self.assertEqual(record[2], 0x01)
        self.assertEqual(tuple(record[6:8]), (16, 53))

    def test_custom_mask_table_contains_every_dense_sprite_mask(self) -> None:
        first = min(self.mapping)
        for custom_sprite_id, expected in self.expected_masks.items():
            offset = (
                builder.MAP_SPRITE_GRAY_CUSTOM_MASK_TABLE
                + (custom_sprite_id - first)
                * builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES
            )
            self.assertEqual(
                bytes(
                    self.patched[
                        offset :
                        offset + builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES
                    ]
                ),
                expected,
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
        routine = builder._build_map_sprite_gray_custom_mask_routine(
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
        self.assertIn(
            builder.MAP_SPRITE_GRAY_CUSTOM_MASK_TABLE.to_bytes(4, "big"),
            routine,
        )
        self.assertIn((0x011DE2).to_bytes(4, "big"), routine)

    def test_redesigned_elwin_and_hein_gray_shapes_match_active_sprites(self) -> None:
        for commander_id, class_id in ((1, 0x14), (5, 0x14)):
            custom_sprite_id = next(
                sprite_id
                for candidate_commander, candidate_class, sprite_id in (
                    builder.AI_CLASS_MAP_SPRITE_SPECS
                )
                if (candidate_commander, candidate_class)
                == (commander_id, class_id)
            )
            active_start = (
                builder.MAP_SPRITE_FRAME_BASES[0]
                + custom_sprite_id * builder.MAP_SPRITE_BYTES
            )
            active_pixels = builder._decode_map_sprite_pixels(
                bytes(
                    self.patched[
                        active_start : active_start + builder.MAP_SPRITE_BYTES
                    ]
                )
            )
            mask = self.expected_masks[custom_sprite_id]
            expanded = []
            for offset in range(0, len(mask), 2):
                high_plane, low_plane = mask[offset : offset + 2]
                expanded.extend(
                    2 * ((high_plane >> bit) & 1)
                    + ((low_plane >> bit) & 1)
                    for bit in range(7, -1, -1)
                )
            with self.subTest(commander_id=commander_id):
                self.assertEqual(
                    [value != 0 for value in expanded],
                    [value != 0 for value in active_pixels],
                )

    def test_every_redesigned_custom_gray_shape_matches_its_active_sprite(self) -> None:
        for custom_sprite_id, source_sprite_id in self.mapping.items():
            custom_start = (
                builder.MAP_SPRITE_FRAME_BASES[0]
                + custom_sprite_id * builder.MAP_SPRITE_BYTES
            )
            source_start = (
                builder.MAP_SPRITE_FRAME_BASES[0]
                + source_sprite_id * builder.MAP_SPRITE_BYTES
            )
            stock_mask_start = (
                0x0510C0
                + source_sprite_id
                * builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES
            )
            active_pixels = builder._decode_map_sprite_pixels(
                bytes(
                    self.patched[
                        custom_start : custom_start + builder.MAP_SPRITE_BYTES
                    ]
                )
            )
            source_pixels = builder._decode_map_sprite_pixels(
                bytes(
                    self.original[
                        source_start : source_start + builder.MAP_SPRITE_BYTES
                    ]
                )
            )

            def decode_mask(mask: bytes) -> list[int]:
                return [
                    2 * ((mask[offset] >> bit) & 1)
                    + ((mask[offset + 1] >> bit) & 1)
                    for offset in range(0, len(mask), 2)
                    for bit in range(7, -1, -1)
                ]

            stock_pixels = decode_mask(
                bytes(
                    self.original[
                        stock_mask_start :
                        stock_mask_start
                        + builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES
                    ]
                )
            )
            if (
                [value != 0 for value in active_pixels]
                == [value != 0 for value in source_pixels]
                == [value != 0 for value in stock_pixels]
            ):
                continue
            with self.subTest(custom_sprite_id=f"0x{custom_sprite_id:04X}"):
                self.assertEqual(
                    [value != 0 for value in decode_mask(
                        self.expected_masks[custom_sprite_id]
                    )],
                    [value != 0 for value in active_pixels],
                )

    def test_pure_recolor_keeps_its_hand_authored_stock_gray_mask(self) -> None:
        source_sprite_id = self.mapping[builder.LOREN_CUSTOM_SPRITE_ID]
        start = (
            0x0510C0
            + source_sprite_id * builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES
        )
        self.assertEqual(
            self.expected_masks[builder.LOREN_CUSTOM_SPRITE_ID],
            self.original[
                start : start + builder.MAP_SPRITE_GRAY_SOURCE_MASK_BYTES
            ],
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
        builder.patch_bald_map_sprite(data)
        builder.patch_shaman_map_sprite(data)
        builder.patch_loren_map_sprite(data)
        builder.patch_paired_npc_map_sprites(data)
        builder.patch_ai_class_map_sprites(data)
        data[builder.MAP_SPRITE_GRAY_CUSTOM_MASK_TABLE] = 0
        with self.assertRaisesRegex(ValueError, "table is not blank"):
            builder.patch_map_sprite_gray_source_remap(
                data, self.original
            )


if __name__ == "__main__":
    unittest.main()
