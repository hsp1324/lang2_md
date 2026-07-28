import unittest

from tools import verify_hard_mode_runtime_evidence as verifier


class HardModeRuntimeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = verifier.verify_evidence()
        cls.scenario_twenty_five_groups = (
            verifier.verify_scenario_twenty_five()
        )

    def test_scenario_one_retains_two_hard_targets(self):
        targets = [
            expected
            for expected in verifier.SCENARIO_ONE_GROUPS
            if expected.hard_target
        ]
        self.assertEqual([group.name for group in targets], ["발드", "제국지휘관"])
        self.assertEqual(
            [
                (
                    group.commander_at,
                    group.commander_df,
                    group.soldier_at,
                    group.soldier_df,
                )
                for group in targets
            ],
            [(23, 19, 3, 1), (21, 19, 1, 3)],
        )

    def test_scenario_one_scripted_leon_and_laird_remain_excluded(self):
        excluded = [
            expected
            for expected in verifier.SCENARIO_ONE_GROUPS
            if not expected.hard_target
        ]
        self.assertEqual([group.name for group in excluded], ["레온", "레아드"])
        self.assertEqual(
            [
                (
                    group.commander_at,
                    group.commander_df,
                    group.soldier_at,
                    group.soldier_df,
                )
                for group in excluded
            ],
            [(40, 31, 11, 8), (33, 25, 6, 4)],
        )

    def test_runtime_group_members_match_planned_mercenaries(self):
        self.assertEqual(
            [group.mercenaries for group in self.groups],
            [expected.mercenaries for expected in verifier.SCENARIO_ONE_GROUPS],
        )

    def test_scenario_twenty_five_verifies_all_eleven_hard_targets(self):
        self.assertEqual(len(self.scenario_twenty_five_groups), 11)
        self.assertEqual(
            (
                self.scenario_twenty_five_groups[0].class_id,
                self.scenario_twenty_five_groups[0].name_id,
                self.scenario_twenty_five_groups[0].commander_at,
                self.scenario_twenty_five_groups[0].commander_df,
                self.scenario_twenty_five_groups[0].soldier_at,
                self.scenario_twenty_five_groups[0].soldier_df,
            ),
            (0x4D, 0x0D, 64, 49, 21, 16),
        )
        self.assertEqual(
            (
                self.scenario_twenty_five_groups[-1].class_id,
                self.scenario_twenty_five_groups[-1].name_id,
                self.scenario_twenty_five_groups[-1].commander_at,
                self.scenario_twenty_five_groups[-1].commander_df,
                self.scenario_twenty_five_groups[-1].soldier_at,
                self.scenario_twenty_five_groups[-1].soldier_df,
            ),
            (0x4B, 0x31, 58, 41, 18, 16),
        )

    def test_scenario_twenty_five_uses_full_planned_mercenary_rosters(self):
        self.assertEqual(
            self.scenario_twenty_five_groups[0].mercenaries,
            (0x7B,) * 6,
        )
        self.assertEqual(
            self.scenario_twenty_five_groups[3].mercenaries,
            (0x7C,) * 6,
        )
        self.assertEqual(
            self.scenario_twenty_five_groups[-1].mercenaries,
            (0x7D,) * 6,
        )


if __name__ == "__main__":
    unittest.main()
