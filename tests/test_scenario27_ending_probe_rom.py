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
        self.assertEqual(
            data[base + FIELD_OFFSETS["at"]],
            probe_builder.PROBE_BERNHARDT_AT_MODIFIER & 0xFF,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["df"]],
            probe_builder.PROBE_BERNHARDT_DF_MODIFIER & 0xFF,
        )
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

    def test_balanced_input_allows_only_fields_overwritten_by_probe(self):
        data = bytearray(self.built)
        base = probe_builder.BERNHARDT_RECORD_OFFSET
        data[base + FIELD_OFFSETS["at"]] ^= 0x11
        data[base + FIELD_OFFSETS["df"]] ^= 0x22
        data[base + probe_builder.BALANCE_RECORD_TAG_OFFSET] = 0x42
        data[base + FIELD_OFFSETS["mercenaries"]] = 0x42
        probe_builder.patch_probe(
            data,
            self.source,
            allow_balanced_input=True,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["at"]],
            probe_builder.PROBE_BERNHARDT_AT_MODIFIER & 0xFF,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["df"]],
            probe_builder.PROBE_BERNHARDT_DF_MODIFIER & 0xFF,
        )
        self.assertEqual(
            data[
                base + FIELD_OFFSETS["mercenaries"]:
                base + FIELD_OFFSETS["mercenaries"] + 6
            ],
            b"\xFF" * 6,
        )
        self.assertEqual(
            data[base + probe_builder.BALANCE_RECORD_TAG_OFFSET],
            0x42,
        )

    def test_balanced_input_still_rejects_identity_or_position_changes(self):
        for offset in (
            0,
            FIELD_OFFSETS["name_id"],
            FIELD_OFFSETS["class_id"],
            FIELD_OFFSETS["level"],
            FIELD_OFFSETS["x"],
            FIELD_OFFSETS["y"],
        ):
            data = bytearray(self.built)
            data[probe_builder.BERNHARDT_RECORD_OFFSET + offset] ^= 1
            with self.assertRaisesRegex(ValueError, "protected fields"):
                probe_builder.patch_probe(
                    data,
                    self.source,
                    allow_balanced_input=True,
                )

    def test_probe_updates_megadrive_checksum(self):
        data = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)


if __name__ == "__main__":
    unittest.main()
