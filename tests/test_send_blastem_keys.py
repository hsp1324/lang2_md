import unittest
from unittest.mock import MagicMock, patch

from tools.send_blastem_keys import activate_window, choose_monitor


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

    def test_direct_event_placement_does_not_request_focus(self):
        display = MagicMock()
        window = MagicMock()
        with patch(
            "tools.send_blastem_keys.blastem_window_position",
            return_value=(1960, 757),
        ):
            activate_window(display, window, request_focus=False)
        window.configure.assert_called_once()
        display.sync.assert_called_once()
        display.intern_atom.assert_not_called()
        window.set_input_focus.assert_not_called()


if __name__ == "__main__":
    unittest.main()
