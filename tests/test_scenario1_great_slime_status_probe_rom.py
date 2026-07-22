from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario1_clear_probe_rom as clear_builder
from tools import build_scenario1_great_slime_status_probe_rom as status_builder
from tools.scenario_data import FIELD_OFFSETS


ROOT = Path(__file__).resolve().parents[1]


class Scenario1GreatSlimeStatusProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = bytearray((ROOT / builder.OUT_ROM).read_bytes())
        clear_builder.patch_probe(cls.built, cls.source)
        cls.clear_probe = bytes(cls.built)

    def patched(self) -> bytearray:
        data = bytearray(self.clear_probe)
        status_builder.patch_probe(data, self.source)
        return data

    def test_probe_only_relabels_the_clear_target_and_updates_checksum(self):
        data = self.patched()
        base = clear_builder.BALD_RECORD_OFFSET
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

    def test_probe_uses_source_verified_great_slime_identity(self):
        data = self.patched()
        target = clear_builder.BALD_RECORD_OFFSET
        source_record = status_builder.SOURCE_GREAT_SLIME_RECORD_OFFSET
        for field in ("name_id", "class_id"):
            self.assertEqual(
                data[target + FIELD_OFFSETS[field]],
                self.source[source_record + FIELD_OFFSETS[field]],
            )
        self.assertEqual(
            data[target + FIELD_OFFSETS["name_id"]],
            status_builder.SOURCE_GREAT_SLIME_NAME_ID,
        )
        self.assertEqual(
            data[target + FIELD_OFFSETS["class_id"]],
            status_builder.SOURCE_GREAT_SLIME_CLASS_ID,
        )

    def test_probe_rejects_a_non_clear_target(self):
        data = bytearray(self.clear_probe)
        data[clear_builder.BALD_RECORD_OFFSET + 1] ^= 1
        with self.assertRaisesRegex(ValueError, "clear probe"):
            status_builder.patch_probe(data, self.source)

    def test_probe_rejects_changed_source_identity(self):
        source = bytearray(self.source)
        source[
            status_builder.SOURCE_GREAT_SLIME_RECORD_OFFSET
            + FIELD_OFFSETS["name_id"]
        ] ^= 1
        with self.assertRaisesRegex(ValueError, "Great Slime name ID"):
            status_builder.patch_probe(bytearray(self.clear_probe), source)

    def test_probe_checksum_is_valid(self):
        data = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(expected, 0x7A27)
        self.assertEqual(builder.be16(data, 0x18E), expected)


if __name__ == "__main__":
    unittest.main()
