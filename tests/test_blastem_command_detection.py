from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

from PIL import Image

from tools import run_blastem_sequence as runner


REAL_TITLE_SCREEN_VISIBLE = runner.title_screen_visible


class BlastemCommandDetectionTests(unittest.TestCase):
    def setUp(self):
        title_patcher = mock.patch.object(
            runner,
            "title_screen_visible",
            return_value=False,
        )
        title_patcher.start()
        self.addCleanup(title_patcher.stop)

    def args(self) -> SimpleNamespace:
        return SimpleNamespace(
            capture_prefix=Path("captures/run/detect.png"),
            click_window=False,
            confirmation_delay=0.1,
            hold=0.08,
            max_confirmations=3,
            send_event=True,
            xlib_capture=True,
        )

    def test_short_dialogue_line_is_detected(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "short-dialogue.png"
            image = Image.new("RGB", (320, 240), (87, 146, 255))
            pixels = image.load()
            for y in range(98, 171):
                for x in range(20, 300):
                    pixels[x, y] = (0, 0, 119)
            for y in range(112, 120):
                for x in range(30, 60):
                    pixels[x, y] = (255, 255, 255)
            image.save(path)

            self.assertTrue(runner.battle_dialogue_visible(path))

    def test_blank_dialogue_box_is_not_detected(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "blank-dialogue.png"
            image = Image.new("RGB", (320, 240), (87, 146, 255))
            pixels = image.load()
            for y in range(98, 171):
                for x in range(20, 300):
                    pixels[x, y] = (0, 0, 119)
            image.save(path)

            self.assertFalse(runner.battle_dialogue_visible(path))

    def test_battle_map_status_bar_is_detected(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "battle-map.png"
            image = Image.new("RGB", (320, 240), (48, 128, 48))
            pixels = image.load()
            for y in range(195, 235):
                for x in range(320):
                    pixels[x, y] = (0, 0, 119) if x % 40 < 22 else (0, 0, 0)
            for y in range(195, 235):
                for x in range(0, 320, 10):
                    pixels[x, y] = (160, 112, 32)
            image.save(path)

            self.assertTrue(runner.battle_map_surface_visible(path))

    def test_crowded_secret_scenario_status_bar_is_detected(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "secret-battle-map.png"
            image = Image.new("RGB", (320, 240), (48, 128, 48))
            pixels = image.load()
            for y in range(195, 235):
                for x in range(320):
                    pixels[x, y] = (
                        (0, 0, 119) if x % 20 < 10 else (0, 0, 0)
                    )
            for y in range(195, 235):
                for x in range(0, 320, 10):
                    pixels[x, y] = (160, 112, 32)
            image.save(path)

            self.assertTrue(runner.battle_map_surface_visible(path))

    @mock.patch.object(runner.time, "sleep")
    @mock.patch.object(runner.subprocess, "call")
    @mock.patch.object(runner, "battle_dialogue_visible")
    @mock.patch.object(runner, "battle_command_menu_visible")
    @mock.patch.object(runner, "game_over_visible", return_value=False)
    @mock.patch.object(runner, "capture_window")
    def test_current_command_menu_is_detected_before_sending_confirmation(
        self,
        capture_window,
        game_over_visible,
        battle_command_menu_visible,
        battle_dialogue_visible,
        subprocess_call,
        sleep,
    ):
        battle_command_menu_visible.side_effect = (True, True)

        self.assertEqual(runner.advance_to_battle_command(self.args()), 0)

        subprocess_call.assert_not_called()
        battle_dialogue_visible.assert_not_called()
        self.assertEqual(capture_window.call_count, 2)

    @mock.patch.object(runner.time, "sleep")
    @mock.patch.object(runner, "wait_for_dialogue_stability")
    @mock.patch.object(runner.subprocess, "call", return_value=0)
    @mock.patch.object(runner, "battle_dialogue_visible", return_value=True)
    @mock.patch.object(runner, "battle_command_menu_visible")
    @mock.patch.object(runner, "game_over_visible", return_value=False)
    @mock.patch.object(runner, "capture_window")
    def test_dialogue_is_captured_before_first_confirmation(
        self,
        capture_window,
        game_over_visible,
        battle_command_menu_visible,
        battle_dialogue_visible,
        subprocess_call,
        wait_for_dialogue_stability,
        sleep,
    ):
        battle_command_menu_visible.side_effect = (False, True, True)

        self.assertEqual(runner.advance_to_battle_command(self.args()), 0)

        subprocess_call.assert_called_once()
        first_capture = capture_window.call_args_list[0].args[0]
        self.assertEqual(first_capture.name, "detect_00.png")
        self.assertEqual(capture_window.call_count, 3)
        wait_for_dialogue_stability.assert_called_once()

    @mock.patch.object(runner.time, "sleep")
    @mock.patch.object(runner, "capture_window")
    def test_dialogue_waits_for_two_identical_complete_text_captures(
        self,
        capture_window,
        sleep,
    ):
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            frame = directory / "dialogue.png"
            partial = Image.new("RGB", (320, 240), (87, 146, 255))
            complete = partial.copy()
            for image, text_width in ((partial, 36), (complete, 92)):
                pixels = image.load()
                for y in range(98, 171):
                    for x in range(20, 300):
                        pixels[x, y] = (0, 0, 119)
                for y in range(112, 120):
                    for x in range(30, 30 + text_width):
                        pixels[x, y] = (255, 255, 255)
            partial.save(frame)
            complete_path = directory / "complete.png"
            complete.save(complete_path)

            def capture_complete(path, *, xlib_only=False):
                Image.open(complete_path).save(path)

            capture_window.side_effect = capture_complete

            runner.wait_for_dialogue_stability(self.args(), frame)

            self.assertEqual(capture_window.call_count, 3)
            self.assertEqual(sleep.call_count, 3)
            self.assertEqual(
                runner.dialogue_text_fingerprint(frame),
                runner.dialogue_text_fingerprint(complete_path),
            )

    @mock.patch.object(
        runner,
        "battle_dialogue_visible",
        return_value=False,
    )
    @mock.patch.object(runner, "capture_window")
    @mock.patch.object(runner.time, "sleep")
    def test_auto_closing_panel_does_not_request_confirmation(
        self,
        sleep,
        capture_window,
        battle_dialogue_visible,
    ):
        with TemporaryDirectory() as temporary_directory:
            frame = Path(temporary_directory) / "panel.png"
            Image.new("RGB", (320, 240), (0, 0, 119)).save(frame)

            self.assertFalse(
                runner.wait_for_dialogue_stability(self.args(), frame)
            )

            capture_window.assert_called_once()
            battle_dialogue_visible.assert_called_once_with(frame)

    @mock.patch.object(runner.subprocess, "call")
    @mock.patch.object(runner, "battle_dialogue_visible")
    @mock.patch.object(runner, "battle_command_menu_visible")
    @mock.patch.object(runner, "game_over_visible", return_value=True)
    @mock.patch.object(runner, "capture_window")
    def test_current_game_over_is_detected_before_sending_confirmation(
        self,
        capture_window,
        game_over_visible,
        battle_command_menu_visible,
        battle_dialogue_visible,
        subprocess_call,
    ):
        self.assertEqual(runner.advance_to_battle_command(self.args()), 2)

        subprocess_call.assert_not_called()
        battle_dialogue_visible.assert_not_called()
        battle_command_menu_visible.assert_not_called()
        capture_window.assert_called_once()

    def test_stable_title_screen_is_detected(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "title.png"
            image = Image.new("RGB", (320, 240), (0, 0, 96))
            pixels = image.load()
            for y in range(165, 174):
                for x in range(90, 230):
                    if x % 5 < 2:
                        pixels[x, y] = (255, 255, 255)
            image.save(path)

            self.assertTrue(REAL_TITLE_SCREEN_VISIBLE(path))

    @mock.patch.object(runner.subprocess, "call")
    @mock.patch.object(runner, "title_screen_visible", return_value=True)
    @mock.patch.object(runner, "game_over_visible", return_value=False)
    @mock.patch.object(runner, "capture_window")
    def test_title_return_is_reported_separately_from_game_over(
        self,
        capture_window,
        game_over_visible,
        title_screen_visible,
        subprocess_call,
    ):
        self.assertEqual(runner.advance_to_battle_command(self.args()), 3)

        subprocess_call.assert_not_called()
        capture_window.assert_called_once()

    @mock.patch.object(runner.time, "sleep")
    @mock.patch.object(runner.subprocess, "call")
    @mock.patch.object(runner, "battle_dialogue_visible", return_value=False)
    @mock.patch.object(runner, "battle_command_menu_visible")
    @mock.patch.object(runner, "game_over_visible", return_value=False)
    @mock.patch.object(runner, "capture_window")
    def test_non_dialogue_transition_waits_without_sending_confirmation(
        self,
        capture_window,
        game_over_visible,
        battle_command_menu_visible,
        battle_dialogue_visible,
        subprocess_call,
        sleep,
    ):
        battle_command_menu_visible.side_effect = (False, True, True)

        self.assertEqual(runner.advance_to_battle_command(self.args()), 0)

        subprocess_call.assert_not_called()
        sleep.assert_called()

    @mock.patch.object(runner.time, "sleep")
    @mock.patch.object(runner, "battle_map_surface_visible", return_value=True)
    @mock.patch.object(runner.subprocess, "call", return_value=0)
    @mock.patch.object(runner, "battle_dialogue_visible", return_value=False)
    @mock.patch.object(runner, "battle_command_menu_visible")
    @mock.patch.object(runner, "game_over_visible", return_value=False)
    @mock.patch.object(runner, "capture_window")
    def test_fresh_battle_opens_command_menu_from_map_surface(
        self,
        capture_window,
        game_over_visible,
        battle_command_menu_visible,
        battle_dialogue_visible,
        subprocess_call,
        battle_map_surface_visible,
        sleep,
    ):
        battle_command_menu_visible.side_effect = (False, False, True, True)

        self.assertEqual(
            runner.advance_to_battle_command(self.args(), open_map_command=True),
            0,
        )

        self.assertEqual(subprocess_call.call_count, 2)
        self.assertEqual(capture_window.call_count, 4)

    @mock.patch.object(runner.time, "sleep")
    @mock.patch.object(runner, "battle_map_surface_visible", return_value=True)
    @mock.patch.object(runner.subprocess, "call", return_value=0)
    @mock.patch.object(runner, "battle_dialogue_visible", return_value=False)
    @mock.patch.object(runner, "battle_command_menu_visible")
    @mock.patch.object(runner, "game_over_visible", return_value=False)
    @mock.patch.object(runner, "capture_window")
    def test_map_transition_can_require_more_than_four_confirmations(
        self,
        capture_window,
        game_over_visible,
        battle_command_menu_visible,
        battle_dialogue_visible,
        subprocess_call,
        battle_map_surface_visible,
        sleep,
    ):
        args = self.args()
        args.max_confirmations = 6
        battle_command_menu_visible.side_effect = (
            False,
            False,
            False,
            False,
            False,
            True,
            True,
        )

        self.assertEqual(
            runner.advance_to_battle_command(args, open_map_command=True),
            0,
        )

        self.assertEqual(subprocess_call.call_count, 5)
        self.assertEqual(capture_window.call_count, 7)


if __name__ == "__main__":
    unittest.main()
