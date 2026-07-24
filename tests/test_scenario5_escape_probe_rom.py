from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario5_escape_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario5EscapeProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def annihilation_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            enemy_annihilation=True,
        )
        return data

    def annihilation_allowed_offsets(self) -> set[int]:
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {0x18E, 0x18F}
        allowed.update(
            range(
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET,
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
                + len(
                    probe_builder.deployment_bytes(
                        probe_builder.SOURCE_PLAYER_DEPLOYMENTS
                    )
                ),
            )
        )
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            allowed.update(
                {
                    base + FIELD_OFFSETS["at"],
                    base + FIELD_OFFSETS["df"],
                    *(
                        base + FIELD_OFFSETS["mercenaries"] + slot
                        for slot in range(6)
                    ),
                }
            )
        wrapper = probe_builder.annihilation_wrapper_code()
        allowed.update(
            range(
                probe_builder.START_MENU_ENTRY_OPERAND,
                probe_builder.START_MENU_ENTRY_OPERAND + 4,
            )
        )
        allowed.update(
            range(
                probe_builder.ANNIHILATION_WRAPPER,
                probe_builder.ANNIHILATION_WRAPPER + len(wrapper),
            )
        )
        return allowed

    def test_probe_only_changes_first_deployment_y_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        expected_changes = {
            0x18E,
            0x18F,
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 2,
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 3,
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_scenario_layout_and_all_fixed_records(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        source_layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        probe_layout = scenario_layout(data, probe_builder.SCENARIO_NUMBER)
        self.assertEqual(probe_layout, source_layout)
        start = source_layout.records_offset
        end = start + source_layout.record_count * FIXED_RECORD_SIZE
        self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_moves_only_elwin_to_north_threshold(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(
            data[start : start + 4],
            bytes.fromhex(
                f"{probe_builder.SOURCE_FIRST_PLAYER_X:04X} "
                f"{probe_builder.PROBE_FIRST_PLAYER_Y:04X}"
            ),
        )

    def test_annihilation_changes_only_declared_diagnostic_fields(self):
        data = self.annihilation_patched()
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, self.annihilation_allowed_offsets())

    def test_annihilation_preserves_fixed_identity_and_coordinates(self):
        data = self.annihilation_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base] & 0x80, self.source[base] & 0x80)
            self.assertEqual(data[base + 0x08], self.source[base + 0x08])
            for field in (
                "level",
                "name_id",
                "class_id",
                "x",
                "y",
            ):
                offset = FIELD_OFFSETS[field]
                self.assertEqual(data[base + offset], self.source[base + offset])
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)

    def test_annihilation_moves_only_first_player_below_source_target(self):
        data = self.annihilation_patched()
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        expected = probe_builder.deployment_bytes(
            probe_builder.ANNIHILATION_PLAYER_DEPLOYMENTS
        )
        self.assertEqual(data[start : start + len(expected)], expected)
        self.assertEqual(
            probe_builder.ANNIHILATION_PLAYER_DEPLOYMENTS[1:],
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS[1:],
        )

    def test_annihilation_wrapper_isolates_one_living_enemy(self):
        code = probe_builder.annihilation_wrapper_code()
        target = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.ANNIHILATION_TARGET_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 01")
            + (target + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        for group in probe_builder.ANNIHILATION_HIDDEN_RUNTIME_GROUPS:
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
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
        self.assertTrue(code.endswith(bytes.fromhex("4E F9 00 02 2C 1E")))

    def test_probe_rejects_changed_deployment_or_fixed_record(self):
        changed_deployment = bytearray(self.built)
        changed_deployment[probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "player deployments differ"):
            probe_builder.patch_probe(changed_deployment, self.source)

        changed_record = bytearray(self.built)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        changed_record[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed records differ"):
            probe_builder.patch_probe(changed_record, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_annihilation_checksum_is_valid(self):
        data = self.annihilation_patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)


if __name__ == "__main__":
    unittest.main()
