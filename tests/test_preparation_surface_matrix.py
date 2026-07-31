from pathlib import Path
import json
import subprocess
import sys
import unittest

from tools import run_preparation_surface_matrix as matrix


ROOT = Path(__file__).resolve().parents[1]
NORMAL_ROM = ROOT / "tmp/Langrisser II (Korean prep-pattern-pool-yal probe).md"
REFERENCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
SEED_GST = (
    ROOT
    / "captures/analysis/"
    "hard_mode_current_candidate_first_turn_s27_endpoint.gst"
)


class PreparationSurfaceMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = NORMAL_ROM.read_bytes()

    def test_player_commander_counts_for_scenarios_one_through_twenty_seven(self):
        self.assertEqual(
            [
                matrix.player_commander_count(self.data, number)
                for number in range(1, 28)
            ],
            [
                2, 3, 3, 3, 5, 5, 6, 7, 7,
                5, 6, 7, 7, 7, 7, 8, 8, 8,
                8, 8, 8, 8, 9, 9, 9, 10, 10,
            ],
        )

    def test_seed_preserves_actual_classes_and_hire_masks(self):
        roster = matrix.manual_slot_roster(SEED_GST)
        self.assertEqual(
            [row["class_id"] for row in roster],
            [1, 2, 2, 1, 3, 1, 6, 1, 7, 9],
        )
        self.assertEqual(
            [row["hire_mask"] for row in roster],
            [
                "0x0004", "0x0800", "0x0800", "0x0004", "0x0800",
                "0x0004", "0x2004", "0x0004", "0x1004", "0x0900",
            ],
        )
        self.assertEqual(
            [row["korean"] for row in roster[0]["hire_rows"]],
            ["솔저"],
        )
        self.assertEqual(
            [row["korean"] for row in roster[6]["hire_rows"]],
            ["솔저", "그리폰"],
        )
        self.assertTrue(
            all(row["hire_page_count"] == 1 for row in roster)
        )

    def test_player_commander_ids_follow_each_scenario_name_table(self):
        self.assertEqual(matrix.player_commander_ids(self.data, 1), [1, 5])
        self.assertEqual(
            matrix.player_commander_ids(self.data, 9),
            [1, 5, 6, 2, 4, 8, 7],
        )

    def test_plan_looks_up_seed_progress_by_commander_id(self):
        plan = matrix.build_plan(NORMAL_ROM, REFERENCE_ROM, SEED_GST, 9)
        rows = plan["allied_commanders"]["seed_records"]
        self.assertEqual(
            [row["commander_id"] for row in rows],
            [1, 5, 6, 2, 4, 8, 7],
        )
        self.assertEqual(
            [row["class_korean"] for row in rows],
            [
                "파이터", "워록", "파이터", "클레릭",
                "파이터", "파이터", "호크나이트",
            ],
        )
        self.assertEqual(
            [[hire["korean"] for hire in row["hire_rows"]] for row in rows],
            [
                ["솔저"], ["가드맨"], ["솔저"], ["가드맨"],
                ["솔저"], ["솔저"], ["솔저", "그리폰"],
            ],
        )

    def test_allied_navigation_turns_the_page_after_fifth_commander(self):
        self.assertEqual(
            matrix.allied_next_navigation(4, 7),
            ["down"],
        )
        self.assertEqual(
            matrix.allied_next_navigation(5, 7),
            ["right", "up"],
        )
        self.assertEqual(
            matrix.allied_next_navigation(6, 7),
            ["down"],
        )
        self.assertEqual(
            matrix.allied_next_navigation(5, 10),
            ["right", "up", "up", "up", "up"],
        )

    def test_scenario_one_route_covers_each_visible_record_once(self):
        plan = matrix.build_plan(NORMAL_ROM, REFERENCE_ROM, SEED_GST, 1)
        fixed = plan["fixed_records"]
        self.assertEqual(fixed["count"], 12)
        self.assertEqual(fixed["visible_count"], 6)
        self.assertEqual(
            [row["index"] for row in fixed["route"]],
            [0, 1, 8, 9, 10, 11],
        )
        leon = next(row for row in fixed["route"] if row["index"] == 9)
        self.assertEqual(leon["mercenary_classes_korean"], ["로얄호스"])
        self.assertEqual(leon["runtime_checkpoint_chars"], ["얄"])
        self.assertTrue(
            all(
                not row["runtime_checkpoint_chars"]
                for row in fixed["route"]
                if row["index"] != 9
            )
        )
        self.assertEqual(
            fixed["navigation"],
            "right_cycle_source_record_order",
        )
        self.assertEqual(
            [row["index"] for row in fixed["not_applicable"]],
            [2, 3, 4, 5, 6, 7],
        )

    def test_directional_route_closes_coordinate_distance_exactly(self):
        keys = matrix.directional_keys((16, 12), (4, 3))
        self.assertEqual(keys.count("left"), 12)
        self.assertEqual(keys.count("up"), 9)
        self.assertEqual(len(keys), 21)

    def test_perceptual_hash_distance_counts_changed_bits(self):
        self.assertEqual(
            matrix.hash_distance(
                (False, False, True, True),
                (False, True, False, True),
            ),
            2,
        )
        with self.assertRaisesRegex(ValueError, "same length"):
            matrix.hash_distance((False,), (False, True))

    def test_preparation_action_cursor_detector_reads_hire_row(self):
        frame = ROOT / "captures/run/normal_3203_s09_pre_shop_prep.png"
        self.assertEqual(matrix.preparation_focus_side(frame), "right")
        self.assertEqual(matrix.preparation_action_row(frame), 0)

    def test_fixed_detail_detector_rejects_arrangement_and_equipment_shapes(self):
        self.assertTrue(
            matrix.fixed_detail_visible(
                ROOT / "captures/run/normal_3203_s09_pre_shop_enemy_detail.png"
            )
        )
        self.assertFalse(
            matrix.fixed_detail_visible(
                ROOT / "captures/run/normal_3203_s09_pre_shop_arrangement.png"
            )
        )

    def test_arrangement_menu_detector_rejects_detail(self):
        menu = ROOT / "captures/run/normal_3203_s09_pre_shop_arrangement.png"
        detail = ROOT / "captures/run/normal_3203_s09_pre_shop_enemy_detail.png"
        self.assertTrue(matrix.arrangement_menu_visible(menu))
        self.assertFalse(matrix.arrangement_menu_visible(detail))

    def test_scenario_five_arrangement_menu_uses_panel_width_not_detail_shape(self):
        menu = (
            ROOT
            / "captures/run/preparation_surface_matrix/normal/s05/current03/"
            "pre/arrangement/menu.png"
        )
        detail = (
            ROOT
            / "captures/run/preparation_surface_matrix/normal/s05/current03/"
            "pre/fixed/record_00.png"
        )
        # The five-row menu also satisfies the broad legacy detail detector.
        # Its blue panel ends before x=145, while a real detail panel does not.
        self.assertTrue(matrix.fixed_detail_visible(menu))
        self.assertTrue(matrix.arrangement_menu_visible(menu))
        self.assertFalse(matrix.arrangement_menu_visible(detail))

    def test_arrangement_roster_detector_accepts_five_visible_rows(self):
        roster = (
            ROOT
            / "captures/run/preparation_surface_matrix/normal/s09/s09a02/"
            "pre/arrangement/roster_page_01.png"
        )
        self.assertTrue(matrix.arrangement_roster_visible(roster))
        self.assertFalse(matrix.arrangement_menu_visible(roster))

    def test_plan_cli_emits_machine_readable_unreviewed_policy(self):
        output = subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "tools/run_preparation_surface_matrix.py"),
                "plan",
                "--profile",
                "normal",
                "--scenario",
                "1",
            ],
            cwd=ROOT,
            text=True,
        )
        plan = json.loads(output)
        self.assertEqual(plan["scenario"], 1)
        self.assertEqual(plan["allied_commanders"]["count"], 2)
        self.assertIn("never change", plan["acceptance_policy"])


if __name__ == "__main__":
    unittest.main()
