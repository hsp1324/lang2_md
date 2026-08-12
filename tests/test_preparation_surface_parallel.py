from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from tools import run_preparation_surface_parallel as parallel


ROOT = Path(__file__).resolve().parents[1]


class PreparationSurfaceParallelTests(unittest.TestCase):
    def test_scenario_parser_accepts_ranges_and_deduplicates(self) -> None:
        self.assertEqual(parallel.parse_scenarios("1-3,2,7,11-12"), [1, 2, 3, 7, 11, 12])

    def test_scenario_parser_rejects_reverse_and_out_of_range(self) -> None:
        with self.assertRaisesRegex(Exception, "backwards"):
            parallel.parse_scenarios("4-2")
        with self.assertRaisesRegex(Exception, "scenario must be"):
            parallel.parse_scenarios("32")

    def test_plan_assigns_distinct_isolated_displays(self) -> None:
        rom = ROOT / (
            "roms/builds/"
            "Langrisser II (Korean Hard v1.3.7).md"
        )
        output = subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "tools/run_preparation_surface_parallel.py"),
                "plan",
                "--profile", "hard",
                "--rom", str(rom),
                "--scenarios", "1-8",
                "--workers", "4",
                "--attempts", "3",
                "--display-base", "130",
                "--run-id", "parallel-plan-test",
            ],
            cwd=ROOT,
            text=True,
        )
        self.assertIn('"displays": [', output)
        self.assertIn('"attempts": 3', output)
        for display in (":130", ":131", ":132", ":133"):
            self.assertIn(f'"{display}"', output)

    def test_xvfb_launcher_rejects_physical_or_ambiguous_displays(self) -> None:
        for display in (":0", ":1", ":99", ":104.0", "localhost:104"):
            with self.subTest(display=display):
                with self.assertRaises(ValueError):
                    parallel.display_number(display)
        self.assertEqual(parallel.display_number(":100"), 100)

    def test_xvfb_process_is_never_spawned_before_display_validation(self) -> None:
        with mock.patch.object(parallel.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(ValueError, "possibly physical"):
                parallel.start_xvfb(Path("/tmp/Xvfb"), Path("/tmp/lib"), ":0")
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
