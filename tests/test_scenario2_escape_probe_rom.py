from pathlib import Path
import unittest

from tools import build_scenario2_escape_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class Scenario2EscapeProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = JP_ROM.read_bytes()
        cls.production = KO_ROM.read_bytes()

    def patched(
        self,
        *,
        enemy_annihilation: bool = False,
        liana_death: bool = False,
        protagonist_death: bool = False,
    ) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            enemy_annihilation=enemy_annihilation,
            liana_death=liana_death,
            protagonist_death=protagonist_death,
        )
        return data

    def test_probe_changes_only_liana_y_and_checksum(self):
        data = self.patched()
        y_offset = probe_builder.LIANA_RECORD_OFFSET + FIELD_OFFSETS["y"]
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertEqual(data[y_offset], probe_builder.PROBE_LIANA_Y)
        self.assertEqual(
            probe_builder.builder.update_md_checksum(bytearray(data)),
            int.from_bytes(data[0x18E:0x190], "big"),
        )
        self.assertLessEqual(changed, {y_offset, 0x18E, 0x18F})

    def test_source_and_input_record_mutations_are_rejected(self):
        source = bytearray(self.source)
        source[probe_builder.SCENARIO_HEADER + 0x08] ^= 1
        with self.assertRaisesRegex(ValueError, "deployment table"):
            probe_builder.patch_probe(bytearray(self.production), bytes(source))

        data = bytearray(self.production)
        data[probe_builder.LIANA_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Liana record"):
            probe_builder.patch_probe(data, self.source)

    def test_source_owned_result_events_are_locked(self):
        for data in (self.source, self.production):
            for offset, expected in (
                (
                    probe_builder.PROTAGONIST_DEATH_TRIGGER,
                    probe_builder.PROTAGONIST_DEATH_TRIGGER_BYTES,
                ),
                (
                    probe_builder.PROTAGONIST_DEATH_HANDLER,
                    probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES,
                ),
                (
                    probe_builder.LIANA_DEATH_TRIGGER,
                    probe_builder.LIANA_DEATH_TRIGGER_BYTES,
                ),
                (
                    probe_builder.LIANA_DEATH_HANDLER,
                    probe_builder.LIANA_DEATH_HANDLER_BYTES,
                ),
                (
                    probe_builder.ENEMY_ANNIHILATION_TRIGGER,
                    probe_builder.ENEMY_ANNIHILATION_TRIGGER_BYTES,
                ),
                (
                    probe_builder.ENEMY_ANNIHILATION_HANDLER,
                    probe_builder.ENEMY_ANNIHILATION_HANDLER_BYTES,
                ),
            ):
                self.assertEqual(data[offset : offset + len(expected)], expected)

        self.assertEqual(
            int.from_bytes(
                probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES[4:8],
                "big",
            ),
            probe_builder.PROTAGONIST_DEATH_TEXT,
        )
        for text in probe_builder.LIANA_DEATH_TEXTS:
            self.assertIn(
                text.to_bytes(3, "big"),
                probe_builder.LIANA_DEATH_HANDLER_BYTES,
            )
        for text in probe_builder.ENEMY_ANNIHILATION_TEXTS:
            self.assertIn(
                text.to_bytes(3, "big"),
                probe_builder.ENEMY_ANNIHILATION_HANDLER_BYTES,
            )

    def test_diagnostic_modes_preserve_all_scenario_records_and_deployments(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        record_start = layout.records_offset
        record_end = record_start + layout.record_count * FIXED_RECORD_SIZE
        deployment_start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        deployment_end = deployment_start + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4
        for mode in (
            {"enemy_annihilation": True},
            {"protagonist_death": True},
            {"liana_death": True},
        ):
            data = self.patched(**mode)
            self.assertEqual(
                data[record_start:record_end],
                self.source[record_start:record_end],
            )
            self.assertEqual(
                data[deployment_start:deployment_end],
                self.source[deployment_start:deployment_end],
            )

    def test_death_wrappers_target_only_the_declared_runtime_group(self):
        for target_group in (
            probe_builder.PROTAGONIST_RUNTIME_GROUP,
            probe_builder.LIANA_RUNTIME_GROUP,
        ):
            code = probe_builder.runtime_death_wrapper_code(target_group)
            target = (
                probe_builder.RUNTIME_GROUP_BASE
                + target_group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertIn(
                (target + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(
                    4, "big"
                ),
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
            self.assertEqual(
                code[-6:],
                bytes.fromhex("4E F9")
                + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
            )

    def test_death_modes_change_only_wrapper_operand_and_checksum(self):
        for mode, target_group in (
            ({"protagonist_death": True}, probe_builder.PROTAGONIST_RUNTIME_GROUP),
            ({"liana_death": True}, probe_builder.LIANA_RUNTIME_GROUP),
        ):
            data = self.patched(**mode)
            wrapper = probe_builder.runtime_death_wrapper_code(target_group)
            allowed = {
                0x18E,
                0x18F,
                *range(
                    probe_builder.START_MENU_ENTRY_OPERAND,
                    probe_builder.START_MENU_ENTRY_OPERAND + 4,
                ),
                *range(
                    probe_builder.RUNTIME_WRAPPER,
                    probe_builder.RUNTIME_WRAPPER + len(wrapper),
                ),
            }
            changed = {
                offset
                for offset, (before, after) in enumerate(
                    zip(self.production, data)
                )
                if before != after
            }
            self.assertLessEqual(changed, allowed)

    def test_enemy_annihilation_changes_only_declared_probe_fields(self):
        data = self.patched(enemy_annihilation=True)
        wrapper = probe_builder.enemy_annihilation_wrapper_code()
        allowed = {
            0x18E,
            0x18F,
            *range(
                probe_builder.START_MENU_ENTRY_OPERAND,
                probe_builder.START_MENU_ENTRY_OPERAND + 4,
            ),
            *range(
                probe_builder.RUNTIME_WRAPPER,
                probe_builder.RUNTIME_WRAPPER + len(wrapper),
            ),
        }
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)

    def test_enemy_annihilation_preserves_enemy_ownership_and_identity(self):
        data = self.patched(enemy_annihilation=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected_names = (0x2A, 0x2B, 0x13, 0x2C, 0x2D, 0x2E)
        for index, expected_name in zip(
            range(
                probe_builder.FIRST_ENEMY_RECORD_INDEX,
                probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
            ),
            expected_names,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(self.source[base + 0x08], 0x04)
            self.assertEqual(
                data[base + FIELD_OFFSETS["name_id"]],
                expected_name,
            )
            self.assertEqual(
                data[base + FIELD_OFFSETS["class_id"]],
                self.source[base + FIELD_OFFSETS["class_id"]],
            )
            self.assertEqual(
                data[base : base + FIXED_RECORD_SIZE],
                self.source[base : base + FIXED_RECORD_SIZE],
            )

    def test_enemy_annihilation_wrapper_targets_only_enemy_groups(self):
        code = probe_builder.enemy_annihilation_wrapper_code()
        for group in probe_builder.ANNIHILATION_RUNTIME_GROUPS:
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertIn(
                bytes.fromhex("00 39 00 80")
                + (
                    record + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
                ).to_bytes(4, "big"),
                code,
            )
            self.assertIn(
                bytes.fromhex("13 FC 00 FF")
                + (record + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
                code,
            )
            self.assertIn(
                bytes.fromhex("13 FC 00 00")
                + (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
                code,
            )
        for group in range(
            probe_builder.ANNIHILATION_RUNTIME_GROUPS[0]
        ):
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertNotIn(
                (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
                code,
            )

    def test_diagnostic_modes_are_mutually_exclusive(self):
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            probe_builder.patch_probe(
                bytearray(self.production),
                self.source,
                enemy_annihilation=True,
                liana_death=True,
            )


if __name__ == "__main__":
    unittest.main()
