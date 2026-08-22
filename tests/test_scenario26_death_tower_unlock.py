from __future__ import annotations

import unittest

from scripts import build_korean_jp_probe as builder


class Scenario26DeathTowerUnlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = builder.IN_ROM.read_bytes()

    def expanded_source(self) -> bytearray:
        data = bytearray(self.source)
        builder.expand_rom(data)
        return data

    def test_natural_unlock_changes_only_two_requirement_immediates(self):
        data = self.expanded_source()
        before = bytes(data)

        builder.patch_scenario26_natural_death_tower_unlock(
            data,
            self.source,
        )

        start = builder.SCENARIO26_DEATH_TOWER_REQUIREMENT_ROUTINE
        end = start + len(
            builder.SCENARIO26_DEATH_TOWER_REQUIREMENT_NATURAL
        )
        self.assertEqual(
            data[start:end],
            builder.SCENARIO26_DEATH_TOWER_REQUIREMENT_NATURAL,
        )
        changed = [
            offset
            for offset, (old, new) in enumerate(zip(before, data))
            if old != new
        ]
        self.assertEqual(changed, [0x017391, 0x01739F])

    def test_event_gate_and_challenge_destination_remain_stock(self):
        data = self.expanded_source()
        builder.patch_scenario26_natural_death_tower_unlock(
            data,
            self.source,
        )
        gate = builder.SCENARIO26_DEATH_TOWER_GATE
        gate_end = gate + len(builder.SCENARIO26_DEATH_TOWER_GATE_SOURCE)
        self.assertEqual(
            data[gate:gate_end],
            builder.SCENARIO26_DEATH_TOWER_GATE_SOURCE,
        )
        # The unchanged challenge script still selects scenario index 0x1F
        # (visible Scenario X4 / internal Scenario 31) on acceptance.
        self.assertEqual(data[0x1B23E8:0x1B23EA], bytes.fromhex("14 1F"))

    def test_pure_keeps_stock_requirement_while_normal_and_hard_patch_it(self):
        start = builder.SCENARIO26_DEATH_TOWER_REQUIREMENT_ROUTINE
        end = start + len(builder.SCENARIO26_DEATH_TOWER_REQUIREMENT_SOURCE)
        expected = {
            "pure": builder.SCENARIO26_DEATH_TOWER_REQUIREMENT_SOURCE,
            "normal": builder.SCENARIO26_DEATH_TOWER_REQUIREMENT_NATURAL,
            "hard": builder.SCENARIO26_DEATH_TOWER_REQUIREMENT_NATURAL,
        }
        for profile_name, requirement in expected.items():
            with self.subTest(profile=profile_name):
                data = self.expanded_source()
                builder.patch_profile_user_customizations(
                    data,
                    self.source,
                    profile_name=profile_name,
                )
                self.assertEqual(data[start:end], requirement)

    def test_rejects_changed_requirement_or_event_gate(self):
        changed_requirement = bytearray(self.source)
        changed_requirement[
            builder.SCENARIO26_DEATH_TOWER_REQUIREMENT_ROUTINE
        ] ^= 1
        with self.assertRaisesRegex(ValueError, "requirement changed"):
            builder.patch_scenario26_natural_death_tower_unlock(
                self.expanded_source(),
                bytes(changed_requirement),
            )

        changed_gate = bytearray(self.source)
        changed_gate[builder.SCENARIO26_DEATH_TOWER_GATE] ^= 1
        with self.assertRaisesRegex(ValueError, "event gate changed"):
            builder.patch_scenario26_natural_death_tower_unlock(
                self.expanded_source(),
                bytes(changed_gate),
            )


if __name__ == "__main__":
    unittest.main()
