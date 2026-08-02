from pathlib import Path
from unittest import mock
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from tools import run_scenario27_ending_surface as runner
from tools import verify_scenario27_current_ending_surface as verifier


ROOT = Path(__file__).resolve().parents[1]


class Scenario27CurrentEndingSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = verifier.build_report()

    def test_report_passes_without_release_or_acceptance_promotion(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertFalse(self.report["release_promoted"])
        self.assertFalse(self.report["acceptance_updated"])

    def test_runner_bound_covers_the_observed_final_timed_epilogue(self):
        self.assertGreaterEqual(runner.DEFAULT_MAX_ENDING_FRAMES, 3400)

    def test_runner_retries_stock_combat_variance_from_retained_quicksave(self):
        self.assertGreaterEqual(runner.DEFAULT_ATTACK_ATTEMPTS, 4)
        self.assertGreater(runner.DEFAULT_RETRY_RNG_DELAY, 0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime"
            quicksave = runtime / ".local/share/blastem/probe/quicksave.gst"
            quicksave.parent.mkdir(parents=True)
            quicksave.write_bytes(b"miss-state")
            checkpoint = root / "pre-attack.gst"
            checkpoint.write_bytes(b"pre-attack-state")
            calls = []
            recorder = SimpleNamespace(
                runtime_home=runtime,
                send=lambda keys, delay: calls.append((keys, delay)),
            )

            runner.restore_quicksave(recorder, checkpoint, load_delay=0.25)

            self.assertEqual(quicksave.read_bytes(), b"pre-attack-state")
            self.assertEqual(calls, [(["load"], 0.25)])

    def test_battle_confirmations_stop_on_first_zero_hp_checkpoint(self):
        captures = []
        sends = []
        checkpoints = []

        class Recorder:
            def capture(self, relative):
                captures.append(relative)
                return Path(relative)

            def send(self, keys, delay):
                sends.append((keys, delay))

            def save_gst(self, relative):
                path = Path(relative)
                checkpoints.append(path)
                return path

        states = [
            {"hp": 10},
            {"hp": 1},
            {"hp": 0},
            {"hp": 0},
        ]
        with mock.patch.object(
            runner.shared,
            "image_report",
            side_effect=lambda path: {"path": str(path)},
        ), mock.patch.object(
            runner,
            "bernhardt_runtime_state",
            side_effect=states,
        ):
            frames, checkpoint, state, stop_frame = (
                runner.advance_battle_until_defeated(
                    Recorder(),
                    attempt=2,
                    max_frames=8,
                    battle_delay=0.2,
                )
            )

        self.assertEqual(stop_frame, 3)
        self.assertEqual(state["hp"], 0)
        self.assertEqual(len(frames), 3)
        self.assertEqual(len(captures), 3)
        self.assertEqual(len(sends), 3)
        self.assertEqual(len(checkpoints), 3)
        self.assertEqual(checkpoint, checkpoints[-1])

    def test_checked_report_is_current(self):
        subprocess.check_call(
            [
                sys.executable,
                str(ROOT / "tools/verify_scenario27_current_ending_surface.py"),
                "--check",
            ],
            cwd=ROOT,
        )

    def test_both_profiles_are_exact_focused_candidate_derivatives(self):
        for profile in ("normal", "hard"):
            row = self.report["profiles"][profile]
            self.assertEqual(row["status"], "pass")
            self.assertTrue(row["candidate"]["hash_matches"])
            self.assertTrue(row["candidate"]["checksum_matches"])
            probe = row["diagnostic_probe"]
            self.assertTrue(probe["hash_matches"])
            self.assertTrue(probe["checksum_matches"])
            self.assertTrue(probe["exact_rebuild"])
            self.assertEqual(probe["changed_byte_count_including_checksum"], 11)

    def test_fresh_runs_identify_scenario_and_defeat_only_staged_bernhardt(self):
        for profile in ("normal", "hard"):
            checks = self.report["profiles"][profile]["run_checks"]
            self.assertTrue(all(checks.values()), (profile, checks))
        self.assertTrue(self.report["automation"]["fresh_uninterrupted_runs_only"])
        self.assertFalse(self.report["automation"]["savestate_resume_accepted"])
        self.assertEqual(self.report["automation"]["fin_bound_frames"], 3200)

    def test_all_recorded_battle_and_ending_frames_are_hash_locked(self):
        expected = {
            "normal": (36, 34, 2957, 1124),
            "hard": (36, 34, 2960, 1126),
        }
        for profile, values in expected.items():
            battle_count, battle_unique, ending_count, ending_unique = values
            sequences = self.report["profiles"][profile]["sequences"]
            battle = sequences["battle"]
            ending = sequences["ending"]
            self.assertEqual(battle["frame_count"], battle_count)
            self.assertEqual(battle["unique_frame_hashes"], battle_unique)
            self.assertEqual(ending["frame_count"], ending_count)
            self.assertEqual(ending["unique_frame_hashes"], ending_unique)
            for row in (battle, ending):
                self.assertTrue(row["all_recorded_hashes_match_files"])
                self.assertEqual(row["sequence_digest"], row["expected_sequence_digest"])
                self.assertEqual(row["total_bytes"], row["expected_total_bytes"])

    def test_current_profiles_retain_historical_reviewed_ending_surfaces(self):
        for profile in ("normal", "hard"):
            matches = self.report["profiles"][profile]["historical_pixel_matches"]
            self.assertEqual(
                set(matches),
                {"montage", "scott", "lana", "bozel", "leon", "liana", "elwin", "fin"},
            )
            for row in matches.values():
                self.assertTrue(row["historical_hash_matches"])
                self.assertTrue(row["current_hash_matches"])

    def test_hard_keith_egbert_bernhardt_and_fin_manual_review_is_locked(self):
        review = self.report["manual_hard_review"]
        self.assertEqual(set(review), {"keith", "egbert", "bernhardt", "fin"})
        self.assertTrue(all(row["hash_matches"] for row in review.values()))
        self.assertIn("Korean text", review["egbert"]["review"])

    def test_profile_endpoints_share_clean_preparation_target_and_fin(self):
        cross = self.report["cross_profile"]
        self.assertTrue(cross["preparation_pixel_identical"])
        self.assertTrue(cross["turn1_command_pixel_identical"])
        self.assertTrue(cross["bernhardt_target_pixel_identical"])
        self.assertTrue(cross["fin_pixel_identical"])

    def test_fin_and_caption_detectors_do_not_confuse_title_or_epilogue(self):
        old_fin = ROOT / "captures/run/e93e_s27_ending_watch/875.png"
        current_fin = ROOT / "captures/run/current_s27_ending/hard/runtime01/ending/advance_2960.png"
        caption = ROOT / "captures/run/current_s27_ending/normal/runtime08/ending/advance_0154.png"
        title = ROOT / "captures/run/c7ab_s27_title.png"
        epilogue = ROOT / "captures/run/current_s27_ending/hard/runtime01/ending/advance_2360.png"
        self.assertTrue(runner.fin_visible(old_fin))
        self.assertTrue(runner.fin_visible(current_fin))
        self.assertFalse(runner.fin_visible(title))
        self.assertFalse(runner.fin_visible(epilogue))
        self.assertTrue(runner.ending_caption_visible(caption))
        self.assertFalse(runner.ending_caption_visible(current_fin))
        self.assertFalse(runner.ending_caption_visible(epilogue))


if __name__ == "__main__":
    unittest.main()
