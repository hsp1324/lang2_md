from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario5_escape_probe_rom as probe_builder
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario5EscapeProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def test_probe_only_changes_first_deployment_y_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        expected_changes = {
            0x18E,
            0x18F,
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 2,
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 3,
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_scenario_layout_and_all_fixed_records(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        source_layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        probe_layout = scenario_layout(data, probe_builder.SCENARIO_NUMBER)
        self.assertEqual(probe_layout, source_layout)
        start = source_layout.records_offset
        end = start + source_layout.record_count * FIXED_RECORD_SIZE
        self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_moves_only_elwin_to_north_threshold(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(
            data[start : start + 4],
            bytes.fromhex(
                f"{probe_builder.SOURCE_FIRST_PLAYER_X:04X} "
                f"{probe_builder.PROBE_FIRST_PLAYER_Y:04X}"
            ),
        )

    def test_probe_rejects_changed_deployment_or_fixed_record(self):
        changed_deployment = bytearray(self.built)
        changed_deployment[probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "first player deployment"):
            probe_builder.patch_probe(changed_deployment, self.source)

        changed_record = bytearray(self.built)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        changed_record[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed records differ"):
            probe_builder.patch_probe(changed_record, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)


if __name__ == "__main__":
    unittest.main()
