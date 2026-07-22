from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario4_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario4ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        return data

    def test_probe_only_changes_verified_fields_and_checksum(self):
        data = self.patched()
        base = probe_builder.MORGAN_RECORD_OFFSET
        expected_changes = {
            0x18E,
            0x18F,
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 3,
            base + FIELD_OFFSETS["at"],
            base + FIELD_OFFSETS["df"],
            *(
                base + FIELD_OFFSETS["mercenaries"] + slot
                for slot in range(6)
            ),
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_morgan_identity_and_coordinates(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = layout.records_offset + probe_builder.MORGAN_RECORD_INDEX * FIXED_RECORD_SIZE
        for field_offset in (
            0x00,
            FIELD_OFFSETS["level"],
            FIELD_OFFSETS["x"],
            FIELD_OFFSETS["y"],
            FIELD_OFFSETS["name_id"],
            FIELD_OFFSETS["class_id"],
        ):
            self.assertEqual(data[base + field_offset], self.source[base + field_offset])

    def test_probe_places_elwin_below_unguarded_morgan(self):
        data = self.patched()
        deployment = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(
            data[deployment : deployment + 4],
            bytes.fromhex("0007 0016"),
        )
        base = probe_builder.MORGAN_RECORD_OFFSET
        self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
        start = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[start : start + 6], b"\xFF" * 6)

    def test_probe_rejects_changed_morgan_record(self):
        data = bytearray(self.built)
        data[probe_builder.MORGAN_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Morgan record differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_rejects_changed_deployment(self):
        data = bytearray(self.built)
        data[probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 1] ^= 1
        with self.assertRaisesRegex(ValueError, "first player deployment"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_updates_megadrive_checksum(self):
        data = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)

    def test_progression_probe_only_changes_enemy_stats_mercenaries_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_progression_probe(data, self.source)
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
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_progression_probe_preserves_deployment_identity_and_coordinates(self):
        data = bytearray(self.built)
        probe_builder.patch_progression_probe(data, self.source)
        deployment = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(
            data[deployment : deployment + 4],
            probe_builder.SOURCE_FIRST_PLAYER_DEPLOYMENT,
        )
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            for field_offset in (
                0x00,
                FIELD_OFFSETS["level"],
                FIELD_OFFSETS["x"],
                FIELD_OFFSETS["y"],
                FIELD_OFFSETS["name_id"],
                FIELD_OFFSETS["class_id"],
            ):
                self.assertEqual(
                    data[base + field_offset], self.source[base + field_offset]
                )

    def test_progression_probe_weakens_all_six_enemy_records(self):
        data = bytearray(self.built)
        probe_builder.patch_progression_probe(data, self.source)
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

    def test_progression_probe_rejects_changed_enemy_record(self):
        data = bytearray(self.built)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = (
            layout.records_offset
            + probe_builder.FIRST_ENEMY_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        data[base] ^= 1
        with self.assertRaisesRegex(ValueError, "enemy record 5 differs"):
            probe_builder.patch_progression_probe(data, self.source)

    def test_masked_knight_status_probe_changes_only_visibility_coordinates_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_masked_knight_status_probe(data, self.source)
        base = probe_builder.MASKED_KNIGHT_RECORD_OFFSET
        expected_changes = {
            0x18E,
            0x18F,
            base,
            base + FIELD_OFFSETS["x"],
            base + FIELD_OFFSETS["y"],
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_masked_knight_status_probe_preserves_source_identity_class_and_stats(self):
        data = bytearray(self.built)
        probe_builder.patch_masked_knight_status_probe(data, self.source)
        base = probe_builder.MASKED_KNIGHT_RECORD_OFFSET
        self.assertEqual(data[base] & 0x80, 0)
        self.assertEqual(
            (
                data[base + FIELD_OFFSETS["x"]],
                data[base + FIELD_OFFSETS["y"]],
            ),
            (
                probe_builder.MASKED_KNIGHT_X,
                probe_builder.MASKED_KNIGHT_Y,
            ),
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["name_id"]],
            probe_builder.MASKED_KNIGHT_NAME_ID,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["class_id"]],
            probe_builder.MASKED_KNIGHT_CLASS_ID,
        )
        for field_offset in (
            FIELD_OFFSETS["level"],
            FIELD_OFFSETS["at"],
            FIELD_OFFSETS["df"],
        ):
            self.assertEqual(
                data[base + field_offset], self.source[base + field_offset]
            )
        mercenary = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(
            data[mercenary : mercenary + 6],
            self.source[mercenary : mercenary + 6],
        )

    def test_masked_knight_status_probe_rejects_changed_source_record(self):
        data = bytearray(self.built)
        data[probe_builder.MASKED_KNIGHT_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "masked-knight record differs"):
            probe_builder.patch_masked_knight_status_probe(data, self.source)


if __name__ == "__main__":
    unittest.main()
