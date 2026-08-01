import hashlib
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_b104_glyph_lifetime_fix as release


ROOT = Path(__file__).resolve().parents[1]


class B104GlyphLifetimeFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = release.SOURCE_ROM.read_bytes()
        cls.reference = release.PATCH_REFERENCE_ROM.read_bytes()
        cls.output = release.build(cls.source, cls.reference)

    def test_source_and_patch_reference_hash_guards_are_current(self):
        self.assertEqual(
            hashlib.sha256(self.source).hexdigest(),
            release.SOURCE_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(self.reference).hexdigest(),
            release.PATCH_REFERENCE_SHA256,
        )

    def test_every_glyph_fix_range_matches_proven_reference(self):
        for start, end in release.GLYPH_FIX_RANGES:
            with self.subTest(start=f"0x{start:06X}"):
                self.assertEqual(
                    self.output[start:end],
                    self.reference[start:end],
                )

    def test_title_shows_b104_and_translation_stays_101(self):
        header = self.output[0x150:0x180].decode("ascii").rstrip()
        self.assertEqual(header, release.TARGET_HEADER)
        translation = builder.build_title_version_record("번역:1.0.1")
        translation_at = builder.TITLE_HARD_TRANSLATION_TEXT_RECORD
        self.assertEqual(
            self.output[
                translation_at : translation_at + len(translation)
            ],
            translation,
        )
        balance = builder.build_title_version_record("하드:1.0.4")
        balance_at = builder.TITLE_HARD_BALANCE_TEXT_RECORD
        self.assertEqual(
            self.output[balance_at : balance_at + len(balance)],
            balance,
        )

    def test_design_balance_scenario_and_save_bytes_are_preserved(self):
        allowed = (
            release.offsets(release.GLYPH_FIX_RANGES)
            | set(range(0x150, 0x180))
            | set(range(0x18E, 0x190))
            | set(
                range(
                    builder.TITLE_HARD_BALANCE_TEXT_RECORD,
                    builder.TITLE_HARD_BALANCE_TEXT_RECORD
                    + len(builder.build_title_version_record("하드:1.0.4")),
                )
            )
        )
        changed = {
            offset
            for offset, (before, after) in enumerate(
                zip(self.source, self.output)
            )
            if before != after
        }
        self.assertTrue(changed <= allowed)
        for start, end in release.PRESERVED_HARD_BALANCE_RANGES:
            self.assertEqual(self.output[start:end], self.source[start:end])
        self.assertEqual(self.output[0x1B0:0x1BC], self.source[0x1B0:0x1BC])
        self.assertEqual(len(self.output), len(self.source))

    def test_battle_destinations_avoid_all_ordinary_sprite_caches(self):
        battle_tiles = set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        ordinary = (
            set(range(0x0348, 0x0388))
            | set(range(0x0448, 0x0488))
            | set(range(0x03B0, 0x03F0))
        )
        self.assertFalse(battle_tiles & ordinary)
        self.assertFalse(battle_tiles & set(range(0x07A0, 0x07C0)))
        table = builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE
        encoded = b"".join(
            tile.to_bytes(2, "big")
            for tile in builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS
        )
        self.assertEqual(self.output[table : table + len(encoded)], encoded)

    def test_megadrive_checksum_is_valid(self):
        self.assertEqual(
            self.output[0x18E:0x190],
            release.md_checksum(self.output).to_bytes(2, "big"),
        )


if __name__ == "__main__":
    unittest.main()
