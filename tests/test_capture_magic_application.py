from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import call, patch

from PIL import Image

from tools import build_magic_application_probe_rom as probe_builder
from tools import capture_magic_application as capture_tool
from tools.run_blastem_sequence import GST_WORK_RAM_FILE_OFFSET


class CaptureMagicApplicationTests(unittest.TestCase):
    def test_magic_positions_cover_four_pages(self):
        self.assertEqual(capture_tool.magic_position(0), (0, 0))
        self.assertEqual(capture_tool.magic_position(5), (0, 5))
        self.assertEqual(capture_tool.magic_position(6), (1, 0))
        self.assertEqual(capture_tool.magic_position(16), (2, 4))
        self.assertEqual(capture_tool.magic_position(21), (3, 3))

    def test_rejects_invalid_magic_id(self):
        for magic_id in (-1, 22):
            with self.subTest(magic_id=magic_id):
                with self.assertRaisesRegex(ValueError, "magic ID"):
                    capture_tool.magic_position(magic_id)

    def test_builds_stable_target_movement(self):
        self.assertEqual(
            capture_tool.movement_specs(-2, 1),
            ["left@0.08:0.35", "left@0.08:0.35", "down@0.08:0.35"],
        )
        self.assertEqual(capture_tool.movement_specs(0, 0), [])
        self.assertGreaterEqual(capture_tool.DIRECTION_HOLD, 0.05)

    def test_reads_hein_mp_from_gst(self):
        record = (
            capture_tool.RUNTIME_RECORD_BASE
            + capture_tool.HEIN_RUNTIME_RECORD * capture_tool.RUNTIME_RECORD_SIZE
        )
        data = bytearray(
            GST_WORK_RAM_FILE_OFFSET + record + capture_tool.RUNTIME_RECORD_SIZE
        )
        offset = GST_WORK_RAM_FILE_OFFSET + record
        data[offset + capture_tool.CURRENT_MP_OFFSET] = 10
        data[offset + capture_tool.MAX_MP_OFFSET] = 12
        self.assertEqual(capture_tool.runtime_mp(bytes(data)), (10, 12))

    def test_rejects_short_gst(self):
        with self.assertRaisesRegex(ValueError, "too short"):
            capture_tool.runtime_mp(b"")

    def test_detects_each_magic_list_cursor_row(self):
        with TemporaryDirectory() as directory:
            for expected_row, start_y in enumerate(
                capture_tool.MAGIC_CURSOR_Y_STARTS
            ):
                with self.subTest(expected_row=expected_row):
                    image = Image.new("RGB", (320, 240), (0, 0, 80))
                    for x in range(36, 44):
                        for y in range(start_y + 5, start_y + 7):
                            image.putpixel((x, y), (220, 220, 220))
                    path = Path(directory) / f"row-{expected_row}.png"
                    image.save(path)
                    self.assertEqual(
                        capture_tool.selected_list_row(path),
                        expected_row,
                    )

    def test_rejects_capture_without_magic_list_cursor(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "blank.png"
            Image.new("RGB", (320, 240), (0, 0, 80)).save(path)
            with self.assertRaisesRegex(RuntimeError, "cursor not detected"):
                capture_tool.selected_list_row(path)

    def test_rejects_ambiguous_non_list_cursor_pattern(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ambiguous.png"
            image = Image.new("RGB", (320, 240), (0, 0, 80))
            for start_y in capture_tool.MAGIC_CURSOR_Y_STARTS[:2]:
                for x in range(36, 44):
                    for y in range(start_y + 5, start_y + 7):
                        image.putpixel((x, y), (220, 220, 220))
            image.save(path)
            with self.assertRaisesRegex(RuntimeError, "is ambiguous"):
                capture_tool.selected_list_row(path)

    def test_rejects_unaccepted_target_before_confirmation_loop(self):
        with TemporaryDirectory() as directory:
            before = Path(directory) / "before.png"
            after = Path(directory) / "after.png"
            Image.new("RGB", (320, 240), (0, 0, 80)).save(before)
            image = Image.new("RGB", (320, 240), (0, 0, 80))
            image.paste((0, 32, 80), (0, 0, 40, 40))
            image.save(after)
            self.assertLess(
                capture_tool.image_change_ratio(before, after),
                capture_tool.UNACCEPTED_TARGET_MAX_CHANGE_RATIO,
            )
            with self.assertRaisesRegex(
                RuntimeError,
                "target confirmation was not accepted",
            ):
                capture_tool.require_target_confirmation_accepted(
                    before,
                    after,
                    12,
                    12,
                )

    def test_accepts_changed_effect_frame_or_spent_mp(self):
        with TemporaryDirectory() as directory:
            before = Path(directory) / "before.png"
            after = Path(directory) / "after.png"
            Image.new("RGB", (320, 240), (0, 0, 80)).save(before)
            Image.new("RGB", (320, 240), (80, 0, 0)).save(after)
            capture_tool.require_target_confirmation_accepted(
                before,
                after,
                12,
                12,
            )
            capture_tool.require_target_confirmation_accepted(
                before,
                before,
                10,
                12,
            )

    def test_quicksave_path_requires_exactly_one_state(self):
        with TemporaryDirectory() as directory:
            with patch.object(capture_tool, "RUNTIME_ROOT", Path(directory)):
                with self.assertRaisesRegex(RuntimeError, "found 0"):
                    capture_tool.quicksave_path("missing")
                state = Path(directory) / "one" / "nested" / "quicksave.gst"
                state.parent.mkdir(parents=True)
                state.write_bytes(b"state")
                self.assertEqual(capture_tool.quicksave_path("one"), state)

    def test_detects_portrait_dialogue_blue_window(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "frame.png"
            image = Image.new("RGB", (320, 240), (0, 128, 0))
            image.paste((0, 0, 128), (30, 110, 295, 185))
            image.save(path)
            self.assertTrue(capture_tool.portrait_dialogue_visible(path))

            image = Image.new("RGB", (320, 240), (0, 128, 0))
            image.paste((0, 0, 128), (25, 70, 295, 120))
            image.save(path)
            self.assertTrue(capture_tool.portrait_dialogue_visible(path))

            image = Image.new("RGB", (320, 240), (0, 128, 0))
            image.paste((0, 0, 128), (30, 70, 135, 185))
            image.save(path)
            self.assertFalse(capture_tool.portrait_dialogue_visible(path))

            Image.new("RGB", (320, 240), (0, 128, 0)).save(path)
            self.assertFalse(capture_tool.portrait_dialogue_visible(path))

    def test_rejects_unfinished_post_effect_dialogue(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "frame.png"
            image = Image.new("RGB", (320, 240), (0, 128, 0))
            image.paste((0, 0, 128), (30, 110, 295, 185))
            image.save(path)
            with self.assertRaisesRegex(
                RuntimeError,
                "remained after 12 confirmations",
            ):
                capture_tool.require_effect_settled(path, 12)

            Image.new("RGB", (320, 240), (0, 128, 0)).save(path)
            capture_tool.require_effect_settled(path, 12)

    def test_target_probe_checksum_is_stable(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "magic.md"
            source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
            probe = bytearray(probe_builder.DEFAULT_INPUT_ROM.read_bytes())
            checksum = probe_builder.patch_probe(probe, source, place_target=True)
            output.write_bytes(probe)
            self.assertEqual(checksum, 0x7F1F)
            self.assertEqual(len(output.read_bytes()), 0x400000)

    def test_effect_delay_defaults_past_the_stock_animation(self):
        self.assertEqual(capture_tool.DEFAULT_EFFECT_DELAY, 8.0)
        self.assertEqual(capture_tool.DEFAULT_DIALOGUE_DELAY, 0.9)
        self.assertEqual(capture_tool.DEFAULT_FINAL_CONFIRMATIONS, 2)
        self.assertEqual(capture_tool.POST_EFFECT_SETTLE_DELAY, 1.2)
        self.assertEqual(capture_tool.POST_EFFECT_CLEAR_CHECKS, 2)

    def test_virtual_display_is_the_default_transport(self):
        self.assertEqual(capture_tool.DEFAULT_VIRTUAL_DISPLAY, ":104")
        self.assertEqual(
            capture_tool.sequence_display_args(desktop_display=False),
            ["--xlib-capture", "--software-renderer"],
        )
        self.assertEqual(
            capture_tool.sequence_display_args(desktop_display=True),
            ["--desktop-display"],
        )

    def test_virtual_capture_uses_xlib_only(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "capture.png"
            previous = capture_tool.XLIB_ONLY_CAPTURE
            try:
                capture_tool.XLIB_ONLY_CAPTURE = True
                with patch.object(capture_tool, "run") as run:
                    capture_tool.capture(path)
                run.assert_called_once_with(
                    [
                        capture_tool.sys.executable,
                        str(capture_tool.CAPTURE_WINDOW),
                        str(path),
                        "--xlib-only",
                    ]
                )
            finally:
                capture_tool.XLIB_ONLY_CAPTURE = previous

    def test_send_steps_reactivates_for_each_input(self):
        with patch.object(capture_tool, "send_keys") as send:
            capture_tool.send_steps(["down:0.3", "down:0.3"])
        self.assertEqual(
            send.call_args_list,
            [call("down:0.3"), call("down:0.3")],
        )


if __name__ == "__main__":
    unittest.main()
