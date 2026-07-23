import unittest

from tools import build_scenario24_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario24ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(data, self.source)
        return data

    def completion_target_patched(self) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            completion_target_only=True,
        )
        return data

    def allowed_offsets(
        self,
        *,
        completion_target_only: bool = False,
    ) -> set[int]:
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
        if completion_target_only:
            size = len(
                probe_builder.deployment_bytes(
                    (probe_builder.COMPLETION_ELWIN_POSITION,)
                )
            )
            allowed.update(
                range(
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET,
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + size,
                )
            )
            for index in probe_builder.COMPLETION_HIDDEN_RECORD_INDEXES:
                allowed.add(layout.records_offset + index * FIXED_RECORD_SIZE)
            wrapper = probe_builder.completion_hp_wrapper_code()
            allowed.update(
                range(
                    probe_builder.START_MENU_ENTRY_OPERAND,
                    probe_builder.START_MENU_ENTRY_OPERAND + 4,
                )
            )
            allowed.update(
                range(
                    probe_builder.COMPLETION_HP_WRAPPER,
                    probe_builder.COMPLETION_HP_WRAPPER + len(wrapper),
                )
            )
        return allowed

    def test_changes_only_declared_enemy_fields_and_checksum(self):
        data = self.patched()
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, self.allowed_offsets())

    def test_preserves_special_side_bernhardt_byte_identical(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = (
            layout.records_offset
            + probe_builder.BERNHARDT_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            data[base : base + FIXED_RECORD_SIZE],
            self.source[base : base + FIXED_RECORD_SIZE],
        )
        self.assertEqual(self.source[base + 0x08], 0x08)
        self.assertEqual(self.source[base + FIELD_OFFSETS["name_id"]], 0x0E)
        self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], 0x4E)

    def test_weakens_only_enemy_records_without_changing_identity(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(1, layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(self.source[base + 0x08], 0x04)
            self.assertFalse(bool(self.source[base] & 0x80))
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)
            for offset in (
                0,
                0x08,
                FIELD_OFFSETS["level"],
                FIELD_OFFSETS["name_id"],
                FIELD_OFFSETS["class_id"],
                FIELD_OFFSETS["x"],
                FIELD_OFFSETS["y"],
            ):
                self.assertEqual(data[base + offset], self.source[base + offset])

    def test_preserves_representative_monster_records(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            probe_builder.DEMON_LORD_RECORD_INDEX: (
                0x65,
                0x5D,
                1,
                46,
                30,
                (29, 9),
            ),
            probe_builder.CERBERUS_RECORD_INDEX: (
                0x4D,
                0x52,
                10,
                37,
                28,
                (27, 22),
            ),
            probe_builder.VAMPIRE_LORD_RECORD_INDEX: (
                0x4A,
                0x5F,
                1,
                43,
                34,
                (16, 23),
            ),
        }
        for index, values in expected.items():
            name_id, class_id, level, at, df, coordinates = values
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(self.source[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], class_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["level"]], level)
            self.assertEqual(self.source[base + FIELD_OFFSETS["at"]], at)
            self.assertEqual(self.source[base + FIELD_OFFSETS["df"]], df)
            self.assertEqual(
                tuple(
                    self.source[
                        base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1
                    ]
                ),
                coordinates,
            )
            self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], class_id)

    def test_preserves_player_deployments_and_event_header(self):
        data = self.patched()
        expected = probe_builder.deployment_bytes(
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS
        )
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(data[start : start + len(expected)], expected)
        self.assertEqual(
            data[probe_builder.SCENARIO_HEADER : probe_builder.DEPLOYMENT_TABLE],
            self.source[probe_builder.SCENARIO_HEADER : probe_builder.DEPLOYMENT_TABLE],
        )

    def test_completion_target_preserves_coordinates_and_hides_only_other_enemies(self):
        data = self.completion_target_patched()
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(
            changed,
            self.allowed_offsets(completion_target_only=True),
        )

        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        expected = probe_builder.deployment_bytes(
            (probe_builder.COMPLETION_ELWIN_POSITION,)
        )
        self.assertEqual(data[start : start + len(expected)], expected)

        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                data[
                    base + FIELD_OFFSETS["x"] :
                    base + FIELD_OFFSETS["y"] + 1
                ],
                self.source[
                    base + FIELD_OFFSETS["x"] :
                    base + FIELD_OFFSETS["y"] + 1
                ],
            )
            if index in (
                probe_builder.BERNHARDT_RECORD_INDEX,
                probe_builder.COMPLETION_TARGET_RECORD_INDEX,
            ):
                self.assertEqual(data[base] & 0x80, self.source[base] & 0x80)
            else:
                self.assertEqual(data[base] & 0x80, 0x80)

    def test_completion_wrapper_covers_special_actor_and_all_enemy_groups(self):
        code = probe_builder.completion_hp_wrapper_code()
        for group in probe_builder.COMPLETION_HIDDEN_RUNTIME_GROUPS:
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            hide = (
                bytes.fromhex("13 FC 00 FF")
                + (record + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big")
            )
            self.assertIn(hide, code)
            defeat = (
                bytes.fromhex("13 FC 00 00")
                + (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big")
            )
            self.assertIn(defeat, code)
        for group in range(
            probe_builder.FIRST_FIXED_RUNTIME_GROUP,
            probe_builder.LAST_FIXED_RUNTIME_GROUP + 1,
        ):
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertIn(
                (record + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
                code,
            )
            self.assertIn(
                (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
                code,
            )
        self.assertEqual(code.count(bytes.fromhex("67 12")), 11)
        self.assertEqual(code.count(bytes.fromhex("67 08")), 11)
        self.assertEqual(code.count(bytes.fromhex("13 FC 00 01")), 11)
        self.assertTrue(
            code.endswith(
                bytes.fromhex("41 F9")
                + probe_builder.START_MENU_ENTRY.to_bytes(4, "big")
                + bytes.fromhex("4E F9")
                + probe_builder.START_MENU_ENTRY.to_bytes(4, "big")
            )
        )

        data = self.completion_target_patched()
        self.assertEqual(
            data[
                probe_builder.START_MENU_ENTRY_OPERAND :
                probe_builder.START_MENU_ENTRY_OPERAND + 4
            ],
            probe_builder.COMPLETION_HP_WRAPPER.to_bytes(4, "big"),
        )
        self.assertEqual(
            data[
                probe_builder.COMPLETION_HP_WRAPPER :
                probe_builder.COMPLETION_HP_WRAPPER + len(code)
            ],
            code,
        )

    def test_completion_target_rejects_changed_start_entry_or_occupied_wrapper(self):
        damaged = bytearray(self.production)
        damaged[probe_builder.START_MENU_ENTRY_OPERAND] ^= 1
        with self.assertRaisesRegex(ValueError, "Start-menu entry operand"):
            probe_builder.patch_probe(
                damaged,
                self.source,
                completion_target_only=True,
            )

        damaged = bytearray(self.production)
        damaged[probe_builder.COMPLETION_HP_WRAPPER] = 0
        with self.assertRaisesRegex(ValueError, "wrapper region"):
            probe_builder.patch_probe(
                damaged,
                self.source,
                completion_target_only=True,
            )

    def test_current_probe_checksums_are_locked(self):
        self.assertEqual(self.patched()[0x18E:0x190], bytes.fromhex("63 AE"))
        self.assertEqual(
            self.completion_target_patched()[0x18E:0x190],
            bytes.fromhex("08 D4"),
        )

    def test_rejects_non_source_fixed_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 0"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
