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
