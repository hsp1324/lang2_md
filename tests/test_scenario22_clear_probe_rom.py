import unittest

from tools import build_scenario22_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario22ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(
        self,
        *,
        completion_hp: bool = False,
        completion_layout: bool = False,
    ) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            completion_hp=completion_hp,
            completion_layout=completion_layout,
        )
        return data

    def allowed_offsets(
        self,
        *,
        completion_hp: bool = False,
        completion_layout: bool = False,
    ) -> set[int]:
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {0x18E, 0x18F}
        for index in range(
            probe_builder.FIRST_COMBAT_RECORD_INDEX,
            probe_builder.LAST_COMBAT_RECORD_INDEX + 1,
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
        if completion_layout:
            for index in range(len(probe_builder.COMPLETION_PLAYER_DEPLOYMENTS)):
                player = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + index * 4
                allowed.update({player + 1, player + 3})
        if completion_hp or completion_layout:
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

    def test_changes_only_declared_combat_fields_and_checksum(self):
        data = self.patched()
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, self.allowed_offsets())

    def test_preserves_allied_liana_record_byte_identical(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = layout.records_offset + probe_builder.LIANA_RECORD_INDEX * FIXED_RECORD_SIZE
        self.assertEqual(
            data[base : base + FIXED_RECORD_SIZE],
            self.source[base : base + FIXED_RECORD_SIZE],
        )
        self.assertEqual(self.source[base + 0x08], 0x03)
        self.assertEqual(self.source[base + FIELD_OFFSETS["name_id"]], 0x02)
        self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], 0x97)

    def test_weakens_special_and_enemy_records_without_changing_ownership(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(1, layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertIn(self.source[base + 0x08], (0x04, 0x08))
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

    def test_preserves_lana_bozel_bernhardt_and_egbert(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            probe_builder.LANA_RECORD_INDEX: (0x0C, 0x60, 6, 39, 36, 0x08, False),
            probe_builder.BOZEL_RECORD_INDEX: (0x10, 0x61, 6, 42, 32, 0x08, False),
            probe_builder.BERNHARDT_RECORD_INDEX: (0x0E, 0x4E, 10, 58, 41, 0x04, True),
            probe_builder.EGBERT_RECORD_INDEX: (0x14, 0x4F, 8, 44, 32, 0x08, False),
        }
        for index, values in expected.items():
            name_id, class_id, level, at, df, side_id, hidden = values
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(bool(self.source[base] & 0x80), hidden)
            self.assertEqual(self.source[base + 0x08], side_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], class_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["level"]], level)
            self.assertEqual(self.source[base + FIELD_OFFSETS["at"]], at)
            self.assertEqual(self.source[base + FIELD_OFFSETS["df"]], df)
            self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], class_id)
            if hidden:
                self.assertEqual(
                    data[
                        base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1
                    ],
                    b"\xFF\xFF",
                )

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

    def test_completion_hp_wrapper_only_touches_present_living_enemies(self):
        code = probe_builder.completion_hp_wrapper_code()
        for group in range(
            probe_builder.FIRST_ENEMY_RUNTIME_GROUP,
            probe_builder.LAST_ENEMY_RUNTIME_GROUP + 1,
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

        data = self.patched(completion_hp=True)
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(
            changed,
            self.allowed_offsets(completion_hp=True),
        )
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

    def test_completion_hp_checksum_is_locked(self):
        data = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(
                data,
                self.source,
                completion_hp=True,
            ),
            0xFF01,
        )

    def test_completion_layout_stages_players_without_moving_enemies(self):
        data = self.patched(completion_layout=True)
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(
            changed,
            self.allowed_offsets(completion_layout=True),
        )
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        expected = probe_builder.deployment_bytes(
            probe_builder.COMPLETION_PLAYER_DEPLOYMENTS
        )
        self.assertEqual(data[start : start + len(expected)], expected)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                data[
                    enemy + FIELD_OFFSETS["x"] :
                    enemy + FIELD_OFFSETS["y"] + 1
                ],
                self.source[
                    enemy + FIELD_OFFSETS["x"] :
                    enemy + FIELD_OFFSETS["y"] + 1
                ],
            )
        adjacent_record_indexes = (1, 2, 4, 5, 6, 7, 8, 9)
        for player, record_index in zip(
            probe_builder.COMPLETION_PLAYER_DEPLOYMENTS,
            adjacent_record_indexes,
        ):
            enemy = layout.records_offset + record_index * FIXED_RECORD_SIZE
            enemy_position = (
                self.source[enemy + FIELD_OFFSETS["x"]],
                self.source[enemy + FIELD_OFFSETS["y"]],
            )
            self.assertEqual(
                abs(player[0] - enemy_position[0])
                + abs(player[1] - enemy_position[1]),
                1,
            )

    def test_completion_layout_checksum_is_locked(self):
        data = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(
                data,
                self.source,
                completion_layout=True,
            ),
            0xFDFF,
        )

    def test_rejects_non_source_fixed_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 0"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
