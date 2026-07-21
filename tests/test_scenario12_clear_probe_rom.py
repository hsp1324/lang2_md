import unittest

from tools import build_scenario12_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario12ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(self, *, compact_layout: bool = False) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            compact_layout=compact_layout,
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
