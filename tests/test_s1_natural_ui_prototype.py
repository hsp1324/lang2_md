from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools import run_s1_natural_ui_prototype as prototype


class S1NaturalUiPrototypeTests(unittest.TestCase):
    def test_rejects_physical_or_ambiguous_display(self) -> None:
        for display in (":0", ":99", "wayland-0", ""):
            with self.subTest(display=display):
                with self.assertRaises(ValueError):
                    prototype.require_isolated_display(display)
        prototype.require_isolated_display(":100")
        prototype.require_isolated_display(":985.0")

    def test_fresh_launcher_has_no_state_or_sram_input(self) -> None:
        command = prototype.fresh_launch_command(
            rom=Path("candidate.md"),
            runtime_name="fresh",
            runtime_root=Path("runtime"),
            display=":985",
            initial_delay=1.0,
        )
        self.assertIn("scenario", command)
        self.assertIn("--replace-existing", command)
        self.assertTrue(
            prototype.FORBIDDEN_LAUNCH_TOKENS.isdisjoint(command)
        )

    def test_rejects_every_forbidden_launcher_token(self) -> None:
        base = ["python", "runner", "scenario", "--replace-existing"]
        for token in prototype.FORBIDDEN_LAUNCH_TOKENS:
            with self.subTest(token=token):
                with self.assertRaisesRegex(ValueError, "forbidden input"):
                    prototype.validate_fresh_launch_command([*base, token])

    def test_destination_is_unoccupied_safe_and_strictly_closer(self) -> None:
        selected = prototype.choose_advance_destination(
            reachable=((11, 17), (10, 16), (9, 15), (8, 14), (7, 13)),
            origin=(11, 17),
            occupied={(8, 14)},
            objective=(4, 7),
            hostiles={(7, 12), (16, 12)},
            require_safe_standby=True,
        )
        self.assertEqual(selected, (9, 15))
        self.assertLess(
            prototype.manhattan(selected, (4, 7)),
            prototype.manhattan((11, 17), (4, 7)),
        )
        self.assertGreater(prototype.manhattan(selected, (7, 12)), 1)

    def test_candidates_are_ordered_for_fail_closed_live_retry(self) -> None:
        candidates = prototype.advance_destination_candidates(
            reachable=((11, 15), (10, 16), (10, 17), (11, 17)),
            origin=(11, 17),
            occupied=set(),
            objective=(4, 7),
            hostiles={(16, 12)},
            require_safe_standby=True,
        )
        self.assertEqual(candidates, [(11, 15), (10, 16), (10, 17)])

    def test_destination_fails_closed_without_progress(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no unoccupied safe cell"):
            prototype.choose_advance_destination(
                reachable=((11, 17), (12, 18)),
                origin=(11, 17),
                occupied=set(),
                objective=(4, 7),
                hostiles=set(),
                require_safe_standby=True,
            )

    def test_destination_fails_closed_if_only_adjacent_to_hostile(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no unoccupied safe cell"):
            prototype.choose_advance_destination(
                reachable=((10, 16),),
                origin=(11, 17),
                occupied=set(),
                objective=(4, 7),
                hostiles={(10, 15)},
                require_safe_standby=True,
            )

    def test_unit_delta_is_keyed_and_deterministic(self) -> None:
        before = [{
            "group_index": 10,
            "member_index": 0,
            "class_id": 0x2E,
            "name_id": 0x12,
            "acted_flag": 0,
            "hp": 10,
            "x": 4,
            "y": 7,
        }]
        after = [{**before[0], "x": 4, "y": 4}]
        self.assertEqual(
            prototype.unit_delta(before, after),
            [{
                "group_index": 10,
                "member_index": 0,
                "before": before[0],
                "after": after[0],
            }],
        )

    def test_dialogue_tracker_confirms_only_stable_completed_page(self) -> None:
        tracker = prototype.DialoguePageTracker()
        incomplete = bytes([0]) * 100
        typing = bytes([1]) * 10 + bytes([0]) * 90
        complete = bytes([1]) * 30 + bytes([0]) * 70
        self.assertEqual(
            tracker.observe_dialogue(incomplete), "waiting_for_stability"
        )
        self.assertEqual(
            tracker.observe_dialogue(typing), "waiting_for_stability"
        )
        self.assertEqual(
            tracker.observe_dialogue(complete), "waiting_for_stability"
        )
        self.assertEqual(
            tracker.observe_dialogue(complete), "confirm_stable_page"
        )

    def test_dialogue_tracker_requires_observed_page_advance(self) -> None:
        tracker = prototype.DialoguePageTracker(retry_frames=2)
        first = bytes([1]) * 30 + bytes([0]) * 70
        second = bytes([0]) * 30 + bytes([1]) * 30 + bytes([0]) * 40
        tracker.observe_dialogue(first)
        self.assertEqual(
            tracker.observe_dialogue(first), "confirm_stable_page"
        )
        self.assertEqual(
            tracker.observe_dialogue(first), "waiting_for_page_advance"
        )
        self.assertEqual(
            tracker.observe_dialogue(first), "retry_confirmation"
        )
        self.assertEqual(
            tracker.observe_dialogue(second), "page_advanced_by_text_change"
        )
        self.assertEqual(tracker.page_advance_count, 1)
        self.assertEqual(
            tracker.observe_dialogue(second), "confirm_stable_page"
        )
        self.assertEqual(
            tracker.observe_non_dialogue(),
            "page_advanced_by_dialogue_disappearance",
        )
        self.assertEqual(tracker.page_advance_count, 2)

    def test_surface_tracker_requires_consecutive_frames(self) -> None:
        tracker = prototype.StableSurfaceTracker(required=2)
        self.assertFalse(tracker.observe("battle_map"))
        self.assertFalse(tracker.observe("turn_command"))
        self.assertTrue(tracker.observe("turn_command"))
        tracker.reset()
        self.assertFalse(tracker.observe("turn_command"))

    def test_rom_hash_guard_records_phase_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rom.md"
            path.write_bytes(b"exact candidate")
            expected = prototype.sha256(path)
            checkpoints: list[dict[str, str]] = []
            prototype.require_exact_rom(path, expected, "before", checkpoints)
            self.assertEqual(checkpoints, [{
                "phase": "before",
                "sha256": expected,
            }])
            with self.assertRaisesRegex(RuntimeError, "exact ROM changed"):
                prototype.require_exact_rom(
                    path, "0" * 64, "after", checkpoints
                )

    def test_source_declares_bounded_non_claims_and_no_cheat_api(self) -> None:
        source = Path(prototype.__file__).read_text(encoding="utf-8")
        self.assertIn('"scenario_1_victory_proven": False', source)
        self.assertIn('"full_campaign_autoplay_proven": False', source)
        self.assertIn('"stock_cheat_used": False', source)
        self.assertNotIn("activate_all_factions(", source)
        self.assertNotIn("set_all_factions_flag(", source)
        self.assertNotIn("recover_manual_slot_from_gst(", source)
        self.assertNotIn("blastem_exact_savestate_command(", source)


if __name__ == "__main__":
    unittest.main()
