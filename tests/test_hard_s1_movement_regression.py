from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools import run_hard_s1_movement_regression as regression
from tools.analyze_preparation_vram_ownership import (
    GST_VDP_REG_OFFSET,
    GST_VRAM_OFFSET,
    VRAM_SIZE,
)


class HardScenario1MovementRegressionTests(unittest.TestCase):
    def test_release_source_and_seed_lineage_constants_match_files(self):
        expected = (
            (regression.DEFAULT_ROM, regression.EXPECTED_ROM_SHA256),
            (regression.DEFAULT_SOURCE_ROM, regression.EXPECTED_SOURCE_SHA256),
            (regression.DEFAULT_SEED_GST, regression.EXPECTED_SEED_SHA256),
        )
        for path, digest in expected:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(), digest
                )

    def test_runtime_display_guard_rejects_physical_or_implicit_displays(self):
        regression.require_isolated_display(":880")
        for display in (":0", ":99", "localhost:0", ""):
            with self.subTest(display=display):
                with self.assertRaises(ValueError):
                    regression.require_isolated_display(display)

    def test_bald_and_soldier_class_records_are_source_identical_move_five(self):
        report = regression.static_movement_report(
            regression.DEFAULT_SOURCE_ROM,
            regression.DEFAULT_ROM,
        )
        self.assertTrue(report["all_records_byte_identical"])
        self.assertTrue(report["all_expected_movement_five"])
        self.assertEqual(
            {
                row["class_id"]: row["hard_movement"]
                for row in report["classes"]
            },
            {"0x2E": 5, "0x64": 5},
        )

    def test_runtime_parser_locks_group_plus_0x44_and_member_identity(self):
        payload = bytearray(0x12478)
        group_start = (
            0x2478
            + regression.RUNTIME_GROUP_BASE
            + regression.BALD_GROUP_INDEX * regression.RUNTIME_GROUP_SIZE
        )
        payload[group_start] = regression.BALD_CLASS_ID
        payload[group_start + 1] = regression.BALD_NAME_ID
        payload[group_start + 3] = 10
        payload[group_start + 6] = regression.BALD_COORDINATE[0]
        payload[group_start + 7] = regression.BALD_COORDINATE[1]
        payload[
            group_start + regression.RUNTIME_GROUP_MOVEMENT_OFFSET
        ] = 5
        with tempfile.TemporaryDirectory() as directory:
            gst = Path(directory) / "synthetic.gst"
            gst.write_bytes(payload)
            group = regression.runtime_group(
                gst, regression.BALD_GROUP_INDEX
            )
        self.assertEqual(group["movement_plus_0x44"], 5)
        self.assertEqual(group["members"][0]["class_id"], 0x2E)
        self.assertEqual(group["members"][0]["name_id"], 0x12)
        self.assertEqual(
            (group["members"][0]["x"], group["members"][0]["y"]),
            (4, 7),
        )

    def test_selected_runtime_pointer_must_name_exact_dynamic_member(self):
        payload = bytearray(0x12478)
        ram = 0x2478
        member_index = 2
        payload[ram + regression.SELECTED_GROUP_INDEX_ADDRESS] = 0
        payload[ram + regression.SELECTED_MEMBER_INDEX_ADDRESS] = member_index
        payload[
            ram + regression.SELECTED_GROUP_POINTER_ADDRESS:
            ram + regression.SELECTED_GROUP_POINTER_ADDRESS + 4
        ] = regression.RUNTIME_GROUP_ABSOLUTE_BASE.to_bytes(4, "big")
        member_pointer = (
            regression.RUNTIME_GROUP_ABSOLUTE_BASE
            + member_index * regression.RUNTIME_MEMBER_SIZE
        )
        payload[
            ram + regression.SELECTED_MEMBER_POINTER_ADDRESS:
            ram + regression.SELECTED_MEMBER_POINTER_ADDRESS + 4
        ] = member_pointer.to_bytes(4, "big")
        with tempfile.TemporaryDirectory() as directory:
            gst = Path(directory) / "selected.gst"
            gst.write_bytes(payload)
            report = regression.selected_runtime_pointer_report(
                gst,
                expected_group_index=0,
                expected_member_index=member_index,
            )
            self.assertTrue(report["matches_exact_runtime_record"])
            with self.assertRaisesRegex(
                RuntimeError, "selected the wrong runtime record"
            ):
                regression.selected_runtime_pointer_report(
                    gst,
                    expected_group_index=0,
                    expected_member_index=1,
                )

    @staticmethod
    def synthetic_vdp_state(changes: dict[tuple[int, int], int]) -> bytes:
        payload = bytearray(GST_VRAM_OFFSET + VRAM_SIZE)
        payload[:4] = b"GST@"
        registers = bytearray(24)
        registers[2] = 0x30  # Plane A at 0xC000.
        registers[4] = 0x07  # Plane B at 0xE000.
        registers[16] = 0x01  # 64x32 cells.
        payload[
            GST_VDP_REG_OFFSET:GST_VDP_REG_OFFSET + len(registers)
        ] = registers
        for (x, y), word in changes.items():
            offset = GST_VRAM_OFFSET + 0xE000 + (y * 64 + x) * 2
            payload[offset:offset + 2] = word.to_bytes(2, "big")
        return bytes(payload)

    def test_reach_delta_groups_3x3_cells_and_unwraps_near_origin(self):
        # Langrisser battle cells are 24px (3x3 VDP tiles), not 16px.  Build a
        # symmetric five-cell cross centered at raw block start (29,8).
        before = self.synthetic_vdp_state({})
        blocks = ((29, 8), (26, 8), (32, 8), (29, 5), (29, 11))
        changes = {
            (start_x + dx, start_y + dy): 0x2000
            for start_x, start_y in blocks
            for dx in range(3)
            for dy in range(3)
        }
        after = self.synthetic_vdp_state(changes)
        with tempfile.TemporaryDirectory() as directory:
            before_path = Path(directory) / "before.gst"
            after_path = Path(directory) / "after.gst"
            capture = Path(directory) / "move.png"
            before_path.write_bytes(before)
            after_path.write_bytes(after)
            image = Image.new("RGB", (320, 240))
            pixels = image.load()
            # Stock 28px cursor outer frame at (230,71), whose inner 24px
            # battle cell begins at screen (232,72).
            for delta_value in (*range(1, 6), *range(22, 27)):
                for x, y in (
                    (230 + delta_value, 71),
                    (230 + delta_value, 98),
                    (230, 71 + delta_value),
                    (257, 71 + delta_value),
                ):
                    pixels[x, y] = (255, 174, 0)
            image.save(capture)
            delta = regression.plane_delta(before_path, after_path)
            report = regression.reach_coordinate_report(
                delta,
                (4, 16),
                movement=5,
                overlay_capture=capture,
                overlay_gst=after_path,
            )
        self.assertEqual(report["reachable_cell_count"], 5)
        self.assertEqual(
            report["coordinates"],
            [[3, 16], [4, 15], [4, 16], [4, 17], [5, 16]],
        )
        self.assertEqual(
            report["raw_plane_b_origin_modulo_name_table"], [29, 8]
        )
        self.assertEqual(
            report["palette_blocks"]["changed_name_table_tile_count"], 45
        )
        self.assertTrue(report["all_coordinates_within_movement_allowance"])
        self.assertTrue(report["origin_is_reachable"])

    def test_enemy_command_detector_accepts_low_blue_status_with_gold_frame(self):
        image = Image.new("RGB", (320, 240), (0, 0, 0))
        pixels = image.load()
        dark_blue = (8, 20, 104)
        gold = (192, 128, 16)
        white = (255, 255, 255)
        for y in range(25, 110):
            for x in range(32, 95):
                pixels[x, y] = dark_blue
        for y in range(30, 50):
            for x in range(36, 46):
                pixels[x, y] = white
        for y in range(42, 145):
            for x in range(94, 107):
                pixels[x, y] = gold
        # Keep this synthetic row just below the shared detector's current
        # 44% floor.  The runner-specific detector may accept it only because
        # the same band also contains the ornate gold status frame.
        for y in range(195, 235):
            for x in range(140):
                pixels[x, y] = dark_blue
            for x in range(140, 173):
                pixels[x, y] = gold
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "enemy-command.png"
            image.save(capture)
            self.assertFalse(
                regression.sequence.battle_command_menu_visible(capture)
            )
            self.assertTrue(
                regression.short_battle_command_menu_visible(capture)
            )

    def test_sha256_cli_value_is_exact_and_normalized(self):
        digest = "A" * 64
        self.assertEqual(regression.validate_sha256(digest), digest.lower())
        for invalid in ("", "a" * 63, "a" * 65, "g" * 64):
            with self.subTest(invalid=invalid):
                with self.assertRaises(regression.argparse.ArgumentTypeError):
                    regression.validate_sha256(invalid)

    def test_stock_all_factions_sequence_and_initial_deployment_are_locked(self):
        self.assertEqual(
            regression.ALL_FACTIONS_INPUT,
            (
                "up", "left", "up", "right", "a", "left", "down", "b",
                "down", "right", "a", "b", "down", "right", "a",
            ),
        )
        self.assertEqual(regression.SELECTED_SOLDIER_MEMBER_INDEX, 6)
        self.assertEqual(regression.SELECTED_SOLDIER_COORDINATE, (12, 16))
        static = regression.all_factions_static_report(
            regression.DEFAULT_ROM.read_bytes()
        )
        self.assertEqual(static["history_length"], 29)
        self.assertTrue(static["history_matches_documented_sequence"])
        self.assertEqual(static["required_current_held_mask"], "0x40")
        self.assertEqual(static["active_flag_work_ram"], "0xA6C7")

    def test_real_move_destination_must_be_in_overlay_and_empty(self):
        report = {
            "coordinates": [[13, 15], [12, 15], [12, 17], [11, 16]]
        }
        occupied = {(12, 17), (11, 16)}
        self.assertEqual(
            regression.reachable_empty_destinations(
                report, (12, 16), occupied
            ),
            [(12, 15), (13, 15)],
        )

    def test_status_popup_is_not_accepted_as_a_move_overlay(self):
        before = self.synthetic_vdp_state({})
        # A unit-information popup can leave Plane B unchanged; a genuine
        # Move range must make palette-only 3x3-cell changes there.
        popup = self.synthetic_vdp_state({})
        with tempfile.TemporaryDirectory() as directory:
            before_path = Path(directory) / "command.gst"
            popup_path = Path(directory) / "status.gst"
            before_path.write_bytes(before)
            popup_path.write_bytes(popup)
            delta = regression.plane_delta(before_path, popup_path)
        with self.assertRaisesRegex(
            ValueError, "palette-only Plane-B changes"
        ):
            regression.movement_palette_blocks(delta)


if __name__ == "__main__":
    unittest.main()
