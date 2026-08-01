from pathlib import Path
import subprocess
import sys
import unittest

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
        rom = ROOT / "roms/releases/Langrisser II (Korean Hard T1.0.1 B1.0.3).md"
        output = subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "tools/run_preparation_surface_parallel.py"),
                "plan",
                "--profile", "hard",
                "--rom", str(rom),
                "--scenarios", "1-8",
                "--workers", "4",
                "--display-base", "130",
                "--run-id", "parallel-plan-test",
            ],
            cwd=ROOT,
            text=True,
        )
        self.assertIn('"displays": [', output)
        for display in (":130", ":131", ":132", ":133"):
            self.assertIn(f'"{display}"', output)


if __name__ == "__main__":
    unittest.main()
