from pathlib import Path
import hashlib
import unittest

from PIL import ImageFont

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class BattleUiResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = JP_ROM.read_bytes()

    def source_resource(self, data: bytes | bytearray) -> bytes:
        entry = (
            builder.BYTE_UI_FONT_RESOURCE_TABLE
            + builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX * 4
        )
        pointer = builder.be32(data, entry) & 0x00FFFFFF
        return builder.decompress_9dfe(data, pointer + 1)

    def test_source_resource_identity_and_terrain_tiles(self):
        entry = (
            builder.BYTE_UI_FONT_RESOURCE_TABLE
            + builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX * 4
        )
        self.assertEqual(
            builder.be32(self.rom, entry) & 0x00FFFFFF,
            builder.BATTLE_UI_TERRAIN_RESOURCE_ORIGINAL_POINTER,
        )
        source = self.source_resource(self.rom)
        self.assertEqual(
            len(source), builder.BATTLE_UI_TERRAIN_RESOURCE_ORIGINAL_SIZE
        )
        self.assertEqual(
            hashlib.sha256(source).hexdigest(),
            builder.BATTLE_UI_TERRAIN_RESOURCE_ORIGINAL_SHA256,
        )
        self.assertEqual(builder.BATTLE_UI_TERRAIN_LABEL, "지형")
        self.assertEqual(builder.BATTLE_UI_TERRAIN_TILE_IDS, (0x47, 0x48))

    def test_patch_changes_only_the_two_terrain_tiles(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        builder.patch_byte_ui_strings(data)
        source = self.source_resource(self.rom)

        builder.patch_battle_ui_terrain_resource(data)

        original_entry = (
            builder.BYTE_UI_FONT_RESOURCE_TABLE
            + builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX * 4
        )
        extended_entry = (
            builder.BYTE_UI_EXT_RESOURCE_TABLE
            + builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX * 4
        )
        self.assertEqual(
            builder.be32(data, original_entry) & 0x00FFFFFF,
            builder.BATTLE_UI_TERRAIN_RESOURCE_RELOC_BASE,
        )
        self.assertEqual(
            builder.be32(data, extended_entry) & 0x00FFFFFF,
            builder.BATTLE_UI_TERRAIN_RESOURCE_RELOC_BASE,
        )
        localized = self.source_resource(data)
        font = ImageFont.truetype(str(ROOT / "tools/fonts/Galmuri7.ttf"), 8)
        expected = bytearray(source)
        for char, tile_id in zip(
            builder.BATTLE_UI_TERRAIN_LABEL,
            builder.BATTLE_UI_TERRAIN_TILE_IDS,
            strict=True,
        ):
            start = tile_id * 32
            expected[start : start + 32] = builder.render_byte_ui_tile(char, font)
        self.assertEqual(localized, bytes(expected))

    def test_patch_rejects_changed_source_pointer(self):
        data = bytearray(self.rom)
        builder.expand_rom(data)
        builder.patch_byte_ui_strings(data)
        entry = (
            builder.BYTE_UI_FONT_RESOURCE_TABLE
            + builder.BATTLE_UI_TERRAIN_RESOURCE_INDEX * 4
        )
        builder.put32(data, entry, builder.BATTLE_UI_TERRAIN_RESOURCE_ORIGINAL_POINTER + 2)
        with self.assertRaisesRegex(ValueError, "terrain resource pointer changed"):
            builder.patch_battle_ui_terrain_resource(data)


if __name__ == "__main__":
    unittest.main()
