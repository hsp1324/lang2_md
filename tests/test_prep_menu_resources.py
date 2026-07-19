import unittest
from pathlib import Path

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / builder.IN_ROM
KO_ROM = ROOT / builder.OUT_ROM


def read_rows(data: bytes) -> tuple[tuple[int, ...], ...]:
    rows = []
    cursor = builder.PREP_MENU_TOKEN_STREAM
    for _ in range(4):
        rows.append(tuple(builder.be16(data, cursor + index * 2) for index in range(6)))
        cursor += 16
    return tuple(rows)


class PrepMenuResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()

    def test_japanese_rows_match_verified_source(self) -> None:
        self.assertEqual(read_rows(self.jp), builder.PREP_MENU_ORIGINAL_ROWS)

    def test_localized_rows_replace_every_unloaded_blank_tile(self) -> None:
        rows = read_rows(self.ko)
        self.assertNotIn(0x05FC, (token for row in rows for token in row))
        self.assertEqual(rows[0][-2:], (builder.PREP_MENU_LOADED_BLANK_TILE,) * 2)
        self.assertEqual(rows[2][-2:], (builder.PREP_MENU_LOADED_BLANK_TILE,) * 2)
        self.assertEqual(rows[3][-1], builder.PREP_MENU_LOADED_BLANK_TILE)


if __name__ == "__main__":
    unittest.main()
