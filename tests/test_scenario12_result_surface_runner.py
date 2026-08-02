from pathlib import Path
import tempfile
import unittest

from tools import run_scenario12_result_surface as runner
from tools import run_preparation_surface_matrix as matrix


class Scenario12ResultSurfaceRunnerTests(unittest.TestCase):
    def test_checked_continuation_identity_is_current(self) -> None:
        self.assertTrue(runner.DEFAULT_CONTINUATION_GST.is_file())
        self.assertEqual(
            runner.shared.sha256(runner.DEFAULT_CONTINUATION_GST),
            runner.EXPECTED_CONTINUATION_SHA256,
        )

    def test_runtime_group_reads_only_requested_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.gst"
            payload = bytearray(matrix.GST_WORK_RAM_FILE_OFFSET + 0x10000)
            record = (
                matrix.GST_WORK_RAM_FILE_OFFSET
                + matrix.RUNTIME_GROUP_BASE
                + runner.FINAL_LIVING_ARMOR_RUNTIME_GROUP
                * matrix.RUNTIME_GROUP_SIZE
            )
            payload[record : record + 8] = bytes.fromhex(
                "59 49 00 0A 00 00 17 08"
            )
            path.write_bytes(payload)

            self.assertEqual(
                runner.runtime_group(
                    path,
                    runner.FINAL_LIVING_ARMOR_RUNTIME_GROUP,
                ),
                {
                    "group": 9,
                    "class_id": 0x59,
                    "name_id": 0x49,
                    "defeated_flag": 0,
                    "hp": 10,
                    "x": 23,
                    "y": 8,
                },
            )

    def test_sherry_attack_navigation_targets_one_cell_right(self) -> None:
        calls = []

        class Recorder:
            def send(self, keys, delay=0.75):
                calls.append((list(keys), delay))

            def capture(self, relative):
                calls.append(("capture", relative))
                return Path(relative)

        target = runner.select_sherry_attack(Recorder(), round_number=2)

        self.assertEqual(
            calls[0][0],
            ["b:0.5", "a:0.5", "a:0.8", "c:0.5"],
        )
        self.assertEqual(calls[1][0], ["down:0.5", "c:0.6", "right:0.5"])
        self.assertEqual(
            target,
            Path("battle/round_02_target_living_armor.png"),
        )


if __name__ == "__main__":
    unittest.main()
