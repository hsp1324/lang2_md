from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario9_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario9ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def test_probe_only_changes_laird_combat_fields_coordinates_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.LAIRD_RECORD_OFFSET
        expected_changes = {
            0x18E,
            0x18F,
            base + FIELD_OFFSETS["at"],
            base + FIELD_OFFSETS["df"],
            base + FIELD_OFFSETS["x"],
            base + FIELD_OFFSETS["y"],
            *(base + FIELD_OFFSETS["mercenaries"] + slot for slot in range(6)),
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_every_other_fixed_record(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            if index == probe_builder.LAIRD_RECORD_INDEX:
                continue
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_weakens_and_moves_laird_only(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.LAIRD_RECORD_OFFSET
        self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["x"]], 8)
        self.assertEqual(data[base + FIELD_OFFSETS["y"]], 27)
        self.assertEqual(
            data[base + FIELD_OFFSETS["name_id"]],
            probe_builder.SOURCE_LAIRD_NAME_ID,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["class_id"]],
            probe_builder.SOURCE_LAIRD_CLASS_ID,
        )
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)

    def test_probe_rejects_changed_laird_record(self):
        data = bytearray(self.built)
        data[probe_builder.LAIRD_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Laird record differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(checksum, 0x14EB)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)


if __name__ == "__main__":
    unittest.main()
