import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from tools import capture_summon_application as capture_tool
from tools.run_blastem_sequence import GST_WORK_RAM_FILE_OFFSET


class CaptureSummonApplicationTests(unittest.TestCase):
    def test_summon_positions_cover_two_pages(self):
        self.assertEqual(capture_tool.summon_position(0), (0, 0))
        self.assertEqual(capture_tool.summon_position(5), (0, 5))
        self.assertEqual(capture_tool.summon_position(6), (1, 0))
        self.assertEqual(capture_tool.summon_position(7), (1, 1))

    def test_rejects_invalid_summon_id(self):
        for summon_id in (-1, 8):
            with self.subTest(summon_id=summon_id):
                with self.assertRaisesRegex(ValueError, "summon ID"):
                    capture_tool.summon_position(summon_id)

    def test_mp_costs_match_rev00_table(self):
        self.assertEqual(
            capture_tool.SUMMON_MP_COSTS,
            (5, 10, 12, 10, 8, 10, 10, 15),
        )

    def test_reads_summoned_member_from_hein_group(self):
        record = (
            capture_tool.magic_capture.RUNTIME_RECORD_BASE
            + capture_tool.magic_capture.HEIN_RUNTIME_RECORD
            * capture_tool.magic_capture.RUNTIME_RECORD_SIZE
        )
        offset = (
            GST_WORK_RAM_FILE_OFFSET
            + record
            + capture_tool.SUMMONED_MEMBER_INDEX * capture_tool.MEMBER_RECORD_SIZE
        )
        data = bytearray(offset + capture_tool.MEMBER_RECORD_SIZE)
        data[offset] = 0x8D
        data[offset + 6] = 12
        data[offset + 7] = 20
        self.assertEqual(
            capture_tool.runtime_member(
                bytes(data), capture_tool.SUMMONED_MEMBER_INDEX
            ),
            (0x8D, 12, 20),
        )

    def test_rejects_invalid_member_or_short_gst(self):
        for member_index in (-1, 8):
            with self.assertRaisesRegex(ValueError, "member index"):
                capture_tool.runtime_member(b"", member_index)
        with self.assertRaisesRegex(ValueError, "too short"):
            capture_tool.runtime_member(b"", 7)

    def test_detects_each_summon_list_cursor_row(self):
        with TemporaryDirectory() as temp_dir:
            for expected_row, start_y in enumerate(
                capture_tool.SUMMON_CURSOR_Y_STARTS
            ):
                with self.subTest(expected_row=expected_row):
                    image = Image.new("RGB", (320, 240), (0, 0, 80))
                    for x in range(36, 44):
                        for y in range(start_y + 5, start_y + 7):
                            image.putpixel((x, y), (220, 220, 220))
                    path = Path(temp_dir) / f"row-{expected_row}.png"
                    image.save(path)
                    self.assertEqual(
                        capture_tool.selected_list_row(path), expected_row
                    )

    def test_rejects_capture_without_summon_list_cursor(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "blank.png"
            Image.new("RGB", (320, 240), (0, 0, 80)).save(path)
            with self.assertRaisesRegex(RuntimeError, "cursor not detected"):
                capture_tool.selected_list_row(path)

if __name__ == "__main__":
    unittest.main()
