from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario7_clear_probe_rom as probe_builder
from tools.scenario_data import FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario7RuntimeClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            runtime_clear=True,
        )
        return data

    def test_preserves_every_scenario_deployment_and_fixed_record(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        fixed_start = layout.records_offset
        fixed_end = fixed_start + layout.record_count * FIXED_RECORD_SIZE
        self.assertEqual(data[fixed_start:fixed_end], self.source[fixed_start:fixed_end])

        deployment_end = (
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
            + len(probe_builder.SOURCE_PLAYER_DEPLOYMENTS)
        )
        self.assertEqual(
            data[probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end],
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS,
        )

    def test_wrapper_marks_only_runtime_ginam_defeated(self):
        code = probe_builder.runtime_clear_wrapper_code()
        target = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.GINAM_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("00 39 00 80")
            + (target + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 00")
            + (target + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 FF")
            + (target + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertTrue(code.endswith(bytes.fromhex("4E F9 00 02 2C 1E")))

    def test_changes_only_wrapper_operand_and_checksum(self):
        data = self.patched()
        wrapper = probe_builder.runtime_clear_wrapper_code()
        allowed = {0x18E, 0x18F}
        allowed.update(
            range(
                probe_builder.START_MENU_ENTRY_OPERAND,
                probe_builder.START_MENU_ENTRY_OPERAND + 4,
            )
        )
        allowed.update(
            range(
                probe_builder.RUNTIME_WRAPPER,
                probe_builder.RUNTIME_WRAPPER + len(wrapper),
            )
        )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)

    def test_rejects_conflicting_mode(self):
        with self.assertRaisesRegex(ValueError, "modes conflict"):
            probe_builder.patch_probe(
                bytearray(self.built),
                self.source,
                runtime_clear=True,
                protagonist_death=True,
            )


if __name__ == "__main__":
    unittest.main()
