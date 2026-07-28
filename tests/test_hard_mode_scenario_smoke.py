import json
from pathlib import Path
import unittest

from tools import hard_mode_plan
from tools import verify_hard_mode_scenario_runtime as scenario_runtime


ROOT = Path(__file__).resolve().parents[1]


class HardModeScenarioSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(
            scenario_runtime.DEFAULT_RESULTS.read_text(encoding="utf-8")
        )
        cls.plan = hard_mode_plan.build_plan()

    def test_runtime_evidence_reaches_current_candidate_through_owned_deltas(
        self,
    ):
        promoted = json.loads(
            (ROOT / "localization/ai_class_release_delta.json").read_text(
                encoding="utf-8"
            )
        )
        current = json.loads(
            (ROOT / "localization/hard_mode_candidate_delta.json").read_text(
                encoding="utf-8"
            )
        )
        build = json.loads(
            (ROOT / "localization/hard_mode_build.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            self.manifest["hard_rom"]["sha256"],
            promoted["before"]["sha256"],
        )
        self.assertEqual(
            promoted["after"]["sha256"],
            current["before"]["sha256"],
        )
        self.assertEqual(
            current["after"]["sha256"],
            build["hard"]["sha256"],
        )
        self.assertEqual(
            promoted["delta"]["balance_event_ai_changed_bytes"],
            0,
        )
        self.assertEqual(
            current["delta"]["balance_event_ai_changed_bytes"],
            0,
        )

    def test_completed_scenarios_are_sorted_and_unique(self):
        numbers = [row["number"] for row in self.manifest["scenarios"]]
        self.assertEqual(numbers, sorted(set(numbers)))

    def test_smoke_and_deep_evidence_cover_all_scenarios(self):
        self.assertEqual(
            self.manifest["status"],
            "all_scenarios_runtime_loaded",
        )
        coverage = self.manifest["coverage"]
        self.assertEqual(coverage["scenario_count"], 31)
        self.assertEqual(
            coverage["verified_scenarios"],
            list(range(1, 32)),
        )
        self.assertEqual(coverage["missing_scenarios"], [])
        self.assertEqual(
            coverage["deep_evidence_scenarios"],
            [1, 16, 25, 27],
        )

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
