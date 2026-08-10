from pathlib import Path
import tempfile
import unittest

from tools import run_scenario28_31_result_surface as runner


ROOT = Path(__file__).resolve().parents[1]


class Scenario28To31ResultSurfaceRunnerTests(unittest.TestCase):
    def test_runner_covers_the_four_late_scenarios(self) -> None:
        self.assertEqual(runner.SCENARIOS, (28, 29, 30, 31))
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


if __name__ == "__main__":
    unittest.main()
