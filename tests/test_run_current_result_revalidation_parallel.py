from __future__ import annotations

import argparse
from pathlib import Path
import unittest

from tools import run_current_result_revalidation_parallel as runner


ROOT = Path(__file__).resolve().parents[1]


class CurrentResultRevalidationParallelTests(unittest.TestCase):
    def args(self) -> argparse.Namespace:
        return argparse.Namespace(
            profiles=["normal", "hard"],
            scenarios=[12, 14, 17, 27],
            workers=4,
            probe_root=ROOT / "tmp/current-source-result-probes-20260802-01",
            seed_gst=ROOT / "captures/analysis/scenario27_preparation_current.gst",
            output_root=ROOT / "captures/run/test-current-result-revalidation",
            runtime_root=ROOT / "tmp/blastem-runtime",
            run_id="unit-test",
        )

    def test_plan_has_one_isolated_task_per_profile_and_scenario(self):
        report = runner.build_plan(self.args())
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["workers"], 4)
        self.assertEqual(len(report["tasks"]), 8)
        self.assertEqual(
            {(row["profile"], row["scenario"]) for row in report["tasks"]},
            {
                (profile, scenario)
                for profile in ("normal", "hard")
                for scenario in (12, 14, 17, 27)
            },
        )

    def test_scenario_specific_output_layouts_do_not_collide(self):
        args = self.args()
        paths = {
            runner.task_output(
                args.output_root,
                profile,
                scenario,
                args.run_id,
            )
            for profile in args.profiles
            for scenario in args.scenarios
        }
        self.assertEqual(len(paths), 8)
        self.assertIn(
            args.output_root / "s12/normal/unit-test",
            paths,
        )
        self.assertIn(
            args.output_root / "normal/s14/unit-test",
            paths,
        )
        self.assertIn(
            args.output_root / "s17/normal/unit-test",
            paths,
        )

    def test_commands_select_the_correct_runner_and_probe(self):
        args = self.args()
        command = runner.task_command(args, "hard", 27, ":600")
        self.assertTrue(command[1].endswith("run_scenario27_ending_surface.py"))
        self.assertIn(
            str(args.probe_root / "hard/s27-ending.md"),
            command,
        )
        self.assertNotIn("--scenario", command)
        command = runner.task_command(args, "normal", 14, ":601")
        self.assertTrue(command[1].endswith("run_scenario14_15_result_surface.py"))
        self.assertEqual(command[-2:], ["--scenario", "14"])
        command = runner.task_command(args, "hard", 16, ":603")
        self.assertTrue(command[1].endswith("run_scenario14_15_result_surface.py"))
        self.assertEqual(command[-2:], ["--scenario", "16"])
        command = runner.task_command(args, "normal", 10, ":602")
        self.assertTrue(command[1].endswith("run_scenario10_result_surface.py"))
        self.assertIn(
            str(args.probe_root / "normal/s10.md"),
            command,
        )
        self.assertNotIn("--scenario", command)
        command = runner.task_command(args, "hard", 12, ":604")
        self.assertTrue(command[1].endswith("run_scenario12_result_surface.py"))
        self.assertIn(
            str(runner.SCENARIO_SEED_OVERRIDES[12]),
            command,
        )
        self.assertNotIn(str(args.seed_gst), command)


if __name__ == "__main__":
    unittest.main()
