from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image

from tools import run_scenario14_15_result_parallel as parallel
from tools import run_scenario14_15_result_surface as runner


ROOT = Path(__file__).resolve().parents[1]


class Scenario1415ResultRunnerTests(unittest.TestCase):
    def test_result_and_save_surfaces_are_distinguished(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = Path(temporary) / "result.png"
            save = Path(temporary) / "save.png"
            result_image = Image.new("RGB", (320, 240), (1, 1, 1))
            for point, color in runner.RESULT_POINTS.items():
                result_image.putpixel(point, color)
            result_image.save(result)
            save_image = Image.new("RGB", (320, 240), (1, 1, 1))
            for point, color in runner.SAVE_POINTS.items():
                save_image.putpixel(point, color)
            save_image.save(save)
            self.assertEqual(runner.classify_surface(result), "battle_result")
            self.assertEqual(runner.classify_surface(save), "save_menu")

    def test_completion_moves_use_stock_trigger_directions(self) -> None:
        self.assertEqual(
            runner.SCENARIO_MOVE_DIRECTIONS,
            {14: "up", 15: "down", 16: "up"},
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

    def test_save_menu_wait_retains_the_required_continuation_state_surface(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result = directory / "result.png"
            save = directory / "save.png"
            result_image = Image.new("RGB", (320, 240), (1, 1, 1))
            for point, color in runner.RESULT_POINTS.items():
                result_image.putpixel(point, color)
            result_image.save(result)
            save_image = Image.new("RGB", (320, 240), (1, 1, 1))
            for point, color in runner.SAVE_POINTS.items():
                save_image.putpixel(point, color)
            save_image.save(save)

            class Recorder:
                def __init__(self):
                    self.paths = iter((result, save))
                    self.sent = []

                def capture(self, _path):
                    return next(self.paths)

                def send(self, keys, *, delay):
                    self.sent.append((keys, delay))

            recorder = Recorder()
            with (
                mock.patch.object(runner.time, "sleep"),
                mock.patch.object(runner, "relative", side_effect=lambda path: str(path)),
            ):
                retained, frame, observations = runner.wait_for_save_menu(
                    recorder,
                    max_frames=3,
                    settle_delay=0,
                    button_delay=0.25,
                )

        self.assertEqual(retained, save)
        self.assertEqual(frame, 2)
        self.assertEqual(
            [row["surface"] for row in observations],
            ["battle_result", "save_menu"],
        )
        self.assertEqual(recorder.sent, [(["c"], 0.25)])


if __name__ == "__main__":
    unittest.main()
