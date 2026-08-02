from pathlib import Path
import tempfile
import unittest

from tools import run_preparation_surface_matrix as matrix
from tools import run_scenario18_20_result_surface as runner


class Scenario18To20ResultSurfaceRunnerTests(unittest.TestCase):
    def test_checked_continuation_identities_are_current(self) -> None:
        for scenario in runner.SCENARIOS:
            for profile in ("normal", "hard"):
                seed = runner.default_seed(scenario, profile)
                self.assertTrue(seed.is_file())
                self.assertEqual(
                    runner.sha256(seed),
                    runner.expected_seed_sha256(scenario, profile),
                )

    def test_scenario19_hard_uses_one_hp_continuation(self) -> None:
        normal = runner.default_seed(19, "normal")
        hard = runner.default_seed(19, "hard")
        self.assertNotEqual(normal, hard)
        self.assertEqual(runner.runtime_group(normal, 10)["hp"], 10)
        self.assertEqual(runner.runtime_group(hard, 10)["hp"], 1)

    def test_runtime_group_reads_boss_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.gst"
            payload = bytearray(runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES)
            record = (
                runner.GST_WORK_RAM_OFFSET
                + (matrix.RUNTIME_GROUP_BASE & 0xFFFF)
                + 13 * matrix.RUNTIME_GROUP_SIZE
            )
            payload[record:record + 8] = bytes.fromhex(
                "5D 73 00 0A 00 00 16 17"
            )
            path.write_bytes(payload)
            self.assertEqual(
                runner.runtime_group(path, 13),
                {
                    "group": 13,
                    "class_id": 0x5D,
                    "name_id": 0x73,
                    "defeated_flag": 0,
                    "hp": 10,
                    "x": 22,
                    "y": 23,
                },
            )

    def test_every_boss_identity_matches_its_seed(self) -> None:
        for scenario, definition in runner.SCENARIOS.items():
            for profile in ("normal", "hard"):
                state = runner.runtime_group(
                    runner.default_seed(scenario, profile),
                    int(definition["boss_group"]),
                )
                self.assertEqual(state["class_id"], definition["boss_class"])
                self.assertEqual(state["name_id"], definition["boss_name"])
                self.assertEqual(state["hp"], definition["initial_hp"][profile])
                self.assertEqual(
                    (state["x"], state["y"]),
                    tuple(definition["boss_position"]),
                )

    def test_scenario20_reenters_elwin_attack_before_target_confirm(self) -> None:
        calls = []

        class Recorder:
            def send(self, keys, delay=0.75):
                calls.append((list(keys), delay))

            def capture(self, relative):
                calls.append(("capture", relative))
                return Path(relative)

        target = runner.begin_final_battle(
            Recorder(),
            scenario=20,
            loaded=Path("loaded.png"),
        )
        self.assertEqual(
            calls[0][0],
            ["b:0.6", "c:0.7", "down:0.6", "c:0.7", "down:0.6"],
        )
        self.assertEqual(calls[-1], (["c"], 0.45))
        self.assertEqual(target, Path("battle/fias_attack_target.png"))

    def test_scenario18_and_19_confirm_retained_attack_target(self) -> None:
        calls = []

        class Recorder:
            def send(self, keys, delay=0.75):
                calls.append((list(keys), delay))

        loaded = Path("loaded.png")
        target = runner.begin_final_battle(
            Recorder(),
            scenario=19,
            loaded=loaded,
        )
        self.assertEqual(target, loaded)
        self.assertEqual(calls, [(["c"], 0.45)])


if __name__ == "__main__":
    unittest.main()
