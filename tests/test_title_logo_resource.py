import hashlib
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / builder.IN_ROM
KO_ROM = ROOT / builder.OUT_ROM
CURRENT_TILE_SHA256 = "a7dc88edbc9dced635928000be897ea9dff7a680bc9ad736713171b0e577515b"
CURRENT_LAYOUT_SHA256 = "cfbb0598dfa0e0ce9883a0cb3b103c706565eb6782912d30f78e1c0d30d77899"


def decode_layout(record: bytes) -> list[int]:
    cells = []
    cursor = 6
    while cursor < len(record):
        value = record[cursor]
        cursor += 1
        if value == 0xFF:
            break
        if value in (0xF8, 0xF9):
            cursor += 1
        elif value in (0xF7,):
            cells.append(record[cursor])
            cursor += 1
        elif value in (0xFA, 0xFB, 0xFC, 0xFD):
            continue
        elif value == 0xFE:
            count = record[cursor]
            repeated = record[cursor + 1]
            cursor += 2
            cells.extend([repeated] * count)
        else:
            cells.append(value)
    return cells


class TitleLogoResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.jp = JP_ROM.read_bytes()
        cls.en = (ROOT / builder.EN_ROM).read_bytes()
        cls.ko = KO_ROM.read_bytes()

    def test_english_logo_source_is_locked(self) -> None:
        entry = (
            builder.BYTE_UI_FONT_RESOURCE_TABLE
            + builder.TITLE_LOGO_RESOURCE_INDEX * 4
        )
        pointer = builder.be32(self.en, entry) & 0x00FFFFFF
        self.assertEqual(pointer, builder.TITLE_LOGO_ENGLISH_RESOURCE_POINTER)
        self.assertEqual(self.en[pointer], builder.TITLE_LOGO_ENGLISH_RESOURCE_TYPE)
        size = builder.be16(self.en, pointer + 1)
        self.assertEqual(size, builder.TITLE_LOGO_RESOURCE_ORIGINAL_SIZE)
        payload = self.en[pointer + 3 : pointer + 3 + size]
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            builder.TITLE_LOGO_ENGLISH_RESOURCE_SHA256,
        )
        source_layout = self.en[
            builder.TITLE_LOGO_ENGLISH_LAYOUT_RECORD :
            builder.TITLE_LOGO_ENGLISH_LAYOUT_RECORD
            + builder.TITLE_LOGO_ENGLISH_LAYOUT_USED_SIZE
        ]
        self.assertEqual(
            hashlib.sha256(source_layout).hexdigest(),
            builder.TITLE_LOGO_ENGLISH_LAYOUT_SHA256,
        )

    def test_original_logo_resource_and_layout_are_locked(self) -> None:
        entry = (
            builder.BYTE_UI_FONT_RESOURCE_TABLE
            + builder.TITLE_LOGO_RESOURCE_INDEX * 4
        )
        pointer = builder.be32(self.jp, entry) & 0x00FFFFFF
        self.assertEqual(pointer, builder.TITLE_LOGO_RESOURCE_ORIGINAL_POINTER)
        self.assertEqual(self.jp[pointer], 0x03)
        payload = builder.decompress_9dfe(self.jp, pointer + 1)
        self.assertEqual(len(payload), builder.TITLE_LOGO_RESOURCE_ORIGINAL_SIZE)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            builder.TITLE_LOGO_RESOURCE_ORIGINAL_SHA256,
        )
        record = self.jp[
            builder.TITLE_LOGO_LAYOUT_RECORD :
            builder.TITLE_LOGO_LAYOUT_RECORD + builder.TITLE_LOGO_LAYOUT_RECORD_SIZE
        ]
        self.assertEqual(
            hashlib.sha256(record).hexdigest(),
            builder.TITLE_LOGO_LAYOUT_ORIGINAL_SHA256,
        )

    def test_localized_resource_has_fixed_size_and_deterministic_content(self) -> None:
        for table in (
            builder.BYTE_UI_FONT_RESOURCE_TABLE,
            builder.BYTE_UI_EXT_RESOURCE_TABLE,
        ):
            pointer = builder.be32(
                self.ko, table + builder.TITLE_LOGO_RESOURCE_INDEX * 4
            ) & 0x00FFFFFF
            self.assertEqual(pointer, builder.TITLE_LOGO_RESOURCE_RELOC_BASE)
        payload = builder.decompress_9dfe(
            self.ko, builder.TITLE_LOGO_RESOURCE_RELOC_BASE + 1
        )
        self.assertEqual(len(payload), builder.TITLE_LOGO_RESOURCE_ORIGINAL_SIZE)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), CURRENT_TILE_SHA256)

    def test_localized_layout_references_only_visible_logo_tiles(self) -> None:
        record = self.ko[
            builder.TITLE_LOGO_LAYOUT_RECORD :
            builder.TITLE_LOGO_LAYOUT_RECORD + builder.TITLE_LOGO_LAYOUT_RECORD_SIZE
        ]
        self.assertEqual(record[:6], bytes.fromhex("00 01 00 1C 00 08"))
        self.assertEqual(hashlib.sha256(record).hexdigest(), CURRENT_LAYOUT_SHA256)
        cells = decode_layout(record)
        self.assertEqual(
            len(cells),
            builder.TITLE_LOGO_WIDTH_TILES * builder.TITLE_LOGO_HEIGHT_TILES,
        )
        self.assertLess(max(cells), builder.TITLE_LOGO_TILE_COUNT)

        payload = builder.decompress_9dfe(
            self.ko, builder.TITLE_LOGO_RESOURCE_RELOC_BASE + 1
        )
        self.assertEqual(payload[:32], bytes(32))
        for tile_id in set(cells) - {0}:
            tile = payload[tile_id * 32 : (tile_id + 1) * 32]
            self.assertNotEqual(tile, bytes(32))

    def test_adjacent_title_resources_and_layout_tail_are_untouched(self) -> None:
        for index in (392, 394, 395):
            original_pointer = builder.be32(
                self.jp, builder.BYTE_UI_FONT_RESOURCE_TABLE + index * 4
            ) & 0x00FFFFFF
            current_pointer = builder.be32(
                self.ko, builder.BYTE_UI_EXT_RESOURCE_TABLE + index * 4
            ) & 0x00FFFFFF
            self.assertEqual(current_pointer, original_pointer)
        layout_end = (
            builder.TITLE_LOGO_LAYOUT_RECORD + builder.TITLE_LOGO_LAYOUT_RECORD_SIZE
        )
        self.assertEqual(
            self.ko[layout_end : layout_end + 16],
            self.jp[layout_end : layout_end + 16],
        )


if __name__ == "__main__":
    unittest.main()
