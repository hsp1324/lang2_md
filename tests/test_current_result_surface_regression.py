import json
from pathlib import Path
import unittest

from tools import verify_current_result_surface_regression as verifier


class CurrentResultSurfaceRegressionTests(unittest.TestCase):
    def test_run_partition_covers_every_scenario_once(self) -> None:
        self.assertEqual(
            verifier.EARLY_RUN_18 | verifier.EARLY_RUN_19 | verifier.LATER_SCENARIOS,
            frozenset(verifier.ALL_SCENARIOS),
        )
        self.assertFalse(verifier.EARLY_RUN_18 & verifier.EARLY_RUN_19)
        self.assertFalse(verifier.EARLY_RUN_18 & verifier.LATER_SCENARIOS)
        self.assertFalse(verifier.EARLY_RUN_19 & verifier.LATER_SCENARIOS)
        self.assertEqual(set(verifier.RUN_IDS), set(verifier.ALL_SCENARIOS))
        self.assertEqual(set(verifier.PROBE_ROOTS), set(verifier.ALL_SCENARIOS))
        self.assertEqual(
            verifier.RUN_ID_OVERRIDES,
            {("hard", 27): "current-source-20260802-24"},
        )

    def test_evidence_paths_follow_runner_output_layout(self) -> None:
        root = Path("/tmp/result-evidence")
        self.assertEqual(
            verifier.evidence_path(root, "normal", 1),
            root / "normal/s01/post-darkguard-20260802-18/evidence.json",
        )
        self.assertEqual(
            verifier.evidence_path(root, "hard", 12),
            root / "s12/hard/current-source-20260802-20/evidence.json",
        )
        self.assertEqual(
            verifier.evidence_path(root, "normal", 18),
            root / "normal/s18/current-source-20260802-20/evidence.json",
        )
        self.assertEqual(
            verifier.evidence_path(root, "hard", 27),
            root / "s27/hard/current-source-20260802-24/evidence.json",
        )

    def test_checked_report_covers_both_profiles_and_all_scenarios(self) -> None:
        report_path = verifier.DEFAULT_OUTPUT
        if not report_path.is_file():
            self.skipTest("exact-current cumulative result report is not built yet")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["profile_scenario_runs"], 54)
        self.assertEqual(report["passed_profile_scenario_runs"], 54)
        self.assertEqual(report["scenario_1_to_26_result_runs"], 52)
        self.assertEqual(report["scenario_27_terminal_runs"], 2)
        self.assertEqual(len(report["probe_manifests"]), 3)
        self.assertEqual(
            {(row["profile"], row["scenario"]) for row in report["runs"]},
            {
                (profile, scenario)
                for profile in verifier.PROFILE_NAMES
                for scenario in verifier.ALL_SCENARIOS
            },
        )
        self.assertTrue(all(row["status"] == "pass" for row in report["runs"]))
        for row in report["runs"]:
            if row["scenario"] == 27:
                self.assertEqual(row["terminal_surface"]["surface"], "fin")
                self.assertTrue(row["boss_hp_zero"])
            else:
                self.assertEqual(row["battle_result"]["surface"], "battle_result")

    def test_checked_report_is_reproducible_and_does_not_promote_release(self) -> None:
        report_path = verifier.DEFAULT_OUTPUT
        if not report_path.is_file():
            self.skipTest("exact-current cumulative result report is not built yet")
        checked = json.loads(report_path.read_text(encoding="utf-8"))
        local_inputs = [
            verifier.evidence_path(verifier.DEFAULT_RUNTIME_ROOT, profile, scenario)
            for profile in verifier.PROFILE_NAMES
            for scenario in verifier.ALL_SCENARIOS
        ] + [root / "manifest.json" for root in set(verifier.PROBE_ROOTS.values())]
        if not all(path.is_file() for path in local_inputs):
            self.skipTest("ignored local runtime evidence is unavailable")
        self.assertEqual(checked, verifier.verify(verifier.DEFAULT_RUNTIME_ROOT))
        self.assertEqual(checked["release_gate"]["status"], "complete")
        self.assertFalse(
            checked["release_gate"]["release_or_version_promotion_authorized"]
        )
        self.assertFalse(checked["candidate_roms"]["release_roms_modified"])
        self.assertFalse(checked["candidate_roms"]["version_bumped"])


if __name__ == "__main__":
    unittest.main()
