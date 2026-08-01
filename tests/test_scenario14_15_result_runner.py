from pathlib import Path
import unittest

from tools import run_scenario14_15_result_parallel as parallel
from tools import run_scenario14_15_result_surface as runner


ROOT = Path(__file__).resolve().parents[1]


class Scenario1415ResultRunnerTests(unittest.TestCase):
    def test_result_and_save_surfaces_are_distinguished(self) -> None:
        result = (
            ROOT
            / "captures/run/current_s14_s15_result/"
            "hard/s15/battle/battle_result.png"
        )
        save = (
            ROOT
            / "captures/run/current_s14_s15_result/"
            "normal/s14/battle/clear_path_120.png"
        )
        self.assertEqual(runner.classify_surface(result), "battle_result")
        self.assertEqual(runner.classify_surface(save), "save_menu")

    def test_completion_moves_use_stock_trigger_directions(self) -> None:
        self.assertEqual(
            runner.SCENARIO_MOVE_DIRECTIONS,
            {14: "up", 15: "down"},
        )

    def test_parallel_task_roms_are_profile_and_scenario_specific(self) -> None:
        root = ROOT / "tmp/current-result-probes"
        self.assertEqual(
            parallel.task_rom(root, "normal", 14),
            root / "normal/s14.md",
        )
        self.assertEqual(
            parallel.task_rom(root, "hard", 15),
            root / "hard/s15.md",
        )


if __name__ == "__main__":
    unittest.main()
