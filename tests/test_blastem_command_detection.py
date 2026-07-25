from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

from PIL import Image

from tools import run_blastem_sequence as runner


class BlastemCommandDetectionTests(unittest.TestCase):
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
        sleep,
    ):
        battle_command_menu_visible.side_effect = (False, True, True)

        self.assertEqual(runner.advance_to_battle_command(self.args()), 0)

        subprocess_call.assert_called_once()
        first_capture = capture_window.call_args_list[0].args[0]
        self.assertEqual(first_capture.name, "detect_00.png")
        self.assertEqual(capture_window.call_count, 3)

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


if __name__ == "__main__":
    unittest.main()
