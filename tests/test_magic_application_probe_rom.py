from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_magic_application_probe_rom as probe_builder
from tools.class_hire_data import CLASS_RECORD_SIZE, CLASS_RECORD_TABLE


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
NORMAL_ROM = ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.9).md"


class MagicApplicationProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NORMAL_ROM.is_file():
            raise unittest.SkipTest("current Normal verification ROM is absent")
        cls.source = JP_ROM.read_bytes()
        cls.normal = NORMAL_ROM.read_bytes()

    def test_resistance_override_is_diagnostic_and_checksum_valid(self):
        data = bytearray(self.normal)
        offset = (
            CLASS_RECORD_TABLE
            + probe_builder.BALD_CLASS_ID * CLASS_RECORD_SIZE
            + probe_builder.CLASS_MAGIC_RESISTANCE_OFFSET
        )
        original = data[offset]
        checksum = probe_builder.patch_probe(
            data,
            self.source,
            enable_all_magic=False,
            target_magic_resistance=255,
        )
        self.assertNotEqual(original, 255)
        self.assertEqual(data[offset], 255)
        self.assertEqual(checksum, builder.be16(data, 0x18E))

    def test_resistance_override_rejects_out_of_range_values(self):
        for value in (-1, 256):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "0..255"):
                    probe_builder.patch_probe(
                        bytearray(self.normal),
                        self.source,
                        enable_all_magic=False,
                        target_magic_resistance=value,
                    )
