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
            ["left@0.02:0.35", "left@0.02:0.35", "down@0.02:0.35"],
        )
        self.assertEqual(capture_tool.movement_specs(0, 0), [])

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
            Image.new("RGB", (320, 240), (0, 128, 0)).save(path)
            self.assertFalse(capture_tool.portrait_dialogue_visible(path))

    def test_target_probe_checksum_is_stable(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "magic.md"
            source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
            probe = bytearray(probe_builder.DEFAULT_INPUT_ROM.read_bytes())
            checksum = probe_builder.patch_probe(probe, source, place_target=True)
            output.write_bytes(probe)
            self.assertEqual(checksum, 0xC2DC)
            self.assertEqual(len(output.read_bytes()), 0x400000)

    def test_effect_delay_defaults_past_the_stock_animation(self):
        self.assertEqual(capture_tool.DEFAULT_EFFECT_DELAY, 8.0)
        self.assertEqual(capture_tool.DEFAULT_FINAL_CONFIRMATIONS, 2)

    def test_send_steps_reactivates_for_each_input(self):
        with patch.object(capture_tool, "send_keys") as send:
            capture_tool.send_steps(["down:0.3", "down:0.3"])
        self.assertEqual(
            send.call_args_list,
            [call("down:0.3"), call("down:0.3")],
        )


if __name__ == "__main__":
    unittest.main()
