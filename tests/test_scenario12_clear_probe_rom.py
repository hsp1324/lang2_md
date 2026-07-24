import unittest

from tools import build_scenario12_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario12ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(
        self,
        *,
        compact_layout: bool = False,
        protagonist_death: bool = False,
    ) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            compact_layout=compact_layout,
            protagonist_death=protagonist_death,
        )
        return data

    def allowed_probe_offsets(self, *, compact_layout: bool = False) -> set[int]:
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
            if compact_layout and index in probe_builder.COMPACT_VISIBLE_ENEMY_POSITIONS:
                allowed.update(
                    {
                        base + FIELD_OFFSETS["x"],
                        base + FIELD_OFFSETS["y"],
                    }
                )
        if compact_layout:
            allowed.update(
                range(
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET,
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
                    + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4,
                )
            )
        return allowed

    def changed_offsets(self, data: bytes) -> set[int]:
        return {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }

    def test_source_verified_scenario_triggers_are_preserved(self):
        data = self.patched()
        for offset, expected in probe_builder.SCENARIO_TRIGGERS.items():
            with self.subTest(offset=f"0x{offset:06X}"):
                self.assertEqual(
                    self.source[offset : offset + len(expected)],
                    expected,
                )
                self.assertEqual(data[offset : offset + len(expected)], expected)

    def test_protagonist_death_changes_only_wrapper_and_checksum(self):
        data = self.patched(protagonist_death=True)
        wrapper = probe_builder.mark_runtime_group_defeated_code(
            probe_builder.PROTAGONIST_RUNTIME_GROUP
        )
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
        self.assertLessEqual(self.changed_offsets(data), allowed)

    def test_protagonist_death_preserves_all_fixed_records_and_deployments(self):
        data = self.patched(protagonist_death=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        end = start + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4
        self.assertEqual(data[start:end], self.source[start:end])
        fixed_end = (
            layout.records_offset
            + layout.record_count * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            data[layout.records_offset:fixed_end],
            self.source[layout.records_offset:fixed_end],
        )

    def test_protagonist_death_wrapper_targets_only_group_zero(self):
        wrapper = probe_builder.mark_runtime_group_defeated_code(
            probe_builder.PROTAGONIST_RUNTIME_GROUP
        )
        record = probe_builder.RUNTIME_GROUP_BASE
        self.assertIn(
            (record + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(
                4, "big"
            ),
            wrapper,
        )
        self.assertIn(
            (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            wrapper,
        )
        self.assertEqual(
            wrapper[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_diagnostic_modes_conflict(self):
        for kwargs in (
            {"compact_layout": True, "protagonist_death": True},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, "conflict"):
                    probe_builder.patch_probe(
                        bytearray(self.production),
                        self.source,
                        **kwargs,
                    )

    def test_diagnostic_checksums_are_valid(self):
        for kwargs in ({"protagonist_death": True},):
            with self.subTest(kwargs=kwargs):
                data = self.patched(**kwargs)
                expected = sum(
                    int.from_bytes(data[offset : offset + 2], "big")
                    for offset in range(0x200, len(data), 2)
                ) & 0xFFFF
                self.assertEqual(
                    int.from_bytes(data[0x18E:0x190], "big"),
                    expected,
                )
                self.assertEqual(expected, 0xF7AB)

    def test_base_probe_changes_only_enemy_combat_fields_and_checksum(self):
        data = self.patched()
        self.assertLessEqual(self.changed_offsets(data), self.allowed_probe_offsets())

    def test_weakens_every_guardian_including_hidden_egbert(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            start = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[start : start + 6], b"\xFF" * 6)

    def test_preserves_identity_class_level_hidden_state_and_events(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        self.assertEqual(
            data[probe_builder.SCENARIO_HEADER : layout.records_offset],
            self.source[probe_builder.SCENARIO_HEADER : layout.records_offset],
        )
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            for offset in (0, FIELD_OFFSETS["level"], FIELD_OFFSETS["name_id"], FIELD_OFFSETS["class_id"]):
                self.assertEqual(data[base + offset], self.source[base + offset])

    def test_preserves_stock_player_and_enemy_coordinates_by_default(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        size = probe_builder.PLAYER_DEPLOYMENT_COUNT * 4
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(data[start : start + size], self.source[start : start + size])
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                data[base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1],
                self.source[
                    base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1
                ],
            )

    def test_compact_layout_changes_only_declared_coordinates_and_probe_fields(self):
        data = self.patched(compact_layout=True)
        self.assertLessEqual(
            self.changed_offsets(data),
            self.allowed_probe_offsets(compact_layout=True),
        )
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index, (x, y) in probe_builder.COMPACT_VISIBLE_ENEMY_POSITIONS.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                (data[base + FIELD_OFFSETS["x"]], data[base + FIELD_OFFSETS["y"]]),
                (x, y),
            )
        expected = probe_builder.deployment_bytes(
            probe_builder.COMPACT_PLAYER_DEPLOYMENTS
        )
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(data[start : start + len(expected)], expected)

    def test_compact_layout_preserves_hidden_egbert_coordinates(self):
        data = self.patched(compact_layout=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = (
            layout.records_offset
            + probe_builder.LAST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1],
            b"\xFF\xFF",
        )

    def test_compact_positions_are_unique_and_do_not_overlap(self):
        players = set(probe_builder.COMPACT_PLAYER_DEPLOYMENTS)
        enemies = set(probe_builder.COMPACT_VISIBLE_ENEMY_POSITIONS.values())
        self.assertEqual(len(players), probe_builder.PLAYER_DEPLOYMENT_COUNT)
        self.assertEqual(
            len(enemies), probe_builder.LAST_VISIBLE_ENEMY_RECORD_INDEX + 1
        )
        self.assertFalse(players & enemies)

    def test_rejects_non_source_enemy_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "enemy record 0"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
