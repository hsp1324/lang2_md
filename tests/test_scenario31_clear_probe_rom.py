import unittest

from tools import build_scenario31_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario31ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(
        self,
        *,
        compact_layout: bool = False,
        completion_layout: bool = False,
    ) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            compact_layout=compact_layout,
            completion_layout=completion_layout,
        )
        return data

    def allowed_offsets(
        self,
        *,
        compact_layout: bool = False,
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
            if compact_layout:
                allowed.update(
                    {
                        base + FIELD_OFFSETS["x"],
                        base + FIELD_OFFSETS["y"],
                    }
                )
        if completion_layout:
            allowed.update(
                range(
                    layout.record_list_offset,
                    layout.record_list_offset + 2,
                )
            )
            active = (
                layout.records_offset
                + probe_builder.COMPLETION_TARGET_RECORD_INDEX
                * FIXED_RECORD_SIZE
            )
            allowed.update(range(active, active + FIXED_RECORD_SIZE))
        if compact_layout:
            allowed.update(
                range(
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET,
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
                    + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4,
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

    def test_weakens_enemy_and_special_records_without_changing_ownership(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertIn(self.source[base + 0x08], (0x04, 0x08))
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

    def test_preserves_named_commanders_and_original_high_stats(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            probe_builder.VARGAS_RECORD_INDEX: (
                0x0F,
                0x49,
                75,
                54,
                0x04,
                (15, 55),
            ),
            probe_builder.LEON_RECORD_INDEX: (
                0x0D,
                0x4D,
                77,
                59,
                0x04,
                (15, 35),
            ),
            probe_builder.LAIRD_RECORD_INDEX: (
                0x11,
                0x43,
                65,
                45,
                0x04,
                (20, 36),
            ),
            probe_builder.EGBERT_RECORD_INDEX: (
                0x14,
                0x4F,
                68,
                54,
                0x04,
                (15, 25),
            ),
            probe_builder.BOZEL_RECORD_INDEX: (
                0x10,
                0x61,
                69,
                54,
                0x04,
                (15, 15),
            ),
            probe_builder.BERNHARDT_RECORD_INDEX: (
                0x0E,
                0x4E,
                87,
                61,
                0x08,
                (15, 4),
            ),
        }
        for index, values in expected.items():
            name_id, class_id, at, df, side_id, coordinates = values
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(self.source[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], class_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["at"]], at)
            self.assertEqual(self.source[base + FIELD_OFFSETS["df"]], df)
            self.assertEqual(self.source[base + 0x08], side_id)
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

    def test_compact_layout_changes_only_declared_coordinates_and_probe_fields(self):
        data = self.patched(compact_layout=True)
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(
            changed,
            self.allowed_offsets(compact_layout=True),
        )
        expected = probe_builder.deployment_bytes(
            probe_builder.COMPACT_PLAYER_DEPLOYMENTS
        )
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(data[start : start + len(expected)], expected)

        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index, (x, y) in probe_builder.COMPACT_COMBAT_POSITIONS.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                (data[base + FIELD_OFFSETS["x"]], data[base + FIELD_OFFSETS["y"]]),
                (x, y),
            )

    def test_compact_positions_are_unique_and_close_to_loaded_commanders(self):
        players = set(probe_builder.COMPACT_PLAYER_DEPLOYMENTS)
        enemies = set(probe_builder.COMPACT_COMBAT_POSITIONS.values())
        self.assertEqual(len(players), probe_builder.PLAYER_DEPLOYMENT_COUNT)
        self.assertEqual(len(enemies), probe_builder.LAST_COMBAT_RECORD_INDEX + 1)
        self.assertFalse(players & enemies)
        loaded_commanders = probe_builder.COMPACT_PLAYER_DEPLOYMENTS[:5]
        for enemy in enemies:
            self.assertTrue(
                any(
                    max(abs(enemy[0] - player[0]), abs(enemy[1] - player[1])) <= 1
                    for player in loaded_commanders
                )
            )

    def test_completion_layout_reduces_list_to_source_bernhardt_record(self):
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
        source_layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        probe_layout = scenario_layout(data, probe_builder.SCENARIO_NUMBER)
        self.assertEqual(probe_layout.record_count, probe_builder.COMPLETION_RECORD_COUNT)
        expected = probe_builder.deployment_bytes(
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS
        )
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(data[start : start + len(expected)], expected)
        source_record = (
            source_layout.records_offset
            + probe_builder.COMPLETION_SOURCE_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        active = (
            source_layout.records_offset
            + probe_builder.COMPLETION_TARGET_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        expected_record = bytearray(
            self.source[source_record : source_record + FIXED_RECORD_SIZE]
        )
        expected_record[FIELD_OFFSETS["at"]] = probe_builder.COMPLETION_AT
        expected_record[FIELD_OFFSETS["df"]] = probe_builder.COMPLETION_DF
        expected_record[
            FIELD_OFFSETS["mercenaries"] : FIELD_OFFSETS["mercenaries"] + 6
        ] = b"\xFF" * 6
        expected_record[FIELD_OFFSETS["x"]] = probe_builder.COMPLETION_ACTIVE_POSITION[0]
        expected_record[FIELD_OFFSETS["y"]] = probe_builder.COMPLETION_ACTIVE_POSITION[1]
        self.assertEqual(
            data[active : active + FIXED_RECORD_SIZE],
            expected_record,
        )
        self.assertEqual(data[active + 0x08], 8)
        self.assertEqual(data[active + FIELD_OFFSETS["name_id"]], 0x0E)
        self.assertEqual(data[active + FIELD_OFFSETS["class_id"]], 0x4E)
        self.assertFalse(bool(data[active] & 0x80))

    def test_rejects_non_source_fixed_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 0"):
            probe_builder.patch_probe(damaged, self.source)

    def test_checksum_is_current_and_valid(self):
        data = self.patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(expected, 0x20E7)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_optional_layout_checksums_are_current_and_valid(self):
        for data, expected in (
            (self.patched(compact_layout=True), 0x220F),
            (self.patched(completion_layout=True), 0x5F85),
        ):
            actual = sum(
                int.from_bytes(data[offset : offset + 2], "big")
                for offset in range(0x200, len(data), 2)
            ) & 0xFFFF
            self.assertEqual(actual, expected)
            self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)


if __name__ == "__main__":
    unittest.main()
