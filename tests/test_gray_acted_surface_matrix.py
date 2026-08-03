import argparse
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools import run_gray_acted_surface_matrix as gray


ROOT = Path(__file__).resolve().parents[1]


class GrayActedSurfaceMatrixTests(unittest.TestCase):
    def test_direction_parser_preserves_retry_order(self) -> None:
        self.assertEqual(
            gray.parse_directions("down,right,left,up"),
            ["down", "right", "left", "up"],
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            gray.parse_directions("down,down")
        with self.assertRaises(argparse.ArgumentTypeError):
            gray.parse_directions("diagonal")

    def test_scenario_12_experiment_proves_real_move_and_stock_gray_payload(self) -> None:
        root = (
            ROOT
            / "captures/run/gray_acted_surface_experiment/normal/s12/path02"
        )
        after = gray.runtime_group_zero(root / "states/acted_gray.gst")
        state = gray.load_gst(root / "states/acted_gray.gst")
        _, _, expected = gray.expected_gray_payload()
        payload = state.vram[
            gray.GRAY_VRAM_START : gray.GRAY_VRAM_START + gray.GRAY_VRAM_BYTES
        ]
        self.assertEqual(after["acted_flag"], 1)
        self.assertEqual((after["x"], after["y"]), (15, 24))
        self.assertEqual(payload, expected)

    def test_parallel_plan_is_machine_readable(self) -> None:
        output = subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "tools/run_gray_acted_surface_parallel.py"),
                "plan",
                "--profile", "normal",
                "--rom", str(ROOT / "tmp/current-preparation-b103-common-normal.md"),
                "--scenarios", "12-14",
                "--workers", "2",
                "--display-base", "150",
                "--run-id", "unit-plan",
            ],
            cwd=ROOT,
            text=True,
        )
        plan = json.loads(output)
        self.assertEqual(plan["scenarios"], [12, 13, 14])
        self.assertEqual(plan["displays"], [":150", ":151"])
        self.assertEqual(plan["directions"], ["down", "right", "left", "up"])


if __name__ == "__main__":
    unittest.main()
