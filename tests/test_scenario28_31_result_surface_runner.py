from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import run_scenario28_31_result_surface as runner


ROOT = Path(__file__).resolve().parents[1]


class Scenario28To31ResultSurfaceRunnerTests(unittest.TestCase):
    def test_scenario13_actor_wrapper_proves_exact_live_identity(self) -> None:
        wrapper = {"gst": "tmp/scenario13-wrapper.gst"}
        actor = {
            "group": runner.scenario13_probe.ZORUM_RUNTIME_GROUP,
            "class_id": 0x3A,
            "name_id": runner.scenario13_probe.ZORUM_NAME_ID,
            "defeated_flag": 0,
            "hp": 1,
            "x": 18,
            "y": 30,
        }
        recorder = object()
        with (
            mock.patch.object(
                runner,
                "trigger_completion_wrapper",
                return_value=wrapper,
            ) as trigger,
            mock.patch.object(
                runner.scenario13_result,
                "runtime_group",
                return_value=actor,
            ) as runtime_group,
        ):
            result = runner.trigger_scenario13_actor_wrapper(
                recorder,
                phase="zorum",
                runtime_group=runner.scenario13_probe.ZORUM_RUNTIME_GROUP,
                expected_name_id=runner.scenario13_probe.ZORUM_NAME_ID,
                expected_class_id=0x3A,
                expected_position=(18, 30),
            )

        self.assertEqual(result, (wrapper, actor))
        trigger.assert_called_once_with(
            recorder,
            scenario=13,
            phase="zorum",
        )
        runtime_group.assert_called_once_with(
            ROOT / "tmp/scenario13-wrapper.gst",
            runner.scenario13_probe.ZORUM_RUNTIME_GROUP,
        )

    def test_scenario13_actor_wrapper_rejects_identity_and_liveness_mutations(
        self,
    ) -> None:
        baseline = {
            "group": runner.scenario13_probe.ZORUM_RUNTIME_GROUP,
            "class_id": 0x3A,
            "name_id": runner.scenario13_probe.ZORUM_NAME_ID,
            "defeated_flag": 0,
            "hp": 1,
            "x": 18,
            "y": 30,
        }
        mutations = {
            "class": {"class_id": 0x39},
            "name": {"name_id": 0x12},
            "defeated": {"defeated_flag": 0x80},
            "hp": {"hp": 10},
            "hidden_x": {"x": 0xFF},
            "hidden_y": {"y": 0xFF},
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                actor = baseline | mutation
                with (
                    mock.patch.object(
                        runner,
                        "trigger_completion_wrapper",
                        return_value={"gst": "tmp/scenario13-wrapper.gst"},
                    ),
                    mock.patch.object(
                        runner.scenario13_result,
                        "runtime_group",
                        return_value=actor,
                    ),
                    self.assertRaisesRegex(RuntimeError, "HP wrapper failed"),
                ):
                    runner.trigger_scenario13_actor_wrapper(
                        object(),
                        phase="zorum",
                        runtime_group=(
                            runner.scenario13_probe.ZORUM_RUNTIME_GROUP
                        ),
                        expected_name_id=runner.scenario13_probe.ZORUM_NAME_ID,
                        expected_class_id=0x3A,
                        expected_position=(18, 30),
                    )

    def test_runner_covers_fresh_completion_late_scenarios(self) -> None:
        self.assertEqual(
            runner.SCENARIOS,
            (11, 12, 13, 18, 19, 20, 28, 29, 30, 31),
        )
        self.assertEqual(
            runner.ATTACK_DIRECTIONS,
            {
                11: "right",
                12: "up",
                13: "up",
                18: "up",
                19: "down",
                20: "down",
                28: "up",
                29: "up",
                30: "up",
            },
        )
        # Scenario 11 derives its cycle count from the live cursor because a
        # standalone seed starts on Lester while an S10 save starts on Elwin.
        self.assertEqual(runner.ATTACK_COMMANDER_CYCLES, {13: 5})
        self.assertEqual(runner.SCENARIO31_TARGET_GROUP, 10)
        self.assertEqual(
            runner.NEXT_SCENARIO,
            {
                11: 12,
                12: 13,
                13: 14,
                18: 19,
                19: 20,
                20: 21,
                28: 13,
                29: 20,
                30: 23,
                31: 27,
            },
        )

    def test_scenario31_target_state_reads_the_single_completion_record(self) -> None:
        payload = bytearray(runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES)
        record = (
            runner.GST_WORK_RAM_OFFSET
            + runner.RUNTIME_GROUP_BASE
            + runner.SCENARIO31_TARGET_GROUP * runner.RUNTIME_GROUP_SIZE
        )
        payload[record] = 0x3E
        payload[record + 1] = 0x0C
        payload[record + runner.RUNTIME_DEFEATED_FLAG_OFFSET] = 0x80
        payload[record + runner.RUNTIME_HP_OFFSET] = 0
        payload[record + 0x06] = 14
        payload[record + 0x07] = 60
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            state = Path(directory) / "scenario31.gst"
            state.write_bytes(payload)
            self.assertEqual(
                runner.scenario31_target_state(state),
                {
                    "class_id": 0x3E,
                    "name_id": 0x0C,
                    "defeated_flag": 0x80,
                    "defeated": True,
                    "hp": 0,
                    "x": 14,
                    "y": 60,
                },
            )

    def test_scenario11_completion_states_reads_prior_and_final_groups(self) -> None:
        payload = bytearray(runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES)
        for group in runner.scenario11_probe.COMPLETION_DEFEATED_RUNTIME_GROUPS:
            record = (
                runner.GST_WORK_RAM_OFFSET
                + runner.RUNTIME_GROUP_BASE
                + group * runner.RUNTIME_GROUP_SIZE
            )
            payload[record + 2] = 0x80
            payload[record + 6] = 0xFF
        target_group = (
            runner.scenario11_probe.PLAYER_DEPLOYMENT_COUNT
            + runner.scenario11_probe.COMPLETION_TARGET_RECORD_INDEX
        )
        record = (
            runner.GST_WORK_RAM_OFFSET
            + runner.RUNTIME_GROUP_BASE
            + target_group * runner.RUNTIME_GROUP_SIZE
        )
        payload[record] = runner.scenario11_probe.COMPLETION_TARGET_CLASS_ID
        payload[record + 1] = runner.scenario11_probe.COMPLETION_TARGET_NAME_ID
        payload[record + 3] = 1
        payload[record + 6] = 20
        payload[record + 7] = 20
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            state = Path(directory) / "scenario11.gst"
            state.write_bytes(payload)
            result = runner.scenario11_completion_states(state)
        self.assertEqual(len(result["prior_groups"]), 9)
        self.assertTrue(
            all(group["defeated_flag"] == 0x80 for group in result["prior_groups"])
        )
        self.assertEqual(
            result["target"],
            {
                "group": target_group,
                "class_id": runner.scenario11_probe.COMPLETION_TARGET_CLASS_ID,
                "name_id": runner.scenario11_probe.COMPLETION_TARGET_NAME_ID,
                "defeated_flag": 0,
                "hp": 1,
                "x": 20,
                "y": 20,
            },
        )

    def test_scenario11_attack_selection_handles_lester_and_elwin_starts(self) -> None:
        payload = bytearray(runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES)
        groups = (
            (0x01, 18, 20),
            (0x05, 17, 20),
            (runner.SCENARIO11_ATTACKER_NAME_ID, 19, 20),
            (0x08, 18, 19),
            (0x07, 17, 19),
            (0x09, 19, 19),
        )
        for group, (name_id, x, y) in enumerate(groups):
            record = (
                runner.GST_WORK_RAM_OFFSET
                + runner.RUNTIME_GROUP_BASE
                + group * runner.RUNTIME_GROUP_SIZE
            )
            payload[record + 1] = name_id
            payload[record + runner.RUNTIME_HP_OFFSET] = 10
            payload[record + runner.RUNTIME_X_OFFSET] = x
            payload[record + runner.RUNTIME_Y_OFFSET] = y

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            state = Path(directory) / "scenario11.gst"
            cursor = runner.GST_WORK_RAM_OFFSET + runner.SCENARIO11_CURSOR_X
            payload[cursor] = 19
            payload[cursor + 2] = 19
            state.write_bytes(payload)
            lester_start = runner.scenario11_attack_selection(state)

            payload[cursor] = 18
            payload[cursor + 2] = 20
            state.write_bytes(payload)
            elwin_start = runner.scenario11_attack_selection(state)

        self.assertEqual(lester_start["selected"]["name_id"], 0x09)
        self.assertEqual(lester_start["cycle_count"], 3)
        self.assertEqual(elwin_start["selected"]["name_id"], 0x01)
        self.assertEqual(elwin_start["cycle_count"], 2)
        self.assertEqual(elwin_start["target"]["name_id"], 0x04)

    def test_attack_waits_through_blank_transition_before_confirming_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            output = Path(directory)

            class Recorder:
                def __init__(self) -> None:
                    self.output = output
                    self.sent = []
                    self.capture_count = 0

                def send(self, keys, *, delay):
                    self.sent.append((keys, delay))

                def capture(self, relative):
                    path = self.output / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(bytes((self.capture_count,)))
                    self.capture_count += 1
                    return path

            recorder = Recorder()
            with (
                mock.patch.object(
                    runner.sequence,
                    "battle_map_surface_visible",
                    side_effect=(False, True),
                ),
                mock.patch.object(
                    runner.sequence,
                    "battle_command_menu_visible",
                    side_effect=(False, False),
                ),
                mock.patch.object(
                    runner.shared,
                    "image_report",
                    side_effect=lambda path: {"path": str(path)},
                ),
                mock.patch.object(runner.time, "sleep"),
            ):
                result = runner.attack_up(
                    recorder,
                    phase="second",
                    target_checks=2,
                    target_delay=0,
                )

            self.assertEqual(result["target_frame"], 1)
            self.assertEqual(len(result["target_observations"]), 2)
            self.assertEqual(
                recorder.sent,
                [
                    (["down"], 0.7),
                    (["c"], 0.8),
                    (["up"], 0.7),
                    (["c"], 1.4),
                ],
            )
            self.assertEqual(
                (output / "battle/second_target.png").read_bytes(),
                b"\x01",
            )

    def test_scenario13_vargas_miss_fails_closed_without_in_process_retry(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)

            def vargas_gst(path: Path, hp: int) -> None:
                payload = bytearray(
                    runner.matrix.GST_WORK_RAM_FILE_OFFSET + 0x10000
                )
                record = (
                    runner.matrix.GST_WORK_RAM_FILE_OFFSET
                    + runner.matrix.RUNTIME_GROUP_BASE
                    + runner.scenario13_result.VARGAS_RUNTIME_GROUP
                    * runner.matrix.RUNTIME_GROUP_SIZE
                )
                payload[record] = runner.scenario13_probe.COMPLETION_VARGAS_CLASS
                payload[record + 1] = runner.scenario13_probe.VARGAS_NAME_ID
                payload[record + 3] = hp
                payload[record + 6] = (
                    runner.scenario13_result.EXPECTED_VARGAS_POSITION[0]
                )
                payload[record + 7] = (
                    runner.scenario13_result.EXPECTED_VARGAS_POSITION[1]
                )
                path.write_bytes(payload)

            class Recorder:
                def __init__(self) -> None:
                    self.output = root
                    self.sent = []

                def send(self, keys, *, delay):
                    self.sent.append((keys, delay))

                def capture(self, relative):
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"frame")
                    return path

                def save_gst(self, relative):
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    vargas_gst(path, 1)
                    return path

            recorder = Recorder()
            pre_attack = root / "pre.gst"
            vargas_gst(pre_attack, 1)
            with (
                mock.patch.object(
                    runner,
                    "cast_magic_arrow_up",
                    return_value={"target": {"path": "target.png"}},
                ) as cast,
                mock.patch.object(
                    runner.shared,
                    "image_report",
                    side_effect=lambda path: {"path": str(path)},
                ),
                self.assertRaisesRegex(
                    RuntimeError,
                    "fresh BlastEm process",
                ),
            ):
                runner.attack_scenario13_vargas_once(
                    recorder,
                    pre_attack=pre_attack,
                    commander_cycles=3,
                    rng_idle_delay=0,
                    battle_frames=1,
                    battle_delay=0,
                )

            cast.assert_called_once_with(
                recorder,
                phase="vargas",
                confirm_idle_delay=0,
            )
            self.assertNotIn("load", [key for keys, _ in recorder.sent for key in keys])

    def test_scenario31_miss_fails_closed_without_in_process_retry(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)

            def target_gst(path: Path, hp: int) -> None:
                payload = bytearray(runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES)
                record = (
                    runner.GST_WORK_RAM_OFFSET
                    + runner.RUNTIME_GROUP_BASE
                    + runner.SCENARIO31_TARGET_GROUP * runner.RUNTIME_GROUP_SIZE
                )
                payload[record] = 0x4E
                payload[record + 1] = 0x0E
                payload[record + runner.RUNTIME_HP_OFFSET] = hp
                payload[record + runner.RUNTIME_X_OFFSET] = (
                    runner.scenario31_probe.COMPLETION_ACTIVE_POSITION[0]
                )
                payload[record + runner.RUNTIME_Y_OFFSET] = (
                    runner.scenario31_probe.COMPLETION_ACTIVE_POSITION[1]
                )
                path.write_bytes(payload)

            class Recorder:
                def __init__(self) -> None:
                    self.sent = []

                def send(self, keys, *, delay):
                    self.sent.append((keys, delay))

                def capture(self, relative):
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"frame")
                    return path

                def save_gst(self, relative):
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    target_gst(path, runner.scenario31_probe.COMPLETION_HP)
                    return path

            recorder = Recorder()
            with (
                mock.patch.object(
                    runner.shared,
                    "image_report",
                    side_effect=lambda path: {"path": str(path)},
                ),
                self.assertRaisesRegex(
                    RuntimeError,
                    "fresh BlastEm process",
                ),
            ):
                runner.attack_scenario31_once(
                    recorder,
                    rng_idle_delay=0,
                    battle_frames=1,
                    battle_delay=0,
                )

            self.assertNotIn("load", [key for keys, _ in recorder.sent for key in keys])


if __name__ == "__main__":
    unittest.main()
