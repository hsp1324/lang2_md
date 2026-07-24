from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario8_clear_probe_rom as clear_builder
from tools import build_scenario8_status_probe_rom as status_builder
from tools.scenario_data import FIELD_OFFSETS


ROOT = Path(__file__).resolve().parents[1]


class Scenario8StatusProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = bytearray((ROOT / builder.OUT_ROM).read_bytes())
        clear_builder.patch_probe(cls.built, cls.source)
        cls.clear_probe = bytes(cls.built)

    def test_probe_only_relabels_clear_target_and_updates_checksum(self):
        data = bytearray(self.clear_probe)
        status_builder.patch_probe(data, self.source)
        base = status_builder.KRAMER_RECORD_OFFSET
        expected_changes = {
            0x18E,
            0x18F,
            base + FIELD_OFFSETS["name_id"],
            base + FIELD_OFFSETS["class_id"],
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.clear_probe, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_uses_stock_vargas_identity_on_clear_target(self):
        data = bytearray(self.clear_probe)
        status_builder.patch_probe(data, self.source)
        base = status_builder.KRAMER_RECORD_OFFSET
        source_vargas = status_builder.VARGAS_RECORD_OFFSET
        self.assertEqual(
            data[base + FIELD_OFFSETS["name_id"]],
            self.source[source_vargas + FIELD_OFFSETS["name_id"]],
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["class_id"]],
            self.source[source_vargas + FIELD_OFFSETS["class_id"]],
        )
        self.assertEqual(data[base + FIELD_OFFSETS["x"]], 2)
        self.assertEqual(data[base + FIELD_OFFSETS["y"]], 6)
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)

    def test_probe_rejects_changed_vargas_record(self):
        data = bytearray(self.clear_probe)
        data[status_builder.VARGAS_RECORD_OFFSET + 1] ^= 1
        with self.assertRaisesRegex(ValueError, "Vargas record differs"):
            status_builder.patch_probe(data, self.source)

    def test_probe_rejects_changed_clear_target(self):
        data = bytearray(self.clear_probe)
        data[status_builder.KRAMER_RECORD_OFFSET + 1] ^= 1
        with self.assertRaisesRegex(ValueError, "clear probe"):
            status_builder.patch_probe(data, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.clear_probe)
        checksum = status_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(checksum, 0x37A1)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)


if __name__ == "__main__":
    unittest.main()
