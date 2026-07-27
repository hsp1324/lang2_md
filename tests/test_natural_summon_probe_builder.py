from pathlib import Path
import unittest

from tools import build_class_change_probe_rom as class_probe
from tools import build_item_shop_probe_rom as shop_probe
from tools import build_natural_summon_probe_rom as probe_builder
from tools import verify_natural_summon_evidence as evidence


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class NaturalSummonProbeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()

    def test_probe_changes_only_level_trigger_shop_selector_and_checksum(self):
        probe = bytearray(self.production)
        checksum = probe_builder.patch_probe(probe, self.source)
        wrapper = class_probe.PROBE_WRAPPER
        code = class_probe.wrapper_code(
            runtime_record_index=probe_builder.HEIN_RUNTIME_RECORD,
            expected_class=probe_builder.SUMMONER_CLASS,
            probe_level=probe_builder.SUMMONER_PROBE_LEVEL,
            probe_experience=class_probe.class_change_experience(
                self.source,
                probe_builder.SUMMONER_CLASS,
            ),
        )
        allowed = set(range(0x18E, 0x190))
        allowed.update(
            range(
                class_probe.END_TURN_LEVEL_UP_ENTRY_OPERAND,
                class_probe.END_TURN_LEVEL_UP_ENTRY_OPERAND + 4,
            )
        )
        allowed.update(range(wrapper, wrapper + len(code)))
        allowed.update(
            range(
                shop_probe.SHOP_LIST_SELECTOR_OFFSET,
                shop_probe.SHOP_LIST_SELECTOR_OFFSET
                + len(shop_probe.SHOP_LIST_SELECTOR_PATCH),
            )
        )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, probe))
            if before != after
        }
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual(probe[0x18E:0x190], checksum.to_bytes(2, "big"))

    def test_stock_summon_gates_and_costs_remain_source_identical(self):
        probe = bytearray(self.production)
        probe_builder.patch_probe(probe, self.source)
        for offset, size in probe_builder.source_locked_summon_regions():
            with self.subTest(offset=f"0x{offset:06X}"):
                self.assertEqual(
                    probe[offset : offset + size],
                    self.source[offset : offset + size],
                )

    def test_retained_gst_proves_natural_bit_cost_and_spawn(self):
        before = evidence.read_runtime(evidence.DEFAULT_BEFORE.read_bytes())
        after = evidence.read_runtime(evidence.DEFAULT_AFTER.read_bytes())
        evidence.verify(before, after)
        self.assertEqual(before.current_mp - after.current_mp, 15)
        self.assertEqual(after.equipment[0], evidence.IRON_DUMBBELL_ITEM_ID)
        self.assertEqual(after.summoned_class, evidence.BROTHER_CLASS)


if __name__ == "__main__":
    unittest.main()
