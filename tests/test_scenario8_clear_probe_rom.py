from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario8_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario8ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def protagonist_death_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            protagonist_death=True,
        )
        return data

    def boss_survival_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            boss_survival=True,
        )
        return data

    def runtime_clear_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source, runtime_clear=True)
        return data

    def timeout_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            timeout=True,
        )
        return data

    def turn_event_patched(self, turn: int) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            turn_event=turn,
        )
        return data

    def turn_event_sequence_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            turn_event_sequence=True,
        )
        return data

    def turn_23_no_scott_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            turn_23_no_scott=True,
        )
        return data

    def test_probe_only_changes_kramer_combat_fields_coordinates_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.KRAMER_RECORD_OFFSET
        expected_changes = {
            0x18E,
            0x18F,
            base + FIELD_OFFSETS["at"],
            base + FIELD_OFFSETS["df"],
            base + FIELD_OFFSETS["x"],
            base + FIELD_OFFSETS["y"],
            *(base + FIELD_OFFSETS["mercenaries"] + slot for slot in range(6)),
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_every_other_fixed_record(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            if index == probe_builder.KRAMER_RECORD_INDEX:
                continue
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_weakens_and_moves_kramer_only(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.KRAMER_RECORD_OFFSET
        self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["x"]], 2)
        self.assertEqual(data[base + FIELD_OFFSETS["y"]], 6)
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)

    def test_boss_survival_probe_changes_only_isolated_kramer_fields(self):
        data = self.boss_survival_patched()
        base = probe_builder.KRAMER_RECORD_OFFSET
        self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
        self.assertEqual(
            data[base + FIELD_OFFSETS["df"]],
            probe_builder.PROBE_KRAMER_SURVIVAL_DF,
        )
        self.assertEqual(data[base + FIELD_OFFSETS["x"]], 2)
        self.assertEqual(data[base + FIELD_OFFSETS["y"]], 6)
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(
            data[mercenary_offset : mercenary_offset + 6],
            b"\xFF" * 6,
        )
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            if index == probe_builder.KRAMER_RECORD_INDEX:
                continue
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_rejects_changed_kramer_record(self):
        data = bytearray(self.built)
        data[probe_builder.KRAMER_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Kramer record differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(checksum, 0x72F7)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_protagonist_death_changes_only_start_wrapper_and_checksum(self):
        data = self.protagonist_death_patched()
        wrapper = probe_builder.protagonist_death_wrapper_code()
        expected_changes = {
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
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_protagonist_death_preserves_all_scenario_fixed_records(self):
        data = self.protagonist_death_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])

    def test_protagonist_death_wrapper_marks_only_player_group_zero(self):
        code = probe_builder.protagonist_death_wrapper_code()
        protagonist = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.PROTAGONIST_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("00 39 00 80")
            + (
                protagonist + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 00")
            + (protagonist + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 FF")
            + (protagonist + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_protagonist_death_rejects_changed_fixed_record(self):
        data = bytearray(self.built)
        data[probe_builder.KRAMER_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Kramer record differs"):
            probe_builder.patch_probe(
                data,
                self.source,
                protagonist_death=True,
            )

    def test_protagonist_death_checksum_is_valid(self):
        data = self.protagonist_death_patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)
        self.assertEqual(expected, 0x1653)

    def test_runtime_clear_targets_only_kramer_and_preserves_fixed_records(self):
        data = self.runtime_clear_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])
        code = probe_builder.runtime_defeat_group_wrapper_code(
            probe_builder.BOSS_RUNTIME_GROUP
        )
        target = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.BOSS_RUNTIME_GROUP * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            (target + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        protagonist = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.PROTAGONIST_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertNotIn(
            (protagonist + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )

    def test_timeout_changes_only_start_wrapper_and_checksum(self):
        data = self.timeout_patched()
        wrapper = probe_builder.timeout_wrapper_code()
        expected_changes = {
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
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_timeout_preserves_all_scenario_fixed_records(self):
        data = self.timeout_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])

    def test_timeout_wrapper_sets_verified_turn_counter_and_tails_to_stock(self):
        code = probe_builder.timeout_wrapper_code()
        self.assertIn(
            bytes.fromhex("13 FC")
            + probe_builder.TIMEOUT_LAST_ALLOWED_TURN.to_bytes(2, "big")
            + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
            code,
        )
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_diagnostic_modes_conflict(self):
        data = bytearray(self.built)
        with self.assertRaisesRegex(ValueError, "modes conflict"):
            probe_builder.patch_probe(
                data,
                self.source,
                protagonist_death=True,
                timeout=True,
            )

    def test_source_scheduled_turn_table_and_handlers_are_locked(self):
        table_end = (
            probe_builder.TURN_EVENT_TABLE
            + len(probe_builder.TURN_EVENT_TABLE_BYTES)
        )
        self.assertEqual(
            self.source[probe_builder.TURN_EVENT_TABLE:table_end],
            probe_builder.TURN_EVENT_TABLE_BYTES,
        )
        for handler, offset in probe_builder.TURN_EVENT_HANDLERS.items():
            expected = probe_builder.TURN_EVENT_HANDLER_BYTES[handler]
            with self.subTest(handler=handler):
                self.assertEqual(
                    self.source[offset : offset + len(expected)],
                    expected,
                )

    def test_turn_event_changes_only_start_wrapper_and_checksum(self):
        for turn in probe_builder.TURN_EVENT_COUNTER_VALUES:
            with self.subTest(turn=turn):
                data = self.turn_event_patched(turn)
                wrapper = probe_builder.turn_event_wrapper_code(turn)
                expected_changes = {
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
                    index
                    for index, (before, after) in enumerate(zip(self.built, data))
                    if before != after
                }
                self.assertLessEqual(changed, expected_changes)

    def test_turn_event_preserves_deployments_fixed_records_and_event_data(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        deployment_end = (
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
            + len(probe_builder.SOURCE_PLAYER_DEPLOYMENTS)
        )
        table_end = (
            probe_builder.TURN_EVENT_TABLE
            + len(probe_builder.TURN_EVENT_TABLE_BYTES)
        )
        for turn in probe_builder.TURN_EVENT_COUNTER_VALUES:
            with self.subTest(turn=turn):
                data = self.turn_event_patched(turn)
                self.assertEqual(
                    data[
                        probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET:
                        deployment_end
                    ],
                    probe_builder.SOURCE_PLAYER_DEPLOYMENTS,
                )
                for index in range(layout.record_count):
                    start = layout.records_offset + index * FIXED_RECORD_SIZE
                    end = start + FIXED_RECORD_SIZE
                    self.assertEqual(data[start:end], self.source[start:end])
                self.assertEqual(
                    data[probe_builder.TURN_EVENT_TABLE:table_end],
                    probe_builder.TURN_EVENT_TABLE_BYTES,
                )
                for handler, offset in probe_builder.TURN_EVENT_HANDLERS.items():
                    expected = probe_builder.TURN_EVENT_HANDLER_BYTES[handler]
                    self.assertEqual(data[offset : offset + len(expected)], expected)

    def test_turn_event_wrapper_protects_only_player_groups_and_sets_counter(self):
        for turn, counter in probe_builder.TURN_EVENT_COUNTER_VALUES.items():
            with self.subTest(turn=turn):
                code = probe_builder.turn_event_wrapper_code(turn)
                for runtime_group in probe_builder.TURN_EVENT_PROTECTED_RUNTIME_GROUPS:
                    record = (
                        probe_builder.RUNTIME_GROUP_BASE
                        + runtime_group * probe_builder.RUNTIME_GROUP_SIZE
                    )
                    self.assertIn(
                        bytes.fromhex("13 FC")
                        + probe_builder.TURN_EVENT_PROTECTED_DF.to_bytes(2, "big")
                        + (record + probe_builder.RUNTIME_DF_OFFSET).to_bytes(
                            4, "big"
                        ),
                        code,
                    )
                first_fixed = (
                    probe_builder.RUNTIME_GROUP_BASE
                    + probe_builder.FIRST_FIXED_RUNTIME_GROUP
                    * probe_builder.RUNTIME_GROUP_SIZE
                )
                self.assertNotIn(
                    bytes.fromhex("13 FC")
                    + probe_builder.TURN_EVENT_PROTECTED_DF.to_bytes(2, "big")
                    + (first_fixed + probe_builder.RUNTIME_DF_OFFSET).to_bytes(
                        4, "big"
                    ),
                    code,
                )
                self.assertIn(
                    bytes.fromhex("13 FC")
                    + counter.to_bytes(2, "big")
                    + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
                    code,
                )
                self.assertEqual(
                    code[-6:],
                    bytes.fromhex("4E F9")
                    + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
                )

    def test_turn_event_rejects_unknown_target(self):
        data = bytearray(self.built)
        with self.assertRaisesRegex(ValueError, "target must be one of"):
            probe_builder.patch_probe(data, self.source, turn_event=11)

    def test_turn_23_no_scott_changes_only_start_wrapper_and_checksum(self):
        data = self.turn_23_no_scott_patched()
        wrapper = probe_builder.turn_event_wrapper_code(
            23,
            unavailable_runtime_group=probe_builder.SCOTT_RUNTIME_GROUP,
        )
        expected_changes = {
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
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_turn_23_no_scott_preserves_source_scenario_data(self):
        data = self.turn_23_no_scott_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        deployment_end = (
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
            + len(probe_builder.SOURCE_PLAYER_DEPLOYMENTS)
        )
        self.assertEqual(
            data[
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end
            ],
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS,
        )
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])
        table_end = (
            probe_builder.TURN_EVENT_TABLE
            + len(probe_builder.TURN_EVENT_TABLE_BYTES)
        )
        self.assertEqual(
            data[probe_builder.TURN_EVENT_TABLE:table_end],
            probe_builder.TURN_EVENT_TABLE_BYTES,
        )
        for handler, offset in probe_builder.TURN_EVENT_HANDLERS.items():
            expected = probe_builder.TURN_EVENT_HANDLER_BYTES[handler]
            self.assertEqual(data[offset : offset + len(expected)], expected)

    def test_turn_23_no_scott_wrapper_uses_stock_absence_condition(self):
        self.assertEqual(
            probe_builder.SOURCE_PLAYER_NAME_IDS,
            (0x01, 0x05, 0x06, 0x02, 0x04, 0x08, 0x07),
        )
        self.assertEqual(probe_builder.SCOTT_RUNTIME_GROUP, 2)
        code = probe_builder.turn_event_wrapper_code(
            23,
            unavailable_runtime_group=probe_builder.SCOTT_RUNTIME_GROUP,
        )
        scott = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.SCOTT_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("00 39 00 80")
            + (
                scott + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 00")
            + (scott + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 FF")
            + (scott + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 16")
            + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
            code,
        )
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_turn_event_alternate_rejects_other_turns_and_groups(self):
        with self.assertRaisesRegex(ValueError, "only turn 23 without Scott"):
            probe_builder.turn_event_wrapper_code(
                21,
                unavailable_runtime_group=probe_builder.SCOTT_RUNTIME_GROUP,
            )
        with self.assertRaisesRegex(ValueError, "only turn 23 without Scott"):
            probe_builder.turn_event_wrapper_code(
                23,
                unavailable_runtime_group=5,
            )

    def test_turn_event_conflicts_with_other_diagnostic_modes(self):
        data = bytearray(self.built)
        with self.assertRaisesRegex(ValueError, "diagnostic modes conflict"):
            probe_builder.patch_probe(
                data,
                self.source,
                protagonist_death=True,
                turn_event=12,
            )

    def test_turn_event_sequence_changes_only_start_wrapper_and_checksum(self):
        data = self.turn_event_sequence_patched()
        wrapper = probe_builder.turn_event_sequence_wrapper_code()
        expected_changes = {
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
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_turn_event_sequence_preserves_source_scenario_data(self):
        data = self.turn_event_sequence_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        deployment_end = (
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
            + len(probe_builder.SOURCE_PLAYER_DEPLOYMENTS)
        )
        self.assertEqual(
            data[
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end
            ],
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS,
        )
        for index in range(layout.record_count):
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])
        table_end = (
            probe_builder.TURN_EVENT_TABLE
            + len(probe_builder.TURN_EVENT_TABLE_BYTES)
        )
        self.assertEqual(
            data[probe_builder.TURN_EVENT_TABLE:table_end],
            probe_builder.TURN_EVENT_TABLE_BYTES,
        )

    def test_turn_event_sequence_wrapper_has_ordered_guarded_thresholds(self):
        code = probe_builder.turn_event_sequence_wrapper_code()
        previous = -1
        for counter in probe_builder.TURN_EVENT_SEQUENCE_COUNTER_VALUES:
            compare = (
                bytes.fromhex("0C 39")
                + counter.to_bytes(2, "big")
                + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big")
            )
            store = (
                bytes.fromhex("13 FC")
                + counter.to_bytes(2, "big")
                + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big")
            )
            compare_offset = code.index(compare)
            store_offset = code.index(store, compare_offset)
            self.assertGreater(compare_offset, previous)
            self.assertGreater(store_offset, compare_offset)
            self.assertEqual(code[compare_offset + len(compare)], 0x64)
            self.assertEqual(code[store_offset + len(store)], 0x60)
            previous = store_offset
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_turn_event_sequence_conflicts_with_single_target(self):
        data = bytearray(self.built)
        with self.assertRaisesRegex(ValueError, "diagnostic modes conflict"):
            probe_builder.patch_probe(
                data,
                self.source,
                turn_event=12,
                turn_event_sequence=True,
            )

    def test_timeout_checksum_is_valid(self):
        data = self.timeout_patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)
        self.assertEqual(expected, 0x85E2)

    def test_turn_event_checksums_are_valid(self):
        for turn in probe_builder.TURN_EVENT_COUNTER_VALUES:
            with self.subTest(turn=turn):
                data = self.turn_event_patched(turn)
                expected = sum(
                    int.from_bytes(data[offset : offset + 2], "big")
                    for offset in range(0x200, len(data), 2)
                ) & 0xFFFF
                self.assertEqual(
                    int.from_bytes(data[0x18E:0x190], "big"),
                    expected,
                )

    def test_turn_event_sequence_checksum_is_valid(self):
        data = self.turn_event_sequence_patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(
            int.from_bytes(data[0x18E:0x190], "big"),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
