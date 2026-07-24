from pathlib import Path
import unittest

from argparse import Namespace

from tools.run_blastem_sequence import (
    BLASTEM,
    blastem_command,
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

    def test_software_renderer_flag_precedes_rom_path(self):
        rom = ROOT / "roms/builds/Langrisser II (Korean).md"
        self.assertEqual(
            blastem_command(rom, 320, 240, software_renderer=True),
            [str(BLASTEM), "-g", str(rom.resolve()), "320", "240"],
        )
        self.assertEqual(
            blastem_command(rom, 640, 480),
            [str(BLASTEM), str(rom.resolve()), "640", "480"],
        )


if __name__ == "__main__":
    unittest.main()
