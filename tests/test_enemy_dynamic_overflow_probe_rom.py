import unittest

from tools import build_enemy_dynamic_overflow_probe_rom as probe


class EnemyDynamicOverflowProbeRomTests(unittest.TestCase):
    def make_roms(self):
        size = max(
            probe.VISIBLE_MERCENARY_OFFSET + 1,
            max(probe.SCENARIO_13_LEGACY_RECORDS)
            + probe.MERCENARY_OFFSET
            + probe.MERCENARY_COUNT,
        )
        base = bytearray(size)
        legacy = bytearray(size)
        base[probe.VISIBLE_MERCENARY_OFFSET] = (
            probe.VISIBLE_MERCENARY_EXPECTED_CLASS
        )
        for index, record in enumerate(probe.SCENARIO_13_LEGACY_RECORDS):
            start = record + probe.MERCENARY_OFFSET
            legacy[start : start + probe.MERCENARY_COUNT] = bytes(
                range(0x70 + index, 0x70 + index + probe.MERCENARY_COUNT)
            )
        return base, bytes(legacy)

    def test_copies_legacy_vargas_roster_without_touching_visible_group(self):
        base, legacy = self.make_roms()
        probe.patch_probe(base, legacy)
        self.assertEqual(
            base[probe.VISIBLE_MERCENARY_OFFSET],
            probe.VISIBLE_MERCENARY_EXPECTED_CLASS,
        )
        for record in probe.SCENARIO_13_LEGACY_RECORDS:
            start = record + probe.MERCENARY_OFFSET
            end = start + probe.MERCENARY_COUNT
            self.assertEqual(base[start:end], legacy[start:end])

    def test_optional_visible_darkguard_is_diagnostic_only(self):
        base, legacy = self.make_roms()
        probe.patch_probe(base, legacy, make_darkguard_visible=True)
        self.assertEqual(
            base[probe.VISIBLE_MERCENARY_OFFSET],
            probe.DARK_GUARD_CLASS,
        )

    def test_rejects_unexpected_visible_mercenary_owner(self):
        base, legacy = self.make_roms()
        base[probe.VISIBLE_MERCENARY_OFFSET] = 0x72
        with self.assertRaisesRegex(ValueError, "not Dragonia"):
            probe.patch_probe(base, legacy, make_darkguard_visible=True)


if __name__ == "__main__":
    unittest.main()
