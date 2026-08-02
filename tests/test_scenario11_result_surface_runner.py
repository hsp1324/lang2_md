from pathlib import Path
import unittest

from tools import build_scenario11_clear_probe_rom as probe_builder
from tools import run_scenario01_09_result_surface as early
from tools import run_scenario11_result_surface as runner


class Scenario11ResultSurfaceRunnerTests(unittest.TestCase):
    def test_checked_continuation_identity_and_positions_are_current(self) -> None:
        self.assertTrue(runner.DEFAULT_SEED_GST.is_file())
        self.assertEqual(
            runner.shared.sha256(runner.DEFAULT_SEED_GST),
            runner.EXPECTED_SEED_SHA256,
        )
        sherry = early.runtime_group(
            runner.DEFAULT_SEED_GST,
            probe_builder,
            runner.SHERRY_RUNTIME_GROUP,
        )
        target = early.runtime_group(
            runner.DEFAULT_SEED_GST,
            probe_builder,
            runner.FINAL_REINFORCEMENT_GROUP,
        )
        self.assertEqual((sherry["x"], sherry["y"]), runner.SHERRY_POSITION)
        self.assertEqual(
            (target["x"], target["y"]),
            runner.FINAL_REINFORCEMENT_POSITION,
        )
        self.assertGreater(target["hp"], 0)

    def test_final_battle_opens_attack_and_targets_right(self) -> None:
        calls = []

        class Recorder:
            def send(self, keys, delay=0.75):
                calls.append((list(keys), delay))

            def capture(self, relative):
                calls.append(("capture", relative))
                return Path(relative)

        target = runner.begin_final_battle(Recorder())
        self.assertEqual(
            calls,
            [
                (["c"], 0.8),
                (["down"], 0.55),
                (["c"], 0.8),
                (["right"], 0.7),
                ("capture", "battle/final_reinforcement_target.png"),
                (["c"], 1.4),
            ],
        )
        self.assertEqual(target, Path("battle/final_reinforcement_target.png"))


if __name__ == "__main__":
    unittest.main()
