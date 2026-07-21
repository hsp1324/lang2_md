from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools import build_class_change_probe_rom as probe_builder
from tools import capture_class_change_application as application_tool
from tools.run_blastem_sequence import GST_WORK_RAM_FILE_OFFSET


class CaptureClassChangeApplicationTests(unittest.TestCase):
    def test_artifact_stem_is_stable(self):
        self.assertEqual(
            application_tool.artifact_stem(0x7164, 10, 0x03),
            "7164_c10_s03_forced_apply",
        )

    def test_reads_runtime_progress_from_gst(self):
        record = probe_builder.runtime_record_address(0) & 0xFFFF
        data = bytearray(
            GST_WORK_RAM_FILE_OFFSET + record + probe_builder.RUNTIME_RECORD_SIZE
        )
        offset = GST_WORK_RAM_FILE_OFFSET + record
        data[offset] = 0x08
        data[offset + 1] = 0x01
        data[offset + probe_builder.ELWIN_LEVEL_OFFSET] = 1
        data[offset + probe_builder.ELWIN_EXPERIENCE_OFFSET] = 8
        self.assertEqual(
            application_tool.runtime_progress(bytes(data), 0),
            (0x08, 0x01, 1, 8),
        )

    def test_rejects_short_gst(self):
        with self.assertRaisesRegex(ValueError, "too short"):
            application_tool.runtime_progress(b"", 0)

    def test_build_probe_uses_first_source_candidate(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "apply.md"
            checksum, expected_class = application_tool.build_probe(
                probe_builder.DEFAULT_INPUT_ROM,
                probe_builder.DEFAULT_SOURCE_ROM,
                output,
                commander_id=10,
                current_class=0x03,
                runtime_record_index=0,
                restore_commander_id=1,
            )
            self.assertEqual(checksum, 0x5B38)
            self.assertEqual(expected_class, 0x08)
            self.assertEqual(len(output.read_bytes()), 0x400000)


if __name__ == "__main__":
    unittest.main()
