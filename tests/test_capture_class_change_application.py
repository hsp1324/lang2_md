from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

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

    def test_reads_equipped_item_from_gst(self):
        record = probe_builder.runtime_record_address(0) & 0xFFFF
        data = bytearray(
            GST_WORK_RAM_FILE_OFFSET + record + probe_builder.RUNTIME_RECORD_SIZE
        )
        offset = GST_WORK_RAM_FILE_OFFSET + record
        data[offset + probe_builder.EQUIPPED_ITEM_OFFSET] = 0x1A
        self.assertEqual(application_tool.runtime_equipped_item(bytes(data), 0), 0x1A)

    def test_capture_all_candidates_returns_to_selected_row(self):
        self.assertEqual(
            application_tool.candidate_navigation(3, 2, capture_all=True),
            ((1, 2, 3), 1),
        )

    def test_candidate_surface_classifier_requires_the_full_right_panels(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "surface.png"
            image = Image.new("RGB", (320, 240), (49, 174, 0))
            image.save(path)
            self.assertFalse(
                application_tool.class_change_candidate_surface_visible(path)
            )

            left, top, right, bottom = application_tool.CLASS_CHANGE_MENU_PANEL
            for y in range(top, bottom):
                for x in range(left, right):
                    image.putpixel(
                        (x, y), application_tool.CLASS_CHANGE_MENU_BLUE
                    )
            image.save(path)
            self.assertTrue(
                application_tool.class_change_candidate_surface_visible(path)
            )

    def test_candidate_surface_classifier_rejects_wrong_capture_size(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "surface.png"
            Image.new(
                "RGB",
                (640, 480),
                application_tool.CLASS_CHANGE_MENU_BLUE,
            ).save(path)
            self.assertFalse(
                application_tool.class_change_candidate_surface_visible(path)
            )
        self.assertEqual(
            application_tool.candidate_navigation(3, 2, capture_all=False),
            ((1, 2), 0),
        )

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
            self.assertEqual(checksum, 0x4BBB)
            self.assertEqual(expected_class, 0x08)
            self.assertEqual(len(output.read_bytes()), 0x400000)

    def test_build_probe_can_prefer_a_nonfirst_source_candidate(self):
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
                preferred_candidate=0x09,
            )
            self.assertIsInstance(checksum, int)
            self.assertEqual(expected_class, 0x09)
            self.assertEqual(len(output.read_bytes()), 0x400000)

    def test_build_probe_can_restart_from_a_fifth_tier_runestone(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "runestone.md"
            checksum, expected_class = application_tool.build_probe(
                probe_builder.DEFAULT_INPUT_ROM,
                probe_builder.DEFAULT_SOURCE_ROM,
                output,
                commander_id=7,
                current_class=0x24,
                runtime_record_index=0,
                restore_commander_id=1,
                runestone_restart=True,
            )
            self.assertIsInstance(checksum, int)
            self.assertEqual(expected_class, 0x04)
            self.assertEqual(len(output.read_bytes()), 0x400000)


if __name__ == "__main__":
    unittest.main()
