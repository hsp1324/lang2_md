from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario27_ending_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS


ROOT = Path(__file__).resolve().parents[1]


class Scenario27EndingProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        return data

    def test_probe_only_changes_verified_bernhardt_fields_and_checksum(self):
        data = self.patched()
        base = probe_builder.BERNHARDT_RECORD_OFFSET
        expected_changes = {
            base + FIELD_OFFSETS["at"],
            base + FIELD_OFFSETS["df"],
            base + FIELD_OFFSETS["y"],
            *(base + FIELD_OFFSETS["mercenaries"] + index for index in range(6)),
            0x18E,
            0x18F,
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)
        self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
        self.assertEqual(
            data[base + FIELD_OFFSETS["x"]], probe_builder.PROBE_BERNHARDT_X
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["y"]], probe_builder.PROBE_BERNHARDT_Y
        )
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)

    def test_probe_rejects_changed_scenario_layout(self):
        data = bytearray(self.built)
        data[probe_builder.BERNHARDT_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Bernhardt record differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_updates_megadrive_checksum(self):
        data = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)


if __name__ == "__main__":
    unittest.main()
