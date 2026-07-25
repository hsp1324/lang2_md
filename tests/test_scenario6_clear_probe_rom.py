import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario6_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario6ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def partial_loss_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            civilian_loss=True,
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

    def turn_event_patched(self, target_turn: int) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            turn_event=target_turn,
        )
        return data

    def test_probe_only_changes_enemy_combat_fields_coordinates_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected_changes = {0x18E, 0x18F}
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            expected_changes.update(
                {
                    base + FIELD_OFFSETS["at"],
                    base + FIELD_OFFSETS["df"],
                    *(
                        base + FIELD_OFFSETS["mercenaries"] + slot
                        for slot in range(6)
                    ),
                }
            )
            if index <= probe_builder.LAST_VISIBLE_ENEMY_RECORD_INDEX:
                expected_changes.update(
                    {base + FIELD_OFFSETS["x"], base + FIELD_OFFSETS["y"]}
                )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_all_allied_and_npc_records(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        start = layout.records_offset
        end = start + probe_builder.FIRST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
        self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_weakens_enemies_and_moves_only_visible_records(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)
            if index <= probe_builder.LAST_VISIBLE_ENEMY_RECORD_INDEX:
                expected_x, expected_y = probe_builder.PROBE_VISIBLE_COORDINATES[
                    index - probe_builder.FIRST_ENEMY_RECORD_INDEX
                ]
                self.assertEqual(data[base + FIELD_OFFSETS["x"]], expected_x)
                self.assertEqual(data[base + FIELD_OFFSETS["y"]], expected_y)
            else:
                self.assertEqual(data[base + FIELD_OFFSETS["x"]], 0xFF)
                self.assertEqual(data[base + FIELD_OFFSETS["y"]], 0xFF)

    def test_probe_rejects_changed_enemy_record(self):
        data = bytearray(self.built)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = layout.records_offset + probe_builder.FIRST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
        data[base] ^= 1
        with self.assertRaisesRegex(ValueError, "enemy record 4 differs"):
            probe_builder.patch_probe(data, self.source)

    def test_source_scheduled_turn_table_and_handlers_are_locked(self):
        table_end = (
            probe_builder.TURN_EVENT_TABLE
            + len(probe_builder.TURN_EVENT_TABLE_BYTES)
        )
        for data in (self.source, self.built):
            self.assertEqual(
                data[probe_builder.TURN_EVENT_TABLE:table_end],
                probe_builder.TURN_EVENT_TABLE_BYTES,
            )
            for turn, offset in probe_builder.TURN_EVENT_HANDLERS.items():
                expected = probe_builder.TURN_EVENT_HANDLER_BYTES[turn]
                self.assertEqual(data[offset : offset + len(expected)], expected)

    def test_scheduled_turn_dialogue_pages_are_reviewed(self):
        translations = json.loads(
            (ROOT / "localization/event_dialogue_ko.json").read_text(
                encoding="utf-8"
            )
        )
        scenario_addresses = {
            int(row["address"], 16)
            for row in translations["scenarios"]["6"]
        }
        expected = {
            address
            for pages in probe_builder.TURN_EVENT_TEXTS.values()
            for address in pages
        }
        self.assertLessEqual(expected, scenario_addresses)

    def test_turn7_internal_branch_prefixes_are_locked(self):
        for branch, expected in probe_builder.TURN7_BRANCH_PREFIX_BYTES.items():
            offset = probe_builder.TURN7_BRANCH_HANDLERS[branch]
            for data in (self.source, self.built):
                self.assertEqual(data[offset : offset + len(expected)], expected)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_partial_loss_changes_only_declared_diagnostic_fields(self):
        data = self.partial_loss_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {0x18E, 0x18F}
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
            if index == probe_builder.FIRST_ENEMY_RECORD_INDEX:
                allowed.update(
                    {base + FIELD_OFFSETS["x"], base + FIELD_OFFSETS["y"]}
                )
        wrapper = probe_builder.partial_loss_wrapper_code()
        allowed.update(
            range(
                probe_builder.START_MENU_ENTRY_OPERAND,
                probe_builder.START_MENU_ENTRY_OPERAND + 4,
            )
        )
        allowed.update(
            range(
                probe_builder.PARTIAL_LOSS_WRAPPER,
                probe_builder.PARTIAL_LOSS_WRAPPER + len(wrapper),
            )
        )
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)

    def test_partial_loss_preserves_all_allied_and_npc_fixed_records(self):
        data = self.partial_loss_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        start = layout.records_offset
        end = start + probe_builder.FIRST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
        self.assertEqual(data[start:end], self.source[start:end])

    def test_partial_loss_preserves_enemy_identity_and_stock_coordinates(self):
        data = self.partial_loss_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            for field in ("name_id", "class_id", "level"):
                offset = FIELD_OFFSETS[field]
                self.assertEqual(data[base + offset], self.source[base + offset])
            if index == probe_builder.FIRST_ENEMY_RECORD_INDEX:
                self.assertEqual(
                    (
                        data[base + FIELD_OFFSETS["x"]],
                        data[base + FIELD_OFFSETS["y"]],
                    ),
                    probe_builder.PARTIAL_LOSS_TARGET_COORDINATE,
                )
            else:
                self.assertEqual(
                    data[
                        base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1
                    ],
                    self.source[
                        base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1
                    ],
                )

    def test_partial_loss_wrapper_marks_one_resident_and_isolates_target(self):
        code = probe_builder.partial_loss_wrapper_code()
        lost_runtime_group = (
            probe_builder.FIRST_FIXED_RUNTIME_GROUP
            + probe_builder.DEFAULT_LOST_CIVILIAN_RECORDS[0]
        )
        civilian = (
            probe_builder.RUNTIME_GROUP_BASE
            + lost_runtime_group * probe_builder.RUNTIME_GROUP_SIZE
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
            + probe_builder.PARTIAL_LOSS_TARGET_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 01")
            + (target + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        for group in probe_builder.PARTIAL_LOSS_HIDDEN_ENEMY_GROUPS:
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

    def test_partial_loss_wrapper_supports_each_surviving_subset(self):
        for lost_records in ((1,), (2,), (3,), (1, 2), (1, 3), (2, 3)):
            code = probe_builder.partial_loss_wrapper_code(lost_records)
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
                        civilian
                        + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
                    ).to_bytes(4, "big"),
                    code,
                )
        for invalid in ((), (1, 1), (0,), (1, 2, 3)):
            with self.assertRaises(ValueError):
                probe_builder.partial_loss_wrapper_code(invalid)

    def test_partial_loss_checksum_is_valid(self):
        data = self.partial_loss_patched()
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
                probe_builder.PARTIAL_LOSS_WRAPPER,
                probe_builder.PARTIAL_LOSS_WRAPPER + len(wrapper),
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

    def test_turn_event_wrappers_use_the_required_stock_counter_state(self):
        self.assertEqual(
            probe_builder.TURN_EVENT_COUNTER_VALUES,
            {3: 2, 4: 4, 5: 5, 7: 7},
        )
        for target_turn, counter_value in (
            probe_builder.TURN_EVENT_COUNTER_VALUES.items()
        ):
            code = probe_builder.turn_event_wrapper_code(target_turn)
            expected_address = probe_builder.RUNTIME_TURN_COUNTER.to_bytes(
                4, "big"
            )
            prefix_length = (
                len(probe_builder.TURN_EVENT_PROTECTED_RUNTIME_GROUPS) * 8
            )
            for runtime_group in (
                probe_builder.TURN_EVENT_PROTECTED_RUNTIME_GROUPS
            ):
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
                    code[:prefix_length],
                )
            self.assertEqual(
                code[prefix_length : prefix_length + 8],
                bytes.fromhex("0C 39")
                + counter_value.to_bytes(2, "big")
                + expected_address,
            )
            self.assertEqual(
                code[prefix_length + 8 : prefix_length + 10],
                bytes.fromhex("64 08"),
            )
            self.assertEqual(
                code[prefix_length + 10 : prefix_length + 18],
                bytes.fromhex("13 FC")
                + counter_value.to_bytes(2, "big")
                + expected_address,
            )
            self.assertTrue(code.endswith(bytes.fromhex("4E F9 00 02 2C 1E")))

    def test_turn_event_modes_change_only_wrapper_operand_and_checksum(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        fixed_start = layout.records_offset
        fixed_end = fixed_start + layout.record_count * FIXED_RECORD_SIZE
        deployment_end = (
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
            + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4
        )
        for target_turn in probe_builder.TURN_EVENT_HANDLERS:
            data = self.turn_event_patched(target_turn)
            wrapper = probe_builder.turn_event_wrapper_code(target_turn)
            allowed = {0x18E, 0x18F}
            allowed.update(
                range(
                    probe_builder.START_MENU_ENTRY_OPERAND,
                    probe_builder.START_MENU_ENTRY_OPERAND + 4,
                )
            )
            allowed.update(
                range(
                    probe_builder.PARTIAL_LOSS_WRAPPER,
                    probe_builder.PARTIAL_LOSS_WRAPPER + len(wrapper),
                )
            )
            changed = {
                index
                for index, (before, after) in enumerate(zip(self.built, data))
                if before != after
            }
            self.assertLessEqual(changed, allowed)
            self.assertEqual(
                data[
                    probe_builder.DEPLOYMENT_TABLE
                    : deployment_end
                ],
                self.source[
                    probe_builder.DEPLOYMENT_TABLE
                    : deployment_end
                ],
            )
            self.assertEqual(
                data[fixed_start:fixed_end],
                self.source[fixed_start:fixed_end],
            )
            expected_checksum = sum(
                int.from_bytes(data[offset : offset + 2], "big")
                for offset in range(0x200, len(data), 2)
            ) & 0xFFFF
            self.assertEqual(
                int.from_bytes(data[0x18E:0x190], "big"),
                expected_checksum,
            )

    def test_turn_event_wrapper_rejects_unknown_turn(self):
        for target_turn in (1, 2, 6, 8):
            with self.assertRaisesRegex(ValueError, "must be one of"):
                probe_builder.turn_event_wrapper_code(target_turn)

    def test_turn7_branch_modes_only_redirect_the_stock_table_target(self):
        for branch, target in probe_builder.TURN7_BRANCH_HANDLERS.items():
            if branch == "stock":
                continue
            data = bytearray(self.built)
            checksum = probe_builder.patch_probe(
                data,
                self.source,
                turn_event=7,
                turn_event_branch=branch,
            )
            wrapper = probe_builder.turn_event_wrapper_code(7)
            allowed = {0x18E, 0x18F}
            allowed.update(
                range(
                    probe_builder.START_MENU_ENTRY_OPERAND,
                    probe_builder.START_MENU_ENTRY_OPERAND + 4,
                )
            )
            allowed.update(
                range(
                    probe_builder.TURN_EVENT_TABLE_TURN7_TARGET,
                    probe_builder.TURN_EVENT_TABLE_TURN7_TARGET + 4,
                )
            )
            allowed.update(
                range(
                    probe_builder.PARTIAL_LOSS_WRAPPER,
                    probe_builder.PARTIAL_LOSS_WRAPPER + len(wrapper),
                )
            )
            changed = {
                index
                for index, (before, after) in enumerate(zip(self.built, data))
                if before != after
            }
            self.assertLessEqual(changed, allowed)
            target_offset = probe_builder.TURN_EVENT_TABLE_TURN7_TARGET
            self.assertEqual(
                int.from_bytes(data[target_offset : target_offset + 4], "big"),
                target,
            )
            self.assertEqual(
                int.from_bytes(data[0x18E:0x190], "big"),
                checksum,
            )

    def test_turn7_branch_modes_reject_other_turns_and_unknown_names(self):
        with self.assertRaisesRegex(ValueError, "require --turn-event 7"):
            probe_builder.patch_probe(
                bytearray(self.built),
                self.source,
                turn_event=5,
                turn_event_branch="late-arrival",
            )
        with self.assertRaisesRegex(ValueError, "branch must be one of"):
            probe_builder.patch_probe(
                bytearray(self.built),
                self.source,
                turn_event=7,
                turn_event_branch="not-a-branch",
            )

    def test_probe_rejects_conflicting_runtime_modes(self):
        for options in (
            {"civilian_loss": True, "protagonist_death": True},
            {"civilian_loss": True, "turn_event": 3},
            {"protagonist_death": True, "turn_event": 7},
        ):
            with self.assertRaisesRegex(ValueError, "modes conflict"):
                probe_builder.patch_probe(
                    bytearray(self.built),
                    self.source,
                    **options,
                )

    def test_protagonist_death_checksum_is_valid(self):
        data = self.protagonist_death_patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)


if __name__ == "__main__":
    unittest.main()
