import json
from pathlib import Path
from unittest import mock
import tempfile
from types import SimpleNamespace
import unittest

from PIL import Image, ImageDraw

from tools import build_scenario27_ending_probe_rom as probe_builder
from tools import run_scenario27_ending_surface as runner
from tools import run_v137_final_gate as final_gate
from tools import verify_scenario27_current_ending_surface as verifier
from tools.rom_update import bps_apply
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario27CurrentEndingSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The large historical frame/GST corpus is intentionally no longer
        # tracked.  Keep its reviewed, hash-locked report as an archive and
        # leave current exact-ROM runtime acceptance to run_v137_final_gate.
        cls.report = json.loads(
            verifier.DEFAULT_OUTPUT.read_text(encoding="utf-8")
        )

    def test_report_passes_without_release_or_acceptance_promotion(self):
        self.assertEqual(self.report["status"], "pass")
        self.assertFalse(self.report["release_promoted"])
        self.assertFalse(self.report["acceptance_updated"])

    def test_runner_bound_covers_the_observed_final_timed_epilogue(self):
        self.assertGreaterEqual(runner.DEFAULT_MAX_ENDING_FRAMES, 3400)

    def test_runner_can_retry_from_the_retained_one_hp_quicksave(self):
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

    def test_runner_requires_the_probe_start_wrapper_one_hp_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pre-attack.gst"
            payload = bytearray(runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES)
            record = (
                runner.GST_WORK_RAM_OFFSET
                + (runner.RUNTIME_GROUP_BASE & 0xFFFF)
                + runner.BERNHARDT_RUNTIME_GROUP * runner.RUNTIME_GROUP_SIZE
            )
            payload[record] = 0x4E
            payload[record + 1] = 0x0E
            payload[record + runner.RUNTIME_HP_OFFSET] = 1
            payload[record + runner.RUNTIME_X_OFFSET] = 15
            payload[record + runner.RUNTIME_X_OFFSET + 1] = 15
            path.write_bytes(payload)

            state = runner.require_staged_bernhardt(path)
            self.assertEqual(state["hp"], 1)
            payload[record + runner.RUNTIME_HP_OFFSET] = 10
            path.write_bytes(payload)
            with self.assertRaisesRegex(RuntimeError, "Start wrapper"):
                runner.require_staged_bernhardt(path)

    def test_runner_explicitly_triggers_start_wrapper_before_attack(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def gst(name, hp):
                path = root / name
                payload = bytearray(
                    runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES
                )
                record = (
                    runner.GST_WORK_RAM_OFFSET
                    + (runner.RUNTIME_GROUP_BASE & 0xFFFF)
                    + runner.BERNHARDT_RUNTIME_GROUP
                    * runner.RUNTIME_GROUP_SIZE
                )
                payload[record] = 0x4E
                payload[record + 1] = 0x0E
                payload[record + runner.RUNTIME_HP_OFFSET] = hp
                payload[record + runner.RUNTIME_X_OFFSET] = 15
                payload[record + runner.RUNTIME_X_OFFSET + 1] = 15
                path.write_bytes(payload)
                return path

            states = [
                gst("before.gst", 10),
                gst("staged.gst", 1),
                gst("pre-attack.gst", 1),
            ]
            actions = []
            captures = []

            class Recorder:
                def save_gst(self, relative):
                    return states.pop(0)

                def send(self, keys, delay):
                    actions.append((keys, delay))

                def capture(self, relative):
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"capture")
                    captures.append(relative)
                    return path

            with mock.patch.object(
                runner.first_turn,
                "start_menu_cursor_row",
                return_value=0,
            ), mock.patch.object(
                runner.sequence,
                "battle_command_menu_visible",
                return_value=True,
            ):
                result = runner.trigger_and_verify_start_wrapper(Recorder())

            self.assertEqual(
                actions,
                [
                    (["b"], 0.8),
                    (["start"], 1.0),
                    (["b"], 0.8),
                    (["c"], 0.8),
                ],
            )
            self.assertEqual(
                captures,
                [
                    "battle/start_wrapper_menu.png",
                    "battle/turn1_command_staged.png",
                ],
            )
            self.assertEqual(result["action_sequence"], ["b", "start", "b", "c"])
            self.assertEqual(
                result["changed_record_offsets"],
                [runner.RUNTIME_HP_OFFSET],
            )
            self.assertEqual(result["before_state"]["hp"], 10)
            self.assertEqual(result["pre_attack_state"]["hp"], 1)

    def test_runner_rejects_a_no_wrapper_rom_after_the_start_action(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def gst(name):
                path = root / name
                payload = bytearray(
                    runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES
                )
                record = (
                    runner.GST_WORK_RAM_OFFSET
                    + (runner.RUNTIME_GROUP_BASE & 0xFFFF)
                    + runner.BERNHARDT_RUNTIME_GROUP
                    * runner.RUNTIME_GROUP_SIZE
                )
                payload[record] = 0x4E
                payload[record + 1] = 0x0E
                payload[record + runner.RUNTIME_HP_OFFSET] = 10
                payload[record + runner.RUNTIME_X_OFFSET] = 15
                payload[record + runner.RUNTIME_X_OFFSET + 1] = 15
                path.write_bytes(payload)
                return path

            states = [gst("before.gst"), gst("still-ten.gst")]
            actions = []

            class Recorder:
                def save_gst(self, relative):
                    return states.pop(0)

                def send(self, keys, delay):
                    actions.append(keys)

                def capture(self, relative):
                    path = root / "start-menu.png"
                    path.write_bytes(b"capture")
                    return path

            with mock.patch.object(
                runner.first_turn,
                "start_menu_cursor_row",
                return_value=0,
            ), self.assertRaisesRegex(RuntimeError, "Start wrapper"):
                runner.trigger_and_verify_start_wrapper(Recorder())

            self.assertEqual(actions, [["b"], ["start"]])

    def test_archived_report_is_complete_but_not_the_current_release_gate(self):
        self.assertEqual(self.report["schema_version"], 1)
        self.assertEqual(self.report["scenario"], 27)
        self.assertEqual(set(self.report["profiles"]), {"normal", "hard"})
        for profile in ("normal", "hard"):
            row = self.report["profiles"][profile]
            self.assertEqual(
                row["candidate"]["expected_sha256"],
                verifier.CANDIDATES[profile]["sha256"],
            )
            self.assertEqual(
                row["diagnostic_probe"]["expected_sha256"],
                verifier.PROBES[profile]["sha256"],
            )
            self.assertEqual(
                row["evidence_json"]["expected_sha256"],
                verifier.RUNS[profile]["evidence_sha256"],
            )

        phase = final_gate.PHASE_BY_ID["scenario27_final_and_ending"]
        self.assertEqual(phase.expected_pass_count, 36)
        self.assertEqual(
            phase.acceptance_units,
            {
                "ending_to_fin": 3,
                "final_enemy_fixed_record": 30,
                "x4_to_s27_save_transition": 3,
            },
        )
        self.assertEqual(final_gate.FULL_ROUTE_ORDER[-2:], (31, 27))
        self.assertEqual(final_gate.NEXT_SCENARIO[31], 27)

    def test_exact_v137_scenario27_probes_are_reproducible_and_identity_safe(self):
        source = final_gate.DEFAULT_SOURCE_ROM.read_bytes()
        manifest = json.loads(
            (ROOT / "patches/v1.3.7.json").read_text(encoding="utf-8")
        )
        expected_profiles = {"pure", "normal", "hard"}
        self.assertEqual(
            {row["id"] for row in manifest["targets"]},
            expected_profiles,
        )
        source_layout = scenario_layout(source, 27)
        self.assertEqual(source_layout.record_count, 10)
        bernhardt = (
            source_layout.records_offset
            + probe_builder.BERNHARDT_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        allowed = {
            0x18E,
            0x18F,
            *range(
                probe_builder.START_MENU_ENTRY_OPERAND,
                probe_builder.START_MENU_ENTRY_OPERAND + 4,
            ),
            *range(
                probe_builder.RUNTIME_WRAPPER,
                probe_builder.RUNTIME_WRAPPER
                + len(probe_builder.completion_hp_wrapper_code()),
            ),
            bernhardt + FIELD_OFFSETS["at"],
            bernhardt + FIELD_OFFSETS["df"],
            bernhardt + FIELD_OFFSETS["x"],
            bernhardt + FIELD_OFFSETS["y"],
            *(
                bernhardt + FIELD_OFFSETS["mercenaries"] + index
                for index in range(6)
            ),
        }
        already_adjacent_x = bernhardt + FIELD_OFFSETS["x"]
        unchanged_start_operand = probe_builder.START_MENU_ENTRY_OPERAND
        unchanged_wrapper_bytes = {
            probe_builder.RUNTIME_WRAPPER + index
            for index, value in enumerate(
                probe_builder.completion_hp_wrapper_code()
            )
            if value == 0xFF
        }
        expected_changed = allowed - {
            already_adjacent_x,
            unchanged_start_operand,
            *unchanged_wrapper_bytes,
        }
        for row in manifest["targets"]:
            profile = row["id"]
            release = bps_apply(
                (ROOT / "patches" / row["patch_filename"]).read_bytes(),
                source,
            )
            probe = bytearray(release)
            probe_builder.patch_probe(
                probe,
                source,
                allow_balanced_input=profile == "hard",
            )
            changed = {
                offset
                for offset, (before, after) in enumerate(zip(release, probe))
                if before != after
            }
            with self.subTest(profile=profile):
                # Stock Bernhardt is already at X=15. The high byte of both
                # Start operands and FF bytes embedded in the wrapper are also
                # intentional no-ops; every other declared byte changes.
                self.assertEqual(changed, expected_changed)
                self.assertEqual(scenario_layout(probe, 27), source_layout)
                for index in range(source_layout.record_count):
                    start = source_layout.records_offset + index * FIXED_RECORD_SIZE
                    protected = {
                        relative
                        for relative in range(FIXED_RECORD_SIZE)
                        if start + relative not in allowed
                    }
                    self.assertTrue(
                        all(
                            probe[start + relative]
                            == release[start + relative]
                            for relative in protected
                        )
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
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fin = root / "fin.png"
            fin.write_bytes(b"fresh exact-runtime Fin frame")
            with mock.patch.object(
                runner.shared,
                "sha256",
                return_value=runner.FIN_SHA256,
            ):
                self.assertTrue(runner.fin_visible(fin))
            with mock.patch.object(
                runner.shared,
                "sha256",
                return_value="0" * 64,
            ):
                self.assertFalse(runner.fin_visible(fin))

            caption = Image.new("RGB", (320, 240), "black")
            draw = ImageDraw.Draw(caption)
            draw.rectangle((20, 190, 45, 198), fill="white")
            caption_path = root / "caption.png"
            caption.save(caption_path)
            self.assertTrue(runner.ending_caption_visible(caption_path))

            title = Image.new("RGB", (320, 240), "black")
            draw = ImageDraw.Draw(title)
            draw.rectangle((20, 20, 300, 35), fill="white")
            title_path = root / "title.png"
            title.save(title_path)
            self.assertFalse(runner.ending_caption_visible(title_path))

    def test_moving_cinematic_caption_match_is_not_confirmed(self):
        for stable_frames in range(runner.STATIC_CAPTION_CONFIRM_FRAMES):
            self.assertFalse(
                runner.should_confirm_ending_surface(
                    dialogue=False,
                    caption=True,
                    stable_caption_frames=stable_frames,
                )
            )
        self.assertTrue(
            runner.should_confirm_ending_surface(
                dialogue=False,
                caption=True,
                stable_caption_frames=runner.STATIC_CAPTION_CONFIRM_FRAMES,
            )
        )
        self.assertTrue(
            runner.should_confirm_ending_surface(
                dialogue=True,
                caption=False,
                stable_caption_frames=0,
            )
        )


if __name__ == "__main__":
    unittest.main()
