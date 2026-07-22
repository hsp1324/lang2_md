from pathlib import Path
import unittest

from tools import build_magic_application_probe_rom as probe_builder


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class MagicApplicationProbeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()

    def test_source_and_production_keep_stock_branches(self):
        for data in (self.source, self.production):
            self.assertEqual(
                data[
                    probe_builder.ALL_MAGIC_BRANCH_OFFSET :
                    probe_builder.ALL_MAGIC_BRANCH_OFFSET + 4
                ],
                probe_builder.ALL_MAGIC_BRANCH_SOURCE,
            )
            self.assertEqual(
                data[
                    probe_builder.MAGIC_MP_BRANCH_OFFSET :
                    probe_builder.MAGIC_MP_BRANCH_OFFSET + 4
                ],
                probe_builder.MAGIC_MP_BRANCH_SOURCE,
            )

    def test_probe_changes_only_branches_and_checksum(self):
        probe = bytearray(self.production)
        checksum = probe_builder.patch_probe(probe, self.source)
        self.assertEqual(checksum, int.from_bytes(probe[0x18E:0x190], "big"))
        self.assertEqual(
            probe[
                probe_builder.ALL_MAGIC_BRANCH_OFFSET :
                probe_builder.ALL_MAGIC_BRANCH_OFFSET + 4
            ],
            probe_builder.ALL_MAGIC_BRANCH_PATCH,
        )
        self.assertEqual(
            probe[
                probe_builder.MAGIC_MP_BRANCH_OFFSET :
                probe_builder.MAGIC_MP_BRANCH_OFFSET + 4
            ],
            probe_builder.MAGIC_MP_BRANCH_PATCH,
        )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, probe))
            if before != after
        }
        allowed = {
            0x18E,
            0x18F,
            *range(
                probe_builder.ALL_MAGIC_BRANCH_OFFSET,
                probe_builder.ALL_MAGIC_BRANCH_OFFSET + 4,
            ),
            *range(
                probe_builder.MAGIC_MP_BRANCH_OFFSET,
                probe_builder.MAGIC_MP_BRANCH_OFFSET + 4,
            ),
        }
        self.assertLessEqual(changed, allowed)

    def test_source_and_input_mutations_are_rejected(self):
        source = bytearray(self.source)
        source[probe_builder.ALL_MAGIC_BRANCH_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Japanese all-magic"):
            probe_builder.patch_probe(bytearray(self.production), bytes(source))

        probe = bytearray(self.production)
        probe[probe_builder.MAGIC_MP_BRANCH_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "input magic MP"):
            probe_builder.patch_probe(probe, self.source)

    def test_optional_target_reuses_validated_clear_probe(self):
        probe = bytearray(self.production)
        probe_builder.patch_probe(probe, self.source, place_target=True)
        base = probe_builder.clear_probe_builder.BALD_RECORD_OFFSET
        fields = probe_builder.FIELD_OFFSETS
        self.assertEqual(probe[base + fields["x"]], 13)
        self.assertEqual(probe[base + fields["y"]], 19)
        self.assertEqual(probe[base + fields["at"]], 0)
        self.assertEqual(probe[base + fields["df"]], 0)
        mercenaries = base + fields["mercenaries"]
        self.assertEqual(probe[mercenaries : mercenaries + 6], b"\xFF" * 6)

    def test_stock_magic_target_keeps_both_code_branches(self):
        probe = bytearray(self.production)
        checksum = probe_builder.patch_probe(
            probe,
            self.source,
            place_target=True,
            enable_all_magic=False,
        )
        self.assertEqual(checksum, 0x9555)
        self.assertEqual(
            probe[
                probe_builder.ALL_MAGIC_BRANCH_OFFSET :
                probe_builder.ALL_MAGIC_BRANCH_OFFSET + 4
            ],
            probe_builder.ALL_MAGIC_BRANCH_SOURCE,
        )
        self.assertEqual(
            probe[
                probe_builder.MAGIC_MP_BRANCH_OFFSET :
                probe_builder.MAGIC_MP_BRANCH_OFFSET + 4
            ],
            probe_builder.MAGIC_MP_BRANCH_SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
