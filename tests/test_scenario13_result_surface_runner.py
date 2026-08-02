from pathlib import Path
import tempfile
import unittest

from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario13_result_surface as runner


class Scenario13ResultSurfaceRunnerTests(unittest.TestCase):
    def test_checked_continuation_identity_is_current(self) -> None:
        self.assertTrue(runner.DEFAULT_CONTINUATION_GST.is_file())
        self.assertEqual(
            runner.shared.sha256(runner.DEFAULT_CONTINUATION_GST),
            runner.EXPECTED_CONTINUATION_SHA256,
        )

    def test_runtime_group_reads_vargas_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.gst"
            payload = bytearray(matrix.GST_WORK_RAM_FILE_OFFSET + 0x10000)
            record = (
                matrix.GST_WORK_RAM_FILE_OFFSET
                + matrix.RUNTIME_GROUP_BASE
                + runner.VARGAS_RUNTIME_GROUP * matrix.RUNTIME_GROUP_SIZE
            )
            payload[record : record + 8] = bytes.fromhex(
                "2D 0F 00 01 00 00 12 21"
            )
            path.write_bytes(payload)

            self.assertEqual(
                runner.runtime_group(path, runner.VARGAS_RUNTIME_GROUP),
                {
                    "group": 17,
                    "class_id": 0x2D,
                    "name_id": 0x0F,
                    "defeated_flag": 0,
                    "hp": 1,
                    "x": 18,
                    "y": 33,
                },
            )

    def test_keith_attack_navigation_targets_one_cell_left(self) -> None:
        calls = []

        class Recorder:
            def send(self, keys, delay=0.75):
                calls.append((list(keys), delay))

            def capture(self, relative):
                calls.append(("capture", relative))
                return Path(relative)

        target = runner.select_keith_attack(Recorder(), attempt=3)

        self.assertEqual(
            calls[0][0],
            ["b:0.6", "a:0.6", "a:0.6", "c:0.7"],
        )
        self.assertEqual(calls[1][0], ["down:0.5", "c:0.6", "left:0.5"])
        self.assertEqual(target, Path("battle/attempt_03_target_vargas.png"))

    def test_rng_retries_are_bounded_fresh_launches(self) -> None:
        self.assertGreaterEqual(runner.DEFAULT_ATTACK_ATTEMPTS, 3)
        self.assertGreater(runner.DEFAULT_RETRY_RNG_DELAY, 0)


if __name__ == "__main__":
    unittest.main()
