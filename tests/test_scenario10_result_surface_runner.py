from pathlib import Path
import tempfile
import unittest

from tools import build_scenario10_result_surface_probe_rom as probe_builder
from tools import run_scenario10_result_surface as runner


class Scenario10ResultSurfaceRunnerTests(unittest.TestCase):
    def test_runtime_clear_state_requires_every_monster_group(self):
        size = runner.GST_WORK_RAM_OFFSET + runner.WORK_RAM_BYTES
        payload = bytearray(size)
        ram = runner.GST_WORK_RAM_OFFSET
        base = probe_builder.RUNTIME_GROUP_BASE & 0xFFFF
        for group in range(
            probe_builder.FIRST_MONSTER_RUNTIME_GROUP,
            probe_builder.LAST_MONSTER_RUNTIME_GROUP + 1,
        ):
            record = ram + base + group * probe_builder.RUNTIME_GROUP_SIZE
            payload[record + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET] = 0x80
            payload[record + probe_builder.RUNTIME_HP_OFFSET] = 0
            payload[record + probe_builder.RUNTIME_X_OFFSET] = 0xFF

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "clear.gst"
            state.write_bytes(payload)
            report = runner.runtime_clear_state(state)
            self.assertTrue(report["all_monsters_defeated"])

            first = (
                ram
                + base
                + probe_builder.FIRST_MONSTER_RUNTIME_GROUP
                * probe_builder.RUNTIME_GROUP_SIZE
            )
            payload[first + probe_builder.RUNTIME_HP_OFFSET] = 1
            state.write_bytes(payload)
            report = runner.runtime_clear_state(state)
            self.assertFalse(report["all_monsters_defeated"])


if __name__ == "__main__":
    unittest.main()
