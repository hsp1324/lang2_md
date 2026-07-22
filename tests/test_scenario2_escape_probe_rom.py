from pathlib import Path
import unittest

from tools import build_scenario2_escape_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class Scenario2EscapeProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()

    def test_probe_changes_only_liana_y_and_checksum(self):
        data = bytearray(self.production)
        checksum = probe_builder.patch_probe(data, self.source)
        y_offset = probe_builder.LIANA_RECORD_OFFSET + FIELD_OFFSETS["y"]
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertEqual(data[y_offset], probe_builder.PROBE_LIANA_Y)
        self.assertEqual(checksum, int.from_bytes(data[0x18E:0x190], "big"))
        self.assertLessEqual(changed, {y_offset, 0x18E, 0x18F})

    def test_source_and_input_record_mutations_are_rejected(self):
        source = bytearray(self.source)
        source[probe_builder.SCENARIO_HEADER + 0x08] ^= 1
        with self.assertRaisesRegex(ValueError, "deployment table"):
            probe_builder.patch_probe(bytearray(self.production), bytes(source))

        data = bytearray(self.production)
        data[probe_builder.LIANA_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Liana record"):
            probe_builder.patch_probe(data, self.source)


if __name__ == "__main__":
    unittest.main()
