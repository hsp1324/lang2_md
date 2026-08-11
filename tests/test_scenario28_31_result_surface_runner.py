from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import run_scenario28_31_result_surface as runner


ROOT = Path(__file__).resolve().parents[1]


class Scenario28To31ResultSurfaceRunnerTests(unittest.TestCase):
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
        self.assertEqual(runner.ATTACK_COMMANDER_CYCLES, {11: 2, 13: 5})
        self.assertEqual(runner.SCENARIO31_TARGET_GROUP, 10)

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

    def test_scenario13_vargas_retry_restores_after_a_stock_miss(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            root = Path(directory)

            class Recorder:
                def __init__(self) -> None:
                    self.output = root
                    self.runtime_home = root / "runtime"
                    self.runtime_home.mkdir()
                    (self.runtime_home / "quicksave.gst").write_bytes(b"seed")
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
                    payload = bytearray(
                        runner.matrix.GST_WORK_RAM_FILE_OFFSET + 0x10000
                    )
                    record = (
                        runner.matrix.GST_WORK_RAM_FILE_OFFSET
                        + runner.matrix.RUNTIME_GROUP_BASE
                        + runner.scenario13_result.VARGAS_RUNTIME_GROUP
                        * runner.matrix.RUNTIME_GROUP_SIZE
                    )
                    payload[record + 1] = 0x0F
                    payload[record + 3] = (
                        0 if "attempt_02" in relative else 1
                    )
                    path.write_bytes(payload)
                    return path

            recorder = Recorder()
            pre_attack = root / "pre.gst"
            pre_attack.write_bytes(b"pre")
            with (
                mock.patch.object(
                    runner,
                    "restore_quicksave",
                ) as restore,
                mock.patch.object(
                    runner,
                    "cast_magic_arrow_up",
                    return_value={"target": {"path": "target.png"}},
                ),
                mock.patch.object(
                    runner.shared,
                    "image_report",
                    side_effect=lambda path: {"path": str(path)},
                ),
                mock.patch.object(runner.time, "sleep"),
            ):
                attempts = runner.attack_scenario13_vargas_until_defeated(
                    recorder,
                    pre_attack=pre_attack,
                    commander_cycles=3,
                    attack_attempts=2,
                    retry_rng_delay=0,
                    battle_frames=1,
                    battle_delay=0,
                )

            self.assertEqual(len(attempts), 2)
            self.assertEqual(attempts[0]["vargas_runtime_state"]["hp"], 1)
            self.assertEqual(attempts[1]["vargas_runtime_state"]["hp"], 0)
            restore.assert_called_once_with(
                recorder,
                pre_attack,
                load_delay=1.2,
            )


if __name__ == "__main__":
    unittest.main()
