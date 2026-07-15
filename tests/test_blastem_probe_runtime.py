from pathlib import Path
import unittest

from argparse import Namespace

from tools.run_blastem_sequence import (
    detection_capture_path,
    disable_host_gamepad_bindings,
)


ROOT = Path(__file__).resolve().parents[1]


class BlastEmProbeRuntimeTests(unittest.TestCase):
    def test_test_config_removes_host_gamepad_bindings(self):
        source = (ROOT / "tools/blastem/default.cfg").read_text(encoding="utf-8")
        patched = disable_host_gamepad_bindings(source)
        pads = patched[patched.index("\tpads {") : patched.index("\tmice {")]
        self.assertEqual(pads, "\tpads {\n\t}\n")
        self.assertIn("up gamepads.1.up", patched)
        self.assertIn("\tmice {", patched)

    def test_detection_capture_prefix_numbers_frames(self):
        args = Namespace(capture_prefix=Path("captures/run/s03_brief.png"))
        self.assertEqual(
            detection_capture_path(args, Path("fallback.png"), 7),
            Path("captures/run/s03_brief_07.png"),
        )


if __name__ == "__main__":
    unittest.main()
