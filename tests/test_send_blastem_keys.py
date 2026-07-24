import unittest
from unittest.mock import MagicMock, patch

from Xlib import X

from tools.send_blastem_keys import (
    DIRECT_EVENT_NEUTRAL_KEYS,
    DIRECT_EVENT_RELEASE_SETTLE,
    activate_window,
    choose_monitor,
    press,
)


class SendBlastemKeysTests(unittest.TestCase):
    def test_widest_monitor_is_selected_for_emulator_window(self):
        monitors = [
            ("TV", 0, 0, 1920, 1080),
            ("ULTRAWIDE", 1920, 717, 3440, 1440),
        ]
        self.assertEqual(
            choose_monitor(monitors, "widest"),
            ("ULTRAWIDE", 1920, 717, 3440, 1440),
        )

    def test_named_monitor_and_empty_fallback_are_deterministic(self):
        monitors = [
            ("TV", 0, 0, 1920, 1080),
            ("ULTRAWIDE", 1920, 717, 3440, 1440),
        ]
        self.assertEqual(choose_monitor(monitors, "TV"), monitors[0])
        self.assertIsNone(choose_monitor([], "widest"))

    def test_direct_event_does_not_restack_reposition_or_request_focus(self):
        display = MagicMock()
        window = MagicMock()
        with patch(
            "tools.send_blastem_keys.blastem_window_position",
            return_value=(1960, 757),
        ) as position:
            activate_window(display, window, request_focus=False)
        position.assert_not_called()
        window.configure.assert_not_called()
        display.sync.assert_not_called()
        display.intern_atom.assert_not_called()
        window.set_input_focus.assert_not_called()

    def test_direct_event_tap_starts_with_a_neutral_release_interval(self):
        display = MagicMock()
        display.keysym_to_keycode.return_value = 42
        window = MagicMock()

        with (
            patch("tools.send_blastem_keys.event.KeyRelease") as key_release,
            patch("tools.send_blastem_keys.event.KeyPress") as key_press,
            patch("tools.send_blastem_keys.time.sleep") as sleep,
        ):
            key_release.side_effect = [
                *(f"neutral-release-{index}" for index in range(4)),
                "tap-release",
            ]
            key_press.return_value = "tap-press"
            press(display, window, "left", hold=0.02, send_event=True)

        self.assertEqual(
            [call.args[0] for call in window.send_event.call_args_list],
            [
                *(f"neutral-release-{index}" for index in range(4)),
                "tap-press",
                "tap-release",
            ],
        )
        self.assertEqual(DIRECT_EVENT_NEUTRAL_KEYS, ("up", "down", "left", "right"))
        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list],
            [DIRECT_EVENT_RELEASE_SETTLE, 0.02],
        )

    def test_xtest_tap_releases_all_directions_before_pressing(self):
        display = MagicMock()
        display.keysym_to_keycode.return_value = 42
        window = MagicMock()

        with (
            patch("tools.send_blastem_keys.xtest.fake_input") as fake_input,
            patch("tools.send_blastem_keys.time.sleep") as sleep,
        ):
            press(display, window, "up", hold=0.02, send_event=False)

        self.assertEqual(fake_input.call_count, 6)
        for call in fake_input.call_args_list[:4]:
            self.assertEqual(call.args[1], X.KeyRelease)
        self.assertEqual(fake_input.call_args_list[4].args[1], X.KeyPress)
        self.assertEqual(fake_input.call_args_list[5].args[1], X.KeyRelease)
        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list],
            [DIRECT_EVENT_RELEASE_SETTLE, 0.02],
        )


if __name__ == "__main__":
    unittest.main()
