from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_epilogue_probe_rom as probe_builder


ROOT = Path(__file__).resolve().parents[1]


class EpilogueProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()
        cls.records = probe_builder.load_records(
            ROOT / "localization/epilogue_records.json"
        )

    def patched(self, index: int) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source, index, self.records[index])
        return data

    def test_character_slot_mapping_covers_all_record_groups(self):
        self.assertEqual(probe_builder.character_slot_for_record(0), 0)
        self.assertEqual(probe_builder.character_slot_for_record(71), 7)
        self.assertEqual(probe_builder.character_slot_for_record(72), 8)
        self.assertEqual(probe_builder.character_slot_for_record(77), 13)
        self.assertEqual(probe_builder.character_slot_for_record(78), 14)
        self.assertEqual(probe_builder.character_slot_for_record(85), 14)
        self.assertEqual(probe_builder.character_slot_for_record(86), 15)
        self.assertEqual(probe_builder.character_slot_for_record(89), 15)

    def test_normal_group_uses_force_descriptor_and_skips_other_slots(self):
        index = 18
        data = self.patched(index)
        target_slot = probe_builder.character_slot_for_record(index)
        for slot in range(probe_builder.NORMAL_CHARACTER_SLOTS):
            expected = (
                probe_builder.FORCE_DESCRIPTOR
                if slot == target_slot
                else probe_builder.SKIP_DESCRIPTOR
            )
            self.assertEqual(
                probe_builder.be32(
                    data,
                    probe_builder.GROUP_POINTER_TABLE + slot * 4,
                ),
                expected,
            )
        force = probe_builder.FORCE_DESCRIPTOR
        self.assertEqual(builder.be16(data, force + 0), 0x0000)
        self.assertEqual(builder.be16(data, force + 2), 0xFFFF)
        self.assertEqual(builder.be16(data, force + 4), 0x0000)
        self.assertEqual(builder.be16(data, force + 6), 0xFFFF)
        self.assertEqual(
            probe_builder.be32(data, force + 8),
            int(self.records[index]["address"], 16),
        )

    def test_liana_and_world_tables_force_the_selected_record(self):
        for index, table, count in (
            (78, probe_builder.LIANA_POINTER_TABLE, probe_builder.LIANA_RECORD_COUNT),
            (86, probe_builder.WORLD_POINTER_TABLE, probe_builder.WORLD_RECORD_COUNT),
        ):
            data = self.patched(index)
            address = int(self.records[index]["address"], 16)
            self.assertEqual(
                [probe_builder.be32(data, table + item * 4) for item in range(count)],
                [address] * count,
            )
            self.assertEqual(
                {
                    probe_builder.be32(
                        data,
                        probe_builder.GROUP_POINTER_TABLE + slot * 4,
                    )
                    for slot in range(probe_builder.NORMAL_CHARACTER_SLOTS)
                },
                {probe_builder.SKIP_DESCRIPTOR},
            )

    def test_probe_rejects_changed_japanese_source_hash(self):
        source = bytearray(self.source)
        address = int(self.records[0]["address"], 16)
        source[address] ^= 1
        with self.assertRaisesRegex(ValueError, "Japanese source changed"):
            probe_builder.patch_probe(
                bytearray(self.built), bytes(source), 0, self.records[0]
            )

    def test_probe_updates_megadrive_checksum(self):
        data = self.patched(18)
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)


if __name__ == "__main__":
    unittest.main()
