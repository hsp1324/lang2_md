import hashlib
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_b103_vram_collision_fix as release


ROOT = Path(__file__).resolve().parents[1]


class B103VramCollisionFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = release.SOURCE_ROM.read_bytes()
        cls.output = release.build(cls.source)

    def test_builder_and_release_use_safe_ballista_slot(self) -> None:
        self.assertEqual(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS[release.SLOT], 0x07F0)
        self.assertEqual(
            builder.be16(
                self.output,
                builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + release.SLOT * 2,
            ),
            release.NEW_TILE,
        )
        self.assertEqual(
            builder.be32(
                self.output,
                builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + release.SLOT * 4,
            ),
            release.vdp_write_command(release.NEW_TILE),
        )

    def test_title_and_header_show_b103_without_changing_translation_version(self) -> None:
        header = self.output[0x150:0x180].decode("ascii").rstrip()
        self.assertEqual(header, release.TARGET_HEADER)
        translation = builder.build_title_version_record("번역:1.0.1")
        self.assertEqual(
            self.output[
                builder.TITLE_HARD_TRANSLATION_TEXT_RECORD:
                builder.TITLE_HARD_TRANSLATION_TEXT_RECORD + len(translation)
            ],
            translation,
        )
        balance = builder.build_title_version_record("하드:1.0.3")
        self.assertEqual(
            self.output[
                builder.TITLE_HARD_BALANCE_TEXT_RECORD:
                builder.TITLE_HARD_BALANCE_TEXT_RECORD + len(balance)
            ],
            balance,
        )

    def test_only_declared_bytes_change(self) -> None:
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.source, self.output))
            if before != after
        }
        command = builder.BYTE_UI_DYNAMIC_VDP_COMMAND_TABLE + release.SLOT * 4
        tile = builder.BYTE_UI_DYNAMIC_TILE_ID_TABLE + release.SLOT * 2
        title = builder.TITLE_HARD_BALANCE_TEXT_RECORD
        allowed = (
            set(range(0x150, 0x180))
            | set(range(0x18E, 0x190))
            | set(range(command, command + 4))
            | set(range(tile, tile + 2))
            | set(range(title, title + len(builder.build_title_version_record("하드:1.0.3"))))
        )
        self.assertTrue(changed <= allowed)
        self.assertEqual(len(self.output), len(self.source))

    def test_megadrive_checksum_is_valid(self) -> None:
        checksum = sum(
            int.from_bytes(self.output[offset:offset + 2], "big")
            for offset in range(0x200, len(self.output), 2)
        ) & 0xFFFF
        self.assertEqual(self.output[0x18E:0x190], checksum.to_bytes(2, "big"))

    def test_source_hash_guard_is_current(self) -> None:
        self.assertEqual(hashlib.sha256(self.source).hexdigest(), release.SOURCE_SHA256)


if __name__ == "__main__":
    unittest.main()
