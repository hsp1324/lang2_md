import ast
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image

from tools import run_blastem_sequence as sequence
from tools import run_scenario27_ending_page_supplement as supplement
from tools import run_scenario27_stock_route as stock


ROOT = Path(__file__).resolve().parents[1]


class Scenario27StockRouteTests(unittest.TestCase):
    def test_manual_slot_arguments_change_no_level_or_experience(self):
        self.assertEqual(
            stock.manual_slot_args(),
            [
                "--manual-slot-commander-id",
                "1",
                "--manual-slot-level",
                "8",
                "--manual-slot-experience",
                "18",
                "--manual-slot-expected-class",
                "0x12",
                "--manual-slot-class",
                "0x22",
                "--manual-slot-at",
                "99",
                "--manual-slot-df",
                "99",
            ],
        )

    def test_manual_slot_report_allows_only_class_at_df(self):
        size = sequence.MANUAL_SLOT_CHECKSUM_DATA_SIZE
        before = bytearray(size)
        commander = sequence.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        before[commander + sequence.MANUAL_SLOT_COMMANDER_CLASS_OFFSET] = 0x12
        before[commander + sequence.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET] = 8
        before[commander + sequence.MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET] = 18
        before[commander + sequence.MANUAL_SLOT_COMMANDER_AT_OFFSET] = 27
        before[commander + sequence.MANUAL_SLOT_COMMANDER_DF_OFFSET] = 30
        after = bytearray(before)
        after[commander + sequence.MANUAL_SLOT_COMMANDER_CLASS_OFFSET] = 0x22
        after[commander + sequence.MANUAL_SLOT_COMMANDER_AT_OFFSET] = 99
        after[commander + sequence.MANUAL_SLOT_COMMANDER_DF_OFFSET] = 99
        with tempfile.TemporaryDirectory() as temporary:
            seed = Path(temporary) / "seed.gst"
            sram = Path(temporary) / "save.sram"
            seed.write_bytes(b"seed")
            sram.write_bytes(b"sram")
            with mock.patch.object(
                stock.preparation,
                "manual_slot_record_from_gst",
                return_value=bytes(before),
            ), mock.patch.object(
                stock.legacy,
                "manual_slot_record",
                return_value=bytes(after),
            ):
                report = stock.manual_slot_change_report(seed, sram)
        self.assertEqual(report["before_elwin"]["class_id"], 0x12)
        self.assertEqual(report["after_elwin"]["class_id"], 0x22)
        self.assertTrue(report["level_experience_unchanged"])
        self.assertTrue(report["ending_kill_retreat_fields_unchanged"])
        self.assertFalse(report["runtime_hp_coordinate_fields_written"])

    def test_manual_slot_report_rejects_an_ending_stat_change(self):
        size = sequence.MANUAL_SLOT_CHECKSUM_DATA_SIZE
        before = bytearray(size)
        commander = sequence.MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
        before[commander + sequence.MANUAL_SLOT_COMMANDER_CLASS_OFFSET] = 0x12
        before[commander + sequence.MANUAL_SLOT_COMMANDER_LEVEL_OFFSET] = 8
        before[commander + sequence.MANUAL_SLOT_COMMANDER_EXPERIENCE_OFFSET] = 18
        after = bytearray(before)
        after[commander + sequence.MANUAL_SLOT_COMMANDER_CLASS_OFFSET] = 0x22
        after[commander + sequence.MANUAL_SLOT_COMMANDER_AT_OFFSET] = 99
        after[commander + sequence.MANUAL_SLOT_COMMANDER_DF_OFFSET] = 99
        after[commander + 0x12] = 1
        with mock.patch.object(
            stock.preparation,
            "manual_slot_record_from_gst",
            return_value=bytes(before),
        ), mock.patch.object(
            stock.legacy,
            "manual_slot_record",
            return_value=bytes(after),
        ), self.assertRaisesRegex(RuntimeError, "undeclared serialized bytes"):
            stock.manual_slot_change_report(Path("seed"), Path("sram"))

    def test_occupancy_scan_includes_bernhardt_group_18(self):
        def runtime_member(_gst, group, member):
            if (group, member) == (18, 0):
                return {
                    "group_index": group,
                    "member_index": member,
                    "class_id": 0x4E,
                    "name_id": 0x0E,
                    "side_id": 4,
                    "defeated_flag": 0,
                    "hp": 10,
                    "x": 15,
                    "y": 4,
                }
            return {
                "group_index": group,
                "member_index": member,
                "class_id": 0xFF,
                "name_id": 0,
                "side_id": 0,
                "defeated_flag": 0,
                "hp": 0,
                "x": 0xFF,
                "y": 0xFF,
            }

        with mock.patch.object(
            stock.legacy, "runtime_member", side_effect=runtime_member
        ):
            occupants = stock.live_occupants(Path("observed.gst"), (15, 4))
        self.assertEqual([(row["group_index"], row["member_index"]) for row in occupants], [(18, 0)])

    def test_residual_one_row_command_panel_is_not_a_bare_map(self):
        with tempfile.TemporaryDirectory() as temporary:
            panel = Path(temporary) / "panel.png"
            bare = Path(temporary) / "bare.png"
            panel_image = Image.new("RGB", (320, 240), (0, 0, 0))
            panel_image.paste((10, 20, 100), stock.RESIDUAL_PANEL_CROP)
            panel_image.save(panel)
            Image.new("RGB", (320, 240), (0, 0, 0)).save(bare)
            self.assertTrue(stock.residual_command_panel_visible(panel))
            self.assertFalse(stock.residual_command_panel_visible(bare))

    def test_route_is_source_locked_to_stock_turn_two_attack_geometry(self):
        self.assertEqual(len(stock.TURN_ONE_ROUTE), 8)
        self.assertEqual(stock.ELWIN_TURN_ONE_ORIGIN, (15, 16))
        self.assertEqual(stock.ELWIN_TURN_ONE_DESTINATION, (15, 10))
        self.assertEqual(stock.TURN_ONE_ROUTE[-1][4], (15, 9))
        self.assertEqual(stock.BERNHARDT_GROUP, 18)

    def test_ordinary_combat_stops_on_the_first_observed_zero_hp_frame(self):
        class Recorder:
            def __init__(self, root):
                self.root = root
                self.sent = []
                self.frame = 0

            def send(self, keys, *, delay):
                self.sent.append((keys, delay))

            def capture(self, relative):
                self.frame += 1
                return self.root / relative

            def save_gst(self, relative):
                return self.root / relative

        bernhardt_alive = {
            "class_id": stock.BERNHARDT_CLASS,
            "name_id": stock.BERNHARDT_COMMANDER_ID,
            "defeated_flag": 0,
            "hp": 5,
            "x": 15,
            "y": 9,
        }
        bernhardt_defeated = {
            **bernhardt_alive,
            "defeated_flag": 0x80,
            "hp": 0,
        }
        elwin_alive = {
            "class_id": stock.ELWIN_COMBAT_CLASS,
            "name_id": stock.ELWIN_COMMANDER_ID,
            "defeated_flag": 0,
            "hp": 8,
            "x": 15,
            "y": 10,
        }
        with tempfile.TemporaryDirectory() as temporary:
            recorder = Recorder(Path(temporary))
            with mock.patch.object(
                stock.shared,
                "image_report",
                side_effect=lambda path: {"path": str(path)},
            ), mock.patch.object(
                stock.legacy,
                "runtime_member",
                side_effect=(
                    bernhardt_alive,
                    bernhardt_defeated,
                    elwin_alive,
                ),
            ), mock.patch.object(
                stock,
                "live_process_checkpoint",
                return_value={"pid": 7},
            ), mock.patch.object(stock, "assert_same_exact_process"):
                report, _ = stock.confirm_target_and_advance_battle(
                    recorder,
                    rom=Path("release.bin"),
                    baseline_process={"pid": 7},
                    max_frames=5,
                    battle_delay=0.2,
                )
        self.assertEqual(report["stop_frame"], 2)
        self.assertEqual(len(report["battle_frames"]), 2)
        self.assertEqual(
            recorder.sent,
            [(["c"], 0.25), (["c"], 0.2), (["c"], 0.2)],
        )
        self.assertEqual(report["bernhardt"]["hp"], 0)
        self.assertEqual(report["elwin"]["hp"], 8)

    def test_acceptance_sources_contain_no_runtime_restore_or_tactical_writer(self):
        paths = (
            ROOT / "tools/run_scenario27_stock_route.py",
            ROOT / "tools/run_scenario27_ending_page_supplement.py",
        )
        forbidden_names = {
            "relaunch_blastem_from_gst",
            "restore_external_runtime_gst",
            "stage_adjacent_combat_fixture",
            "build_exact_release_runtime_fixture",
            "restore_exact_release_runtime_fixture",
            "validate_loaded_exact_release_runtime_fixture",
            "relaunch_runtime_checkpoint",
            "patch_probe",
            "write_bytes",
        }
        forbidden_cli = {
            "--execution-mode",
            "--probe-manifest",
            "--expected-probe-run-id",
            "--source-rom",
            "--load-delay",
        }
        for path in paths:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            names = {
                node.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Name)
            }
            attributes = {
                node.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
            }
            function_names = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            strings = {
                node.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
            self.assertFalse(forbidden_names & (names | attributes), path)
            self.assertFalse(
                {
                    name
                    for name in function_names
                    if any(
                        token in name.lower()
                        for token in ("fixture", "relaunch", "restore", "staged")
                    )
                },
                path,
            )
            self.assertFalse(forbidden_cli & strings, path)
            self.assertNotIn("-s FILE", source)
            self.assertNotIn("runtime fixture", source.lower())
            self.assertNotIn("run_scenario27_ending_surface", source)
            self.assertNotIn("build_korean_jp_probe", source)

    def test_supplement_has_one_exact_stock_acceptance_mode(self):
        source = Path(supplement.__file__).read_text(encoding="utf-8")
        self.assertIn("exact-release-same-process-stock-ui", source)
        self.assertIn("drive_to_bernhardt_target", source)
        self.assertIn("confirm_target_and_advance_battle", source)
        self.assertIn("same_process_checkpoint", source)
        self.assertNotIn("add_subparsers", source)
        self.assertNotIn('== "model"', source)


if __name__ == "__main__":
    unittest.main()
