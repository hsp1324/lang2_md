import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from tools.capture_blastem_window import (
    crop_printed_client,
    windows_activate_script,
    windows_capture_script,
    windows_print_capture_script,
)
from tools import run_blastem_sequence


class CaptureBlastemWindowTests(unittest.TestCase):
    def test_windows_fallback_captures_client_without_focus_calls(self):
        script = windows_capture_script(
            r"C:\\Temp\\blastem.png", 38, 59, 320, 240, 396, 337
        )
        self.assertIn("DwmGetWindowAttribute", script)
        self.assertIn("/ 396.0", script)
        self.assertIn("/ 337.0", script)
        self.assertIn("[Math]::Round(38 * $scaleX)", script)
        self.assertIn("[Math]::Round(59 * $scaleY)", script)
        self.assertIn("System.Drawing.Bitmap $captureWidth,$captureHeight", script)
        self.assertNotIn("SetForegroundWindow", script)
        self.assertNotIn("SetFocus", script)
        self.assertNotIn("ShowWindow", script)

    def test_print_window_capture_does_not_require_focus(self):
        script = windows_print_capture_script(r"C:\\Temp\\blastem.png")
        self.assertIn("PrintWindow", script)
        self.assertIn("DwmGetWindowAttribute", script)
        self.assertIn("$hdc", script)
        self.assertNotIn("SetForegroundWindow", script)
        self.assertNotIn("SetFocus", script)
        self.assertNotIn("ShowWindow", script)

    def test_activation_is_explicitly_separated_from_capture(self):
        script = windows_activate_script()
        self.assertIn("ShowWindow", script)
        self.assertIn("SetForegroundWindow", script)
        self.assertNotIn("CopyFromScreen", script)

    def test_printed_window_is_scaled_and_cropped_to_x11_client(self):
        printed = Image.new("RGB", (792, 674), "gray")
        client = Image.new("RGB", (640, 480), "navy")
        printed.paste(client, (76, 118))
        cropped = crop_printed_client(
            printed,
            client_x=38,
            client_y=59,
            client_width=320,
            client_height=240,
            outer_width=396,
            outer_height=337,
        )
        self.assertEqual(cropped.size, (320, 240))
        self.assertEqual(cropped.getpixel((0, 0)), (0, 0, 128))
        self.assertEqual(cropped.getpixel((319, 239)), (0, 0, 128))

    @mock.patch("tools.run_blastem_sequence.subprocess.check_call")
    def test_sequence_capture_never_requests_window_activation(self, check_call):
        output = Path("captures/run/detector.png")
        run_blastem_sequence.capture_window(output)

        command = check_call.call_args.args[0]
        self.assertNotIn("--allow-focus-steal", command)
        self.assertNotIn("--print-window", command)


if __name__ == "__main__":
    unittest.main()
