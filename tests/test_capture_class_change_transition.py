from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools import build_class_change_probe_rom as probe_builder
from tools import capture_class_change_transition as capture_tool


ROOT = Path(__file__).resolve().parents[1]


class CaptureClassChangeTransitionTests(unittest.TestCase):
    def test_artifact_stem_is_stable(self):
        self.assertEqual(
            capture_tool.artifact_stem(0x903C, 5, 0x0A),
            "903c_c5_s0a",
        )

    def test_build_probe_uses_selected_source_transition(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "probe.md"
            checksum, candidates = capture_tool.build_probe(
                probe_builder.DEFAULT_INPUT_ROM,
                probe_builder.DEFAULT_SOURCE_ROM,
                output,
                commander_id=5,
                current_class=0x0A,
                runtime_record_index=1,
            )
            self.assertEqual(checksum, 0xDBEF)
            self.assertEqual(candidates, (0x11, 0x12, 0x13))
            self.assertEqual(len(output.read_bytes()), 0x400000)


if __name__ == "__main__":
    unittest.main()
