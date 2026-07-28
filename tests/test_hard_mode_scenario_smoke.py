import hashlib
import json
import unittest

from tools import hard_mode_plan
from tools import verify_hard_mode_scenario_runtime as scenario_runtime


class HardModeScenarioSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            scenario_runtime.DEFAULT_RESULTS.read_text(encoding="utf-8")
        )
        cls.plan = hard_mode_plan.build_plan()

    def test_manifest_targets_the_current_hard_candidate(self):
        rom = scenario_runtime.DEFAULT_ROM
        self.assertEqual(
            self.manifest["hard_rom"]["sha256"],
            hashlib.sha256(rom.read_bytes()).hexdigest(),
        )

    def test_completed_scenarios_are_sorted_and_unique(self):
        numbers = [row["number"] for row in self.manifest["scenarios"]]
        self.assertEqual(numbers, sorted(set(numbers)))

    def test_completed_scenarios_cover_every_planned_target(self):
        plan_by_number = {
            int(row["number"]): row for row in self.plan["scenarios"]
        }
        for result in self.manifest["scenarios"]:
            scenario = plan_by_number[int(result["number"])]
            indexes = [int(record["index"]) for record in scenario["records"]]
            player_groups = int(result["player_group_count"])
            self.assertEqual(
                result["status"],
                "runtime_loader_smoke_verified",
            )
            self.assertEqual(result["target_record_count"], len(indexes))
            exception_indexes = (
                scenario_runtime.scenario_runtime_exception_indexes(
                    int(result["number"])
                )
            )
            self.assertEqual(
                result.get("runtime_exception_indexes", []),
                exception_indexes,
            )
            self.assertEqual(
                result.get(
                    "strict_runtime_target_record_count",
                    len(indexes),
                ),
                len(indexes) - len(exception_indexes),
            )
            self.assertEqual(
                result["runtime_group_range"],
                [
                    player_groups + min(indexes),
                    player_groups + max(indexes),
                ],
            )


if __name__ == "__main__":
    unittest.main()
