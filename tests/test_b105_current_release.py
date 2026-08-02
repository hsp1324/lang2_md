from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_b105_current_release as release


ROOT = Path(__file__).resolve().parents[1]


class B105CurrentReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = release.SOURCE_ROM.read_bytes()
        cls.built = release.stamp_release(cls.source)

    def test_only_version_metadata_and_checksum_change(self) -> None:
        changed = {
            offset
            for offset, (before, after) in enumerate(
                zip(self.source, self.built)
            )
            if before != after
        }
        translation = builder.build_title_version_record(
            release.TARGET_TRANSLATION_TITLE
        )
        balance = builder.build_title_version_record(
            release.TARGET_BALANCE_TITLE
        )
        allowed = (
            set(range(0x150, 0x180))
            | set(range(0x18E, 0x190))
            | set(range(
                builder.TITLE_HARD_TRANSLATION_TEXT_RECORD,
                builder.TITLE_HARD_TRANSLATION_TEXT_RECORD + len(translation),
            ))
            | set(range(
                builder.TITLE_HARD_BALANCE_TEXT_RECORD,
                builder.TITLE_HARD_BALANCE_TEXT_RECORD + len(balance),
            ))
        )
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)

    def test_header_and_title_records_are_b105(self) -> None:
        header = self.built[0x150:0x180].decode("ascii").rstrip()
        self.assertEqual(header, release.TARGET_HEADER)
        for offset, text in (
            (
                builder.TITLE_HARD_TRANSLATION_TEXT_RECORD,
                release.TARGET_TRANSLATION_TITLE,
            ),
            (
                builder.TITLE_HARD_BALANCE_TEXT_RECORD,
                release.TARGET_BALANCE_TITLE,
            ),
        ):
            record = builder.build_title_version_record(text)
            self.assertEqual(self.built[offset : offset + len(record)], record)

    def test_save_descriptor_is_unchanged(self) -> None:
        self.assertEqual(self.built[0x1B0:0x1BC], self.source[0x1B0:0x1BC])

    def test_checksum_is_valid(self) -> None:
        stored = int.from_bytes(self.built[0x18E:0x190], "big")
        self.assertEqual(stored, release.md_checksum(self.built))

    def test_b104_sram_is_compatible_and_preserved_by_name_pairing(self) -> None:
        if not release.SOURCE_SRAM.is_file():
            self.skipTest("desktop B1.0.4 SRAM is not present")
        payload = release.SOURCE_SRAM.read_bytes()
        self.assertIn(len(payload), (0x2000, 0x10000))
        if release.DESKTOP_SRAM.is_file():
            self.assertEqual(release.DESKTOP_SRAM.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
