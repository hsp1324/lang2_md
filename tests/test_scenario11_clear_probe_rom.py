import unittest

from tools import build_scenario11_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario11ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(data, self.source)
        return data

    def death_patched(self, mode: str) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            protagonist_death=mode == "protagonist",
            jessica_death=mode == "jessica",
        )
        return data

    def test_death_modes_change_only_wrapper_and_checksum(self):
        for mode, group in (
            ("protagonist", probe_builder.PROTAGONIST_RUNTIME_GROUP),
            ("jessica", probe_builder.JESSICA_RUNTIME_GROUP),
        ):
            with self.subTest(mode=mode):
                data = self.death_patched(mode)
                wrapper = probe_builder.mark_runtime_group_defeated_code(group)
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

    def test_death_modes_preserve_all_fixed_records(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for mode in ("protagonist", "jessica"):
            with self.subTest(mode=mode):
                data = self.death_patched(mode)
                for index in range(layout.record_count):
                    start = layout.records_offset + index * FIXED_RECORD_SIZE
                    end = start + FIXED_RECORD_SIZE
                    self.assertEqual(data[start:end], self.source[start:end])

    def test_death_wrappers_target_only_requested_runtime_group(self):
        protagonist = probe_builder.mark_runtime_group_defeated_code(
            probe_builder.PROTAGONIST_RUNTIME_GROUP
        )
        jessica = probe_builder.mark_runtime_group_defeated_code(
            probe_builder.JESSICA_RUNTIME_GROUP
        )
        protagonist_record = probe_builder.RUNTIME_GROUP_BASE
        jessica_record = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.JESSICA_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            (protagonist_record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            protagonist,
        )
        self.assertNotIn(
            (jessica_record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            protagonist,
        )
        self.assertIn(
            (jessica_record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            jessica,
        )
        self.assertNotIn(
            (protagonist_record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            jessica,
        )
        self.assertEqual(
            jessica[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_death_modes_reject_safe_layout_options(self):
        data = bytearray(self.production)
        with self.assertRaisesRegex(ValueError, "safe-layout"):
            probe_builder.patch_probe(
                data,
                self.source,
                protagonist_death=True,
                safe_elwin=True,
            )

    def test_death_modes_conflict(self):
        data = bytearray(self.production)
        with self.assertRaisesRegex(ValueError, "modes conflict"):
            probe_builder.patch_probe(
                data,
                self.source,
                protagonist_death=True,
                jessica_death=True,
            )

    def test_death_mode_checksums_are_valid(self):
        for mode, checksum in (("protagonist", 0x949F), ("jessica", 0x9B5F)):
            with self.subTest(mode=mode):
                data = self.death_patched(mode)
                expected = sum(
                    int.from_bytes(data[offset : offset + 2], "big")
                    for offset in range(0x200, len(data), 2)
                ) & 0xFFFF
                self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)
                self.assertEqual(expected, checksum)

    def test_changes_only_enemy_combat_fields_and_checksum(self):
        data = self.patched()
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
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)

    def test_preserves_jessica_deployment_positions_and_events(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        self.assertEqual(
            data[layout.records_offset : layout.records_offset + FIXED_RECORD_SIZE],
            self.source[
                layout.records_offset : layout.records_offset + FIXED_RECORD_SIZE
            ],
        )
        self.assertEqual(
            data[probe_builder.SCENARIO_HEADER : layout.records_offset],
            self.source[probe_builder.SCENARIO_HEADER : layout.records_offset],
        )
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            for field in ("level", "x", "y", "name_id", "class_id"):
                self.assertEqual(
                    data[base + FIELD_OFFSETS[field]],
                    self.source[base + FIELD_OFFSETS[field]],
                )

    def test_weakens_every_imperial_group_including_hidden_reinforcement(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(
                data[mercenary_offset : mercenary_offset + 6],
                b"\xFF" * 6,
            )

    def test_preserves_stock_first_player_deployment(self):
        data = self.patched()
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(
            data[start : start + 4],
            probe_builder.SOURCE_FIRST_PLAYER_DEPLOYMENT,
        )

    def test_safe_elwin_option_changes_only_first_deployment_and_probe_fields(self):
        data = bytearray(self.production)
        probe_builder.patch_probe(data, self.source, safe_elwin=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {
            0x18E,
            0x18F,
            *range(
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET,
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 4,
            ),
        }
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
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(
            data[start : start + 4],
            probe_builder.SAFE_FIRST_PLAYER_DEPLOYMENT,
        )

    def test_safe_clear_layout_changes_only_enemy_level_class_and_visible_positions(self):
        data = bytearray(self.production)
        probe_builder.patch_probe(data, self.source, safe_clear_layout=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {
            0x18E,
            0x18F,
            *range(
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET,
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
                + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4,
            ),
        }
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            allowed.update(
                {
                    base + FIELD_OFFSETS["at"],
                    base + FIELD_OFFSETS["df"],
                    base + FIELD_OFFSETS["level"],
                    base + FIELD_OFFSETS["class_id"],
                    *(
                        base + FIELD_OFFSETS["mercenaries"] + slot
                        for slot in range(6)
                    ),
                }
            )
            if index in probe_builder.SAFE_CLEAR_VISIBLE_POSITIONS:
                allowed.update(
                    {
                        base + FIELD_OFFSETS["x"],
                        base + FIELD_OFFSETS["y"],
                    }
                )
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                data[base + FIELD_OFFSETS["level"]],
                probe_builder.SAFE_CLEAR_ENEMY_LEVEL,
            )
            self.assertEqual(
                data[base + FIELD_OFFSETS["class_id"]],
                probe_builder.SAFE_CLEAR_ENEMY_CLASS,
            )
            self.assertEqual(
                data[base + FIELD_OFFSETS["name_id"]],
                self.source[base + FIELD_OFFSETS["name_id"]],
            )
        for index, (x, y) in probe_builder.SAFE_CLEAR_VISIBLE_POSITIONS.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base + FIELD_OFFSETS["x"]], x)
            self.assertEqual(data[base + FIELD_OFFSETS["y"]], y)
        for index, (x, y) in enumerate(probe_builder.SAFE_PLAYER_DEPLOYMENTS):
            offset = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + index * 4
            self.assertEqual(data[offset : offset + 2], x.to_bytes(2, "big"))
            self.assertEqual(data[offset + 2 : offset + 4], y.to_bytes(2, "big"))
        hidden = layout.records_offset + probe_builder.LAST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
        self.assertEqual(
            data[hidden + FIELD_OFFSETS["x"] : hidden + FIELD_OFFSETS["y"] + 1],
            self.source[hidden + FIELD_OFFSETS["x"] : hidden + FIELD_OFFSETS["y"] + 1],
        )

    def test_safe_clear_layout_places_egbert_adjacent_to_safe_elwin(self):
        self.assertEqual(
            probe_builder.SAFE_CLEAR_VISIBLE_POSITIONS[
                probe_builder.FIRST_ENEMY_RECORD_INDEX
            ],
            (18, 21),
        )
        elwin_x = int.from_bytes(
            probe_builder.SAFE_FIRST_PLAYER_DEPLOYMENT[:2], "big"
        )
        elwin_y = int.from_bytes(
            probe_builder.SAFE_FIRST_PLAYER_DEPLOYMENT[2:], "big"
        )
        egbert_x, egbert_y = probe_builder.SAFE_CLEAR_VISIBLE_POSITIONS[
            probe_builder.FIRST_ENEMY_RECORD_INDEX
        ]
        self.assertEqual(abs(egbert_x - elwin_x) + abs(egbert_y - elwin_y), 1)

    def test_safe_player_assault_layout_has_unique_positions(self):
        self.assertEqual(
            len(set(probe_builder.SAFE_PLAYER_DEPLOYMENTS)),
            probe_builder.PLAYER_DEPLOYMENT_COUNT,
        )
        self.assertFalse(
            set(probe_builder.SAFE_PLAYER_DEPLOYMENTS)
            & set(probe_builder.SAFE_CLEAR_VISIBLE_POSITIONS.values())
        )

    def test_safe_jessica_changes_only_her_coordinates_and_probe_fields(self):
        data = bytearray(self.production)
        probe_builder.patch_probe(data, self.source, safe_jessica=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = layout.records_offset
        allowed = {
            0x18E,
            0x18F,
            base + FIELD_OFFSETS["x"],
            base + FIELD_OFFSETS["y"],
        }
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            enemy = layout.records_offset + index * FIXED_RECORD_SIZE
            allowed.update(
                {
                    enemy + FIELD_OFFSETS["at"],
                    enemy + FIELD_OFFSETS["df"],
                    *(
                        enemy + FIELD_OFFSETS["mercenaries"] + slot
                        for slot in range(6)
                    ),
                }
            )
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)
        self.assertEqual(
            (
                data[base + FIELD_OFFSETS["x"]],
                data[base + FIELD_OFFSETS["y"]],
            ),
            probe_builder.SAFE_JESSICA_POSITION,
        )
        for field in ("level", "at", "df", "name_id", "class_id", "mercenaries"):
            offset = FIELD_OFFSETS[field]
            size = 6 if field == "mercenaries" else 1
            self.assertEqual(
                data[base + offset : base + offset + size],
                self.source[base + offset : base + offset + size],
            )

    def test_safe_jessica_position_does_not_overlap_assault_layout(self):
        self.assertNotIn(
            probe_builder.SAFE_JESSICA_POSITION,
            probe_builder.SAFE_PLAYER_DEPLOYMENTS,
        )
        self.assertNotIn(
            probe_builder.SAFE_JESSICA_POSITION,
            probe_builder.SAFE_CLEAR_VISIBLE_POSITIONS.values(),
        )

    def test_current_safe_jessica_build_checksum(self):
        data = bytearray(self.production)
        checksum = probe_builder.patch_probe(
            data,
            self.source,
            safe_clear_layout=True,
            safe_jessica=True,
        )
        self.assertEqual(checksum, probe_builder.EXPECTED_SAFE_JESSICA_CHECKSUM)

    def test_rejects_non_source_enemy_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[
            layout.records_offset
            + probe_builder.FIRST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
        ] ^= 1
        with self.assertRaisesRegex(ValueError, "enemy record 1"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
