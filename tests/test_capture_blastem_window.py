import unittest

from tools.capture_blastem_window import windows_capture_script


class CaptureBlastemWindowTests(unittest.TestCase):
    def test_windows_fallback_captures_client_without_focus_calls(self):
        script = windows_capture_script(
            r"C:\\Temp\\blastem.png", 38, 59, 320, 240
        )
        self.assertIn("DwmGetWindowAttribute", script)
        self.assertIn("($rect.Left + 38)", script)
        self.assertIn("($rect.Top + 59)", script)
        self.assertIn("System.Drawing.Bitmap 320,240", script)
        self.assertNotIn("SetForegroundWindow", script)
        self.assertNotIn("SetFocus", script)
        self.assertNotIn("ShowWindow", script)


if __name__ == "__main__":
    unittest.main()
