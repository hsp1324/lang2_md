from pathlib import Path
import tempfile
import unittest

from tools import run_scenario01_09_result_surface as runner


class Scenario01To09ResultSurfaceRunnerTests(unittest.TestCase):
    def test_every_scenario_has_a_completion_definition(self) -> None:
        self.assertEqual(tuple(runner.SCENARIOS), tuple(range(1, 10)))
        self.assertEqual(
            runner.SCENARIOS[4]["clear_groups"],
            (runner.scenario4.MORGAN_RUNTIME_GROUP,),
        )
        self.assertEqual(
            runner.SCENARIOS[8]["clear_groups"],
            (runner.scenario8.BOSS_RUNTIME_GROUP,),
        )
        self.assertTrue(
            all(
                definition["completion"] in ("runtime_end_turn", "move_up")
                for definition in runner.SCENARIOS.values()
            )
        )

    def test_runtime_group_reads_big_endian_work_ram_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state.gst"
            payload = bytearray(runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES)
            group = 10
            record = (
                runner.GST_WORK_RAM_OFFSET
                + (runner.scenario4.RUNTIME_GROUP_BASE & 0xFFFF)
                + group * runner.scenario4.RUNTIME_GROUP_SIZE
            )
            payload[record : record + 8] = bytes.fromhex(
                "0F 24 80 00 00 00 FF 15"
            )
            state.write_bytes(payload)
            self.assertEqual(
                runner.runtime_group(state, runner.scenario4, group),
                {
                    "group": group,
                    "class_id": 0x0F,
                    "name_id": 0x24,
                    "defeated_flag": 0x80,
                    "hp": 0,
                    "x": 0xFF,
                    "y": 0x15,
                },
            )


if __name__ == "__main__":
    unittest.main()
