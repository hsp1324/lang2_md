import unittest

from tools import verify_hard_mode_runtime_evidence as verifier


class HardModeRuntimeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = verifier.verify_evidence()

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


if __name__ == "__main__":
    unittest.main()
