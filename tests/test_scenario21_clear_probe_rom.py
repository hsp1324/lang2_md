import unittest

from tools import build_scenario21_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario21ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(
        self,
        *,
        completion_layout: bool = False,
        protagonist_death: bool = False,
    ) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            completion_layout=completion_layout,
            protagonist_death=protagonist_death,
        )
        return data

    def allowed_offsets(
        self,
        *,
        completion_layout: bool = False,
        protagonist_death: bool = False,
    ) -> set[int]:
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {0x18E, 0x18F}
        if not protagonist_death:
            for index in range(layout.record_count):
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
        if completion_layout or protagonist_death:
            wrapper = (
                probe_builder.protagonist_death_wrapper_code()
                if protagonist_death
                else probe_builder.completion_hp_wrapper_code()
            )
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
            if completion_layout:
                for index in range(
                    len(probe_builder.COMPLETION_PLAYER_DEPLOYMENTS)
                ):
                    player = (
                        probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + index * 4
                    )
                    allowed.update({player + 1, player + 3})
                for index in probe_builder.COMPLETION_ENEMY_POSITIONS:
                    enemy = layout.records_offset + index * FIXED_RECORD_SIZE
                    allowed.update(
                        {
                            enemy + FIELD_OFFSETS["x"],
                            enemy + FIELD_OFFSETS["y"],
                        }
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

    def test_weakens_every_enemy_without_changing_identity(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(self.source[base + 0x08], 0x04)
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)
            for offset in (
                0,
                FIELD_OFFSETS["level"],
                FIELD_OFFSETS["name_id"],
                FIELD_OFFSETS["class_id"],
                FIELD_OFFSETS["x"],
                FIELD_OFFSETS["y"],
            ):
                self.assertEqual(data[base + offset], self.source[base + offset])

    def test_preserves_lana_and_hidden_reinforcements(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            probe_builder.LANA_RECORD_INDEX: (0x0C, 0x60, 6, 39, 36, False),
            7: (0x60, 0x5B, 5, 40, 32, True),
            8: (0x61, 0x5B, 8, 41, 35, True),
            9: (0x62, 0x5B, 5, 40, 32, True),
            10: (0x2A, 0x42, 6, 39, 27, True),
        }
        for index, (name_id, class_id, level, at, df, hidden) in expected.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(bool(self.source[base] & 0x80), hidden)
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

    def test_completion_layout_stages_all_stock_reveal_events(self):
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
        lana_source = layout.records_offset + (
            probe_builder.LANA_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        expected_lana = bytearray(
            self.source[lana_source : lana_source + FIXED_RECORD_SIZE]
        )
        expected_lana[FIELD_OFFSETS["at"]] = probe_builder.PROBE_AT
        expected_lana[FIELD_OFFSETS["df"]] = probe_builder.PROBE_DF
        mercenaries = FIELD_OFFSETS["mercenaries"]
        expected_lana[mercenaries : mercenaries + 6] = b"\xFF" * 6
        self.assertEqual(
            data[lana_source : lana_source + FIXED_RECORD_SIZE], expected_lana
        )
        for index, position in probe_builder.COMPLETION_ENEMY_POSITIONS.items():
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                (
                    data[enemy + FIELD_OFFSETS["x"]],
                    data[enemy + FIELD_OFFSETS["y"]],
                ),
                position,
            )
        for index in probe_builder.HIDDEN_ENEMY_RECORD_INDEXES:
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            expected_enemy = bytearray(
                self.source[enemy : enemy + FIXED_RECORD_SIZE]
            )
            expected_enemy[FIELD_OFFSETS["at"]] = probe_builder.PROBE_AT
            expected_enemy[FIELD_OFFSETS["df"]] = probe_builder.PROBE_DF
            expected_enemy[mercenaries : mercenaries + 6] = b"\xFF" * 6
            self.assertEqual(
                data[enemy : enemy + FIXED_RECORD_SIZE], expected_enemy
            )
        self.assertEqual(
            probe_builder.COMPLETION_PLAYER_DEPLOYMENTS[2:5],
            ((2, 4), (2, 16), (2, 26)),
        )
        for player, reveal in zip(
            probe_builder.COMPLETION_PLAYER_DEPLOYMENTS[2:5],
            probe_builder.KRAKEN_REVEAL_POSITIONS,
        ):
            self.assertEqual(
                abs(player[0] - reveal[0]) + abs(player[1] - reveal[1]),
                1,
            )
        self.assertEqual(
            abs(
                probe_builder.COMPLETION_PLAYER_DEPLOYMENTS[1][0]
                - probe_builder.ARCHMAGE_REVEAL_POSITION[0]
            )
            + abs(
                probe_builder.COMPLETION_PLAYER_DEPLOYMENTS[1][1]
                - probe_builder.ARCHMAGE_REVEAL_POSITION[1]
            ),
            1,
        )

    def test_completion_hp_wrapper_only_touches_present_living_groups(self):
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

        data = self.patched(completion_layout=True)
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

    def test_protagonist_death_mode_preserves_source_and_uses_stock_event(self):
        data = self.patched(protagonist_death=True)
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(
            changed,
            self.allowed_offsets(protagonist_death=True),
        )
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        self.assertEqual(
            data[
                layout.record_list_offset :
                layout.records_offset + layout.record_count * FIXED_RECORD_SIZE
            ],
            self.source[
                layout.record_list_offset :
                layout.records_offset + layout.record_count * FIXED_RECORD_SIZE
            ],
        )
        trigger_start = probe_builder.PROTAGONIST_DEATH_TRIGGER
        trigger_end = (
            trigger_start + len(probe_builder.PROTAGONIST_DEATH_TRIGGER_BYTES)
        )
        self.assertEqual(
            data[trigger_start:trigger_end],
            probe_builder.PROTAGONIST_DEATH_TRIGGER_BYTES,
        )
        event_start = probe_builder.PROTAGONIST_DEATH_EVENT
        event_end = event_start + len(probe_builder.PROTAGONIST_DEATH_EVENT_BYTES)
        self.assertEqual(
            data[event_start:event_end],
            probe_builder.PROTAGONIST_DEATH_EVENT_BYTES,
        )
        self.assertIn(
            probe_builder.PROTAGONIST_DEATH_TEXT.to_bytes(4, "big"),
            probe_builder.PROTAGONIST_DEATH_EVENT_BYTES,
        )
        self.assertIn(b"\x13\xFF", probe_builder.PROTAGONIST_DEATH_EVENT_BYTES)

        code = probe_builder.protagonist_death_wrapper_code()
        record = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.PROTAGONIST_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            (record + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(
                4, "big"
            ),
            code,
        )
        self.assertIn(
            (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            (record + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
            code,
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

    def test_diagnostic_modes_conflict(self):
        with self.assertRaisesRegex(ValueError, "diagnostic modes conflict"):
            probe_builder.patch_probe(
                bytearray(self.production),
                self.source,
                completion_layout=True,
                protagonist_death=True,
            )

    def test_default_and_completion_checksums_are_locked(self):
        default = bytearray(self.production)
        completion = bytearray(self.production)
        protagonist_death = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(default, self.source),
            0x1AAC,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                completion,
                self.source,
                completion_layout=True,
            ),
            0xB5E9,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                protagonist_death,
                self.source,
                protagonist_death=True,
            ),
            0x90CC,
        )

    def test_rejects_non_source_fixed_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 0"):
            probe_builder.patch_probe(damaged, self.source)

    def test_rejects_changed_protagonist_death_event(self):
        damaged = bytearray(self.production)
        damaged[probe_builder.PROTAGONIST_DEATH_EVENT] ^= 1
        with self.assertRaisesRegex(ValueError, "protagonist-death event"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
