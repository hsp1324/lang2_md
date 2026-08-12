from __future__ import annotations

from pathlib import Path
import unittest

from tools import run_s1_natural_ui_victory as victory


def unit(
    group: int,
    member: int,
    x: int,
    y: int,
    *,
    hp: int = 10,
) -> dict[str, int]:
    return {
        "group_index": group,
        "member_index": member,
        "side_id": victory.HOSTILE_SIDE,
        "class_id": victory.BALD_CLASS_ID if group == victory.BALD_GROUP else 0x72,
        "name_id": victory.BALD_NAME_ID if group == victory.BALD_GROUP else 0x20,
        "raw_action_flag": 0,
        "acted": 0,
        "defeated": 0,
        "hp": hp,
        "x": x,
        "y": y,
    }


class S1NaturalUiVictoryTests(unittest.TestCase):
    def test_fresh_launcher_rejects_every_external_state_input(self) -> None:
        command = victory.fresh_victory_launch_command(
            rom=Path("candidate.md"),
            runtime_name="fresh-victory",
            runtime_root=Path("runtime"),
            display=":986",
            initial_delay=1.0,
        )
        self.assertTrue(victory.FORBIDDEN_RUNTIME_INPUT_TOKENS.isdisjoint(command))
        for token in victory.FORBIDDEN_RUNTIME_INPUT_TOKENS:
            with self.subTest(token=token):
                with self.assertRaises(ValueError):
                    victory.validate_fresh_victory_launch([*command, token])

    def test_adjacent_target_prioritizes_exact_bald(self) -> None:
        bald = unit(victory.BALD_GROUP, 0, 4, 7)
        guard = unit(victory.BALD_GROUP, 1, 5, 8, hp=1)
        self.assertEqual(
            victory.adjacent_hostile((5, 7), [guard, bald]),
            bald,
        )

    def test_destination_prefers_bald_attack_then_bald_guard(self) -> None:
        bald = unit(victory.BALD_GROUP, 0, 4, 7)
        guard = unit(victory.BALD_GROUP, 1, 5, 7)
        other = unit(11, 0, 9, 9)
        rows = victory.tactical_destination_candidates(
            reachable=((4, 8), (6, 7), (9, 10), (10, 10)),
            origin=(10, 11),
            occupied=set(),
            hostiles=(bald, guard, other),
            bald=(4, 7),
        )
        self.assertEqual(rows[0], ((4, 8), bald))
        self.assertEqual(rows[1], ((6, 7), guard))

    def test_destination_avoids_occupied_and_makes_progress(self) -> None:
        bald = unit(victory.BALD_GROUP, 0, 4, 7)
        rows = victory.tactical_destination_candidates(
            reachable=((11, 17), (10, 16), (9, 15), (8, 14)),
            origin=(11, 17),
            occupied={(8, 14)},
            hostiles=(bald,),
            bald=(4, 7),
        )
        self.assertEqual(rows[0][0], (9, 15))
        self.assertNotIn((8, 14), [row[0] for row in rows])

    def test_destination_fails_without_non_origin_cell(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no unoccupied"):
            victory.tactical_destination_candidates(
                reachable=((11, 17),),
                origin=(11, 17),
                occupied=set(),
                hostiles=(),
                bald=(4, 7),
            )

    def test_route_map_learns_a_shorter_attack_path_from_live_overlays(self) -> None:
        route = victory.ReachabilityRouteMap()
        hostile = unit(13, 0, 13, 13)
        route.learn_overlay((13, 22), ((13, 22), (14, 19)))
        route.learn_overlay((14, 19), ((14, 19), (13, 14)))
        self.assertEqual(route.known_steps_to_attack((13, 22), [hostile]), 2)
        self.assertEqual(route.known_steps_to_attack((14, 19), [hostile]), 1)
        self.assertEqual(
            route.progress_kind(
                origin=(13, 22),
                candidate=(14, 19),
                hostiles=[hostile],
                recent=set(),
            ),
            "known_graph_shorter",
        )

    def test_route_map_allows_stock_overlay_to_omit_only_origin(self) -> None:
        route = victory.ReachabilityRouteMap()
        raw = route.learn_overlay((11, 18), ((10, 18), (11, 17)))
        self.assertEqual(raw, {(10, 18), (11, 17)})
        self.assertIn((11, 18), route.graph)
        self.assertEqual(route.graph[(11, 18)], raw)
        self.assertNotIn((11, 18), raw)

    def test_route_candidates_use_overlay_and_reject_recent_roundtrip(self) -> None:
        bald = unit(victory.BALD_GROUP, 0, 4, 7)
        nearby = unit(13, 0, 13, 13)
        route = victory.ReachabilityRouteMap()
        rows = victory.tactical_destination_candidates(
            reachable=((11, 17), (12, 18), (13, 18), (10, 18)),
            origin=(11, 17),
            occupied=set(),
            hostiles=(bald, nearby),
            bald=(4, 7),
            route=route,
            recent_coordinates=((13, 18),),
        )
        self.assertEqual(rows[0][0], (12, 18))
        self.assertNotIn((13, 18), [row[0] for row in rows])

    def test_route_candidates_fail_closed_on_regression_or_cycle(self) -> None:
        route = victory.ReachabilityRouteMap()
        route.explored_origins.update({(13, 22), (14, 22), (13, 23)})
        with self.assertRaisesRegex(RuntimeError, "cycle-safe graph-progress"):
            victory.tactical_destination_candidates(
                reachable=((13, 22), (14, 22), (13, 23)),
                origin=(13, 22),
                occupied=set(),
                hostiles=(),
                bald=(4, 7),
                route=route,
                recent_coordinates=((14, 22),),
            )

    def test_route_cycle_guard_rejects_repeated_turn_formation(self) -> None:
        guard = victory.ReachabilityRouteMap(limit=4)
        row = unit(0, 1, 13, 21)
        guard.begin_turn([row], 1)
        with self.assertRaisesRegex(RuntimeError, "formation cycle"):
            guard.begin_turn([row], 2)

    def test_turn_summary_records_coordinates_and_attacks(self) -> None:
        row = unit(0, 1, 13, 21)
        action = {
            "kind": "move_then_attack",
            "unit_before": row,
            "destination": [13, 22],
            "attack": {"target": unit(victory.BALD_GROUP, 0, 4, 7)},
            "route_before": {
                "nearest_hostile_manhattan": 9,
                "known_steps_to_attack": None,
            },
            "route_after": {
                "progress_kind": "unexplored_overlay_frontier",
                "nearest_hostile_manhattan": 8,
                "known_steps_to_attack": None,
            },
        }
        summary = victory.turn_action_summary([action])
        self.assertEqual(summary["action_count"], 1)
        self.assertEqual(summary["movement_count"], 1)
        self.assertEqual(summary["attack_count"], 1)
        self.assertEqual(summary["coordinate_changes"][0]["to"], [13, 22])
        self.assertEqual(
            summary["coordinate_changes"][0]["progress_kind"],
            "unexplored_overlay_frontier",
        )

    def test_alive_requires_consistent_runtime_fields(self) -> None:
        bald = unit(victory.BALD_GROUP, 0, 4, 7)
        self.assertTrue(victory.unit_alive(bald))
        self.assertFalse(victory.unit_alive({**bald, "hp": 0, "defeated": 1}))
        self.assertFalse(victory.unit_alive({**bald, "x": 0xFF, "y": 0xFF}))

    def test_source_has_required_acceptance_and_no_forbidden_mutators(self) -> None:
        source = Path(victory.__file__).read_text(encoding="utf-8")
        self.assertIn('"gst_role": "read_only_observation_only"', source)
        self.assertIn('"exact_bald_defeated"', source)
        self.assertIn('"stock_battle_result_retained"', source)
        self.assertIn('"stock_save_menu_records_scenario_2"', source)
        self.assertNotIn("activate_all_factions(", source)
        self.assertNotIn("set_all_factions_flag(", source)
        self.assertNotIn("restore_external_runtime_gst(", source)
        self.assertNotIn("write_bytes(", source)
        self.assertIn("fresh_hire_commander_", source)
        self.assertIn('recorder.send(["1"], delay=0.25)', source)
        self.assertIn('"live_move_overlay_coordinate"', source)
        self.assertIn('"stock_orange_cursor_retained"', source)
        self.assertIn('"raw_move_overlay_tinted"', source)
        self.assertIn(
            '"eligible_as_destination_without_raw_overlay_and_orange": False',
            source,
        )
        self.assertIn("recent player formation cycle detected", source)
        self.assertIn("cancel_move_and_standby_at_origin", source)
        self.assertIn("move_cancel_bare_map", source)
        self.assertIn("C at exact origin did not reopen command", source)
        self.assertIn("B did not return to exact-unit bare map", source)
        self.assertIn('if standby_row != 5:', source)
        self.assertIn('"stock_ui_only": True', source)


if __name__ == "__main__":
    unittest.main()
