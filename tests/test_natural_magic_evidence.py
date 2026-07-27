from pathlib import Path
import unittest

from tools import build_natural_summon_probe_rom as probe_builder
from tools import verify_natural_magic_evidence as evidence
from tools.class_ability_data import SUMMON_ABILITY_ID, ability_ids_from_runtime_mask
from tools.verify_natural_summon_evidence import read_runtime


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class NaturalMagicEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()

    def test_natural_probe_keeps_magic_ownership_and_mp_branches_stock(self):
        probe = bytearray(KO_ROM.read_bytes())
        probe_builder.patch_probe(probe, self.source)
        evidence.validate_stock_magic_path(probe, self.source)

    def test_retained_gst_proves_natural_list_and_attack_cost(self):
        before = read_runtime(evidence.DEFAULT_BEFORE.read_bytes())
        after = read_runtime(evidence.DEFAULT_AFTER.read_bytes())
        evidence.verify(before, after)
        abilities = ability_ids_from_runtime_mask(before.command_flags)
        self.assertEqual(
            tuple(value for value in abilities if value != SUMMON_ABILITY_ID),
            evidence.NATURAL_MAGIC_IDS,
        )
        self.assertEqual(
            before.current_mp - after.current_mp,
            evidence.ATTACK_MP_COST,
        )


if __name__ == "__main__":
    unittest.main()
