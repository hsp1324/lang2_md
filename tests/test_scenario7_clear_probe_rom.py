from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario7_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario7ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def civilian_loss_patched(
        self,
        records: tuple[int, ...] = probe_builder.DEFAULT_LOST_CIVILIAN_RECORDS,
    ) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            civilian_loss=True,
            lost_civilian_records=records,
        )
        return data

    def protagonist_death_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            protagonist_death=True,
        )
        return data

    def turn_event_patched(
        self,
        turn: int,
        branch: str = "stock",
    ) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            turn_event=turn,
            turn_event_branch=branch,
        )
        return data

    def test_probe_only_changes_ginam_combat_fields_coordinates_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.GINAM_RECORD_OFFSET
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
            if index == probe_builder.GINAM_RECORD_INDEX:
                continue
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_locks_player_group_and_resident_event_mapping(self):
        self.assertEqual(probe_builder.PLAYER_DEPLOYMENT_COUNT, 6)
        deployment_end = (
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
            + len(probe_builder.SOURCE_PLAYER_DEPLOYMENTS)
        )
        self.assertEqual(
            self.source[
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end
            ],
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS,
        )
        event_end = (
            probe_builder.RESIDENT_DEATH_EVENT_TABLE
            + len(probe_builder.SOURCE_RESIDENT_DEATH_EVENTS)
        )
        self.assertEqual(
            self.source[probe_builder.RESIDENT_DEATH_EVENT_TABLE:event_end],
            probe_builder.SOURCE_RESIDENT_DEATH_EVENTS,
        )
        self.assertEqual(probe_builder.FIRST_FIXED_RUNTIME_GROUP, 6)
        self.assertEqual(probe_builder.GINAM_RUNTIME_GROUP, 10)

    def test_source_scheduled_turn_table_and_handlers_are_locked(self):
        table_end = (
            probe_builder.TURN_EVENT_TABLE
            + len(probe_builder.TURN_EVENT_TABLE_BYTES)
        )
        self.assertEqual(
            self.source[probe_builder.TURN_EVENT_TABLE:table_end],
            probe_builder.TURN_EVENT_TABLE_BYTES,
        )
        self.assertEqual(
            self.built[probe_builder.TURN_EVENT_TABLE:table_end],
            probe_builder.TURN_EVENT_TABLE_BYTES,
        )
        for handler, offset in probe_builder.TURN_EVENT_HANDLERS.items():
            expected = probe_builder.TURN_EVENT_HANDLER_BYTES[handler]
            self.assertEqual(self.source[offset : offset + len(expected)], expected)
            self.assertEqual(self.built[offset : offset + len(expected)], expected)

    def test_turn6_internal_dialogue_branch_prefix_is_locked(self):
        for branch, expected in (
            probe_builder.TURN6_END_BRANCH_PREFIX_BYTES.items()
        ):
            offset = probe_builder.TURN6_END_BRANCH_HANDLERS[branch]
            self.assertEqual(self.source[offset : offset + len(expected)], expected)
            self.assertEqual(self.built[offset : offset + len(expected)], expected)

    def test_scheduled_turn_dialogue_pages_are_reviewed(self):
        expected_texts = {
            3: (
                0x1904AA,
                0x1904F4,
            ),
            6: (
                0x18FB84,
                0x18FB9C,
                0x18FBC0,
                0x18FBCA,
                0x18FBDA,
                0x18FC2A,
                0x18FC60,
            ),
        }
        self.assertEqual(probe_builder.TURN_EVENT_TEXTS, expected_texts)

    def test_probe_weakens_and_moves_ginam_only(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.GINAM_RECORD_OFFSET
        self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["x"]], 7)
        self.assertEqual(data[base + FIELD_OFFSETS["y"]], 19)
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)

    def test_probe_rejects_changed_ginam_record(self):
        data = bytearray(self.built)
        data[probe_builder.GINAM_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 4 differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_civilian_loss_changes_only_declared_diagnostic_fields(self):
        data = self.civilian_loss_patched()
        base = probe_builder.GINAM_RECORD_OFFSET
        allowed = {
            0x18E,
            0x18F,
            base + FIELD_OFFSETS["at"],
            base + FIELD_OFFSETS["df"],
            base + FIELD_OFFSETS["x"],
            base + FIELD_OFFSETS["y"],
            *(
                base + FIELD_OFFSETS["mercenaries"] + slot
                for slot in range(6)
            ),
        }
        wrapper = probe_builder.civilian_loss_wrapper_code()
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

    def test_civilian_loss_preserves_resident_keith_and_other_enemy_records(self):
        data = self.civilian_loss_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            if index == probe_builder.GINAM_RECORD_INDEX:
                continue
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])

    def test_civilian_loss_preserves_ginam_identity(self):
        data = self.civilian_loss_patched()
        base = probe_builder.GINAM_RECORD_OFFSET
        for field in ("name_id", "class_id", "level"):
            offset = FIELD_OFFSETS[field]
            self.assertEqual(data[base + offset], self.source[base + offset])
        self.assertEqual(
            (
                data[base + FIELD_OFFSETS["x"]],
                data[base + FIELD_OFFSETS["y"]],
            ),
            (probe_builder.PROBE_GINAM_X, probe_builder.PROBE_GINAM_Y),
        )

    def test_civilian_loss_wrapper_marks_resident_and_isolates_ginam(self):
        code = probe_builder.civilian_loss_wrapper_code()
        fixed_record = probe_builder.DEFAULT_LOST_CIVILIAN_RECORDS[0]
        runtime_group = probe_builder.FIRST_FIXED_RUNTIME_GROUP + fixed_record
        civilian = (
            probe_builder.RUNTIME_GROUP_BASE
            + runtime_group * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("00 39 00 80")
            + (
                civilian + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 00")
            + (civilian + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 FF")
            + (civilian + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
            code,
        )
        target = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.GINAM_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 01")
            + (target + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        for group in probe_builder.HIDDEN_ENEMY_RUNTIME_GROUPS:
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertIn(
                bytes.fromhex("13 FC 00 FF")
                + (record + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
                code,
            )
        self.assertTrue(code.endswith(bytes.fromhex("4E F9 00 02 2C 1E")))

    def test_civilian_loss_wrapper_supports_every_nonempty_subset(self):
        subsets = (
            (0,),
            (1,),
            (2,),
            (0, 1),
            (0, 2),
            (1, 2),
            (0, 1, 2),
        )
        for lost_records in subsets:
            code = probe_builder.civilian_loss_wrapper_code(lost_records)
            for fixed_record in lost_records:
                runtime_group = (
                    probe_builder.FIRST_FIXED_RUNTIME_GROUP + fixed_record
                )
                civilian = (
                    probe_builder.RUNTIME_GROUP_BASE
                    + runtime_group * probe_builder.RUNTIME_GROUP_SIZE
                )
                self.assertIn(
                    bytes.fromhex("00 39 00 80")
                    + (
                        civilian + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
                    ).to_bytes(4, "big"),
                    code,
                )
        for invalid in ((), (0, 0), (3,)):
            with self.assertRaises(ValueError):
                probe_builder.civilian_loss_wrapper_code(invalid)

    def test_civilian_loss_checksum_is_valid(self):
        data = self.civilian_loss_patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_protagonist_death_changes_only_start_wrapper_and_checksum(self):
        data = self.protagonist_death_patched()
        wrapper = probe_builder.protagonist_death_wrapper_code()
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

    def test_protagonist_death_preserves_all_scenario_fixed_records(self):
        data = self.protagonist_death_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        start = layout.records_offset
        end = start + layout.record_count * FIXED_RECORD_SIZE
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
            + (
                protagonist + probe_builder.RUNTIME_HP_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 FF")
            + (
                protagonist + probe_builder.RUNTIME_X_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertTrue(code.endswith(bytes.fromhex("4E F9 00 02 2C 1E")))

    def test_probe_rejects_conflicting_runtime_modes(self):
        with self.assertRaisesRegex(ValueError, "modes conflict"):
            probe_builder.patch_probe(
                bytearray(self.built),
                self.source,
                civilian_loss=True,
                protagonist_death=True,
            )
        with self.assertRaisesRegex(ValueError, "modes conflict"):
            probe_builder.patch_probe(
                bytearray(self.built),
                self.source,
                protagonist_death=True,
                turn_event=3,
            )

    def test_protagonist_death_checksum_is_valid(self):
        data = self.protagonist_death_patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_turn_event_modes_change_only_wrapper_operand_and_checksum(self):
        for turn in probe_builder.TURN_EVENT_COUNTER_VALUES:
            data = self.turn_event_patched(turn)
            wrapper = probe_builder.turn_event_wrapper_code(turn)
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

    def test_turn_event_modes_preserve_all_deployments_and_fixed_records(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        fixed_start = layout.records_offset
        fixed_end = fixed_start + layout.record_count * FIXED_RECORD_SIZE
        deployment_end = (
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
            + len(probe_builder.SOURCE_PLAYER_DEPLOYMENTS)
        )
        for turn in probe_builder.TURN_EVENT_COUNTER_VALUES:
            data = self.turn_event_patched(turn)
            self.assertEqual(
                data[
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET:deployment_end
                ],
                probe_builder.SOURCE_PLAYER_DEPLOYMENTS,
            )
            self.assertEqual(
                data[fixed_start:fixed_end],
                self.source[fixed_start:fixed_end],
            )

    def test_turn_event_wrappers_use_required_stock_counter_state(self):
        self.assertEqual(
            probe_builder.TURN_EVENT_COUNTER_VALUES,
            {3: 3, 6: 5},
        )
        self.assertEqual(
            probe_builder.TURN_EVENT_PROTECTED_RUNTIME_GROUPS,
            tuple(range(10)),
        )
        for turn, counter_value in probe_builder.TURN_EVENT_COUNTER_VALUES.items():
            code = probe_builder.turn_event_wrapper_code(turn)
            for runtime_group in probe_builder.TURN_EVENT_PROTECTED_RUNTIME_GROUPS:
                record = (
                    probe_builder.RUNTIME_GROUP_BASE
                    + runtime_group * probe_builder.RUNTIME_GROUP_SIZE
                )
                self.assertIn(
                    bytes.fromhex("13 FC")
                    + probe_builder.TURN_EVENT_PROTECTED_DF.to_bytes(2, "big")
                    + (record + probe_builder.RUNTIME_DF_OFFSET).to_bytes(4, "big"),
                    code,
                )
            self.assertIn(
                bytes.fromhex("0C 39")
                + counter_value.to_bytes(2, "big")
                + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
                code,
            )
            self.assertIn(
                bytes.fromhex("13 FC")
                + counter_value.to_bytes(2, "big")
                + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
                code,
            )
            self.assertTrue(code.endswith(bytes.fromhex("4E F9 00 02 2C 1E")))

    def test_turn_event_wrapper_rejects_unknown_turn(self):
        with self.assertRaisesRegex(ValueError, "must be one of 3, 6"):
            probe_builder.turn_event_wrapper_code(5)
        with self.assertRaisesRegex(ValueError, "must be one of 3, 6"):
            probe_builder.patch_probe(
                bytearray(self.built),
                self.source,
                turn_event=5,
            )

    def test_turn6_branch_only_redirects_source_table_target(self):
        data = self.turn_event_patched(6, "dialogue")
        wrapper = probe_builder.turn_event_wrapper_code(6)
        self.assertEqual(
            int.from_bytes(
                self.source[
                    probe_builder.TURN6_DIALOGUE_BRIDGE_TABLE_TARGET :
                    probe_builder.TURN6_DIALOGUE_BRIDGE_TABLE_TARGET + 4
                ],
                "big",
            ),
            probe_builder.TURN_EVENT_HANDLERS["turn-6-entry"],
        )
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
        allowed.update(
            range(
                probe_builder.TURN6_DIALOGUE_BRIDGE_TABLE_TARGET,
                probe_builder.TURN6_DIALOGUE_BRIDGE_TABLE_TARGET + 4,
            )
        )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)
        self.assertEqual(
            int.from_bytes(
                data[
                    probe_builder.TURN6_DIALOGUE_BRIDGE_TABLE_TARGET :
                    probe_builder.TURN6_DIALOGUE_BRIDGE_TABLE_TARGET + 4
                ],
                "big",
            ),
            probe_builder.TURN6_END_BRANCH_HANDLERS["dialogue"],
        )

    def test_turn6_branch_rejects_other_turns_and_unknown_names(self):
        with self.assertRaisesRegex(ValueError, "require --turn-event 6"):
            probe_builder.patch_probe(
                bytearray(self.built),
                self.source,
                turn_event=3,
                turn_event_branch="dialogue",
            )
        with self.assertRaisesRegex(ValueError, "must be one of"):
            probe_builder.patch_probe(
                bytearray(self.built),
                self.source,
                turn_event=6,
                turn_event_branch="unknown",
            )


if __name__ == "__main__":
    unittest.main()
