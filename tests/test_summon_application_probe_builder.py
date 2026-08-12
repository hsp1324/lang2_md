import hashlib
from pathlib import Path
import unittest

from tools import build_summon_application_probe_rom as probe_builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean Normal v1.3.6).md"


class SummonApplicationProbeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()
        assert hashlib.sha256(cls.production).hexdigest() == (
            "b74359800a697eea5e85d7942ac712b74360bbd8b43ff2082b88d009e94a370a"
        )

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
        self.assertEqual(checksum, 0x36A1)
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

    def test_diagnostic_cost_probe_changes_only_one_source_locked_word(self):
        probe = bytearray(self.production)
        checksum = probe_builder.patch_probe(
            probe,
            self.source,
            diagnostic_summon_id=7,
            diagnostic_summon_cost=12,
        )
        offset = (
            probe_builder.SUMMON_DATA_TABLE
            + 7 * probe_builder.SUMMON_DATA_RECORD_SIZE
            + probe_builder.SUMMON_COST_OFFSET
        )
        self.assertEqual(
            self.source[offset : offset + 2],
            (15).to_bytes(2, "big"),
        )
        self.assertEqual(probe[offset : offset + 2], (12).to_bytes(2, "big"))
        self.assertEqual(checksum, int.from_bytes(probe[0x18E:0x190], "big"))
        baseline = bytearray(self.production)
        probe_builder.patch_probe(baseline, self.source)
        changed = {
            index
            for index, (before, after) in enumerate(zip(baseline, probe))
            if before != after
        }
        self.assertLessEqual(changed, {0x18E, 0x18F, offset, offset + 1})

    def test_rejects_invalid_or_partial_diagnostic_cost(self):
        for kwargs in (
            {"diagnostic_summon_id": 7},
            {"diagnostic_summon_cost": 12},
        ):
            with self.assertRaisesRegex(ValueError, "supplied together"):
                probe_builder.patch_probe(
                    bytearray(self.production),
                    self.source,
                    **kwargs,
                )
        for summon_id, cost in ((-1, 12), (8, 12), (7, -1), (7, 100)):
            with self.subTest(summon_id=summon_id, cost=cost):
                with self.assertRaisesRegex(ValueError, "must be"):
                    probe_builder.patch_probe(
                        bytearray(self.production),
                        self.source,
                        diagnostic_summon_id=summon_id,
                        diagnostic_summon_cost=cost,
                    )

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
