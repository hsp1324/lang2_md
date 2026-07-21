from pathlib import Path
import unittest

from tools import build_summon_application_probe_rom as probe_builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class SummonApplicationProbeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()

    def test_source_and_production_keep_stock_branches(self):
        for data in (self.source, self.production):
            for offset, expected in (
                (
                    probe_builder.SUMMON_COMMAND_BRANCH_OFFSET,
                    probe_builder.SUMMON_COMMAND_BRANCH_SOURCE,
                ),
                (
                    probe_builder.ALL_SUMMON_BRANCH_OFFSET,
                    probe_builder.ALL_SUMMON_BRANCH_SOURCE,
                ),
                (
                    probe_builder.SUMMON_MP_BRANCH_OFFSET,
                    probe_builder.SUMMON_MP_BRANCH_SOURCE,
                ),
            ):
                self.assertEqual(data[offset : offset + len(expected)], expected)

    def test_probe_changes_only_three_branches_and_checksum(self):
        probe = bytearray(self.production)
        checksum = probe_builder.patch_probe(probe, self.source)
        self.assertEqual(checksum, int.from_bytes(probe[0x18E:0x190], "big"))
        self.assertEqual(checksum, 0xADF2)
        allowed = {0x18E, 0x18F}
        for offset, replacement in (
            (
                probe_builder.SUMMON_COMMAND_BRANCH_OFFSET,
                probe_builder.SUMMON_COMMAND_BRANCH_PATCH,
            ),
            (
                probe_builder.ALL_SUMMON_BRANCH_OFFSET,
                probe_builder.ALL_SUMMON_BRANCH_PATCH,
            ),
            (
                probe_builder.SUMMON_MP_BRANCH_OFFSET,
                probe_builder.SUMMON_MP_BRANCH_PATCH,
            ),
        ):
            self.assertEqual(probe[offset : offset + len(replacement)], replacement)
            allowed.update(range(offset, offset + len(replacement)))
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, probe))
            if before != after
        }
        self.assertLessEqual(changed, allowed)

    def test_source_and_input_mutations_are_rejected(self):
        source = bytearray(self.source)
        source[probe_builder.ALL_SUMMON_BRANCH_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Japanese all-summon"):
            probe_builder.patch_probe(bytearray(self.production), bytes(source))

        probe = bytearray(self.production)
        probe[probe_builder.SUMMON_MP_BRANCH_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "input summon MP"):
            probe_builder.patch_probe(probe, self.source)


if __name__ == "__main__":
    unittest.main()
