from pathlib import Path
import unittest

from tools.run_blastem_sequence import disable_host_gamepad_bindings


ROOT = Path(__file__).resolve().parents[1]


class BlastEmProbeRuntimeTests(unittest.TestCase):
    def test_test_config_removes_host_gamepad_bindings(self):
        source = (ROOT / "tools/blastem/default.cfg").read_text(encoding="utf-8")
        patched = disable_host_gamepad_bindings(source)
        pads = patched[patched.index("\tpads {") : patched.index("\tmice {")]
        self.assertEqual(pads, "\tpads {\n\t}\n")
        self.assertIn("up gamepads.1.up", patched)
        self.assertIn("\tmice {", patched)


if __name__ == "__main__":
    unittest.main()
