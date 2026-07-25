import json
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

    def death_patched(
        self,
        *,
        liana_death: bool = False,
        priest_annihilation: bool = False,
        protagonist_death: bool = False,
    ) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_death_probe(
            data,
            self.source,
            liana_death=liana_death,
            priest_annihilation=priest_annihilation,
            protagonist_death=protagonist_death,
        )
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

    def test_source_owned_defeat_events_are_locked(self):
        for data in (self.source, self.built):
            for offset, expected in (
                (
                    probe_builder.PROTAGONIST_DEATH_TRIGGER,
                    probe_builder.PROTAGONIST_DEATH_TRIGGER_BYTES,
                ),
                (
                    probe_builder.PROTAGONIST_DEATH_HANDLER,
                    probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES,
                ),
                (
                    probe_builder.LIANA_DEATH_TRIGGER,
                    probe_builder.LIANA_DEATH_TRIGGER_BYTES,
                ),
                (
                    probe_builder.LIANA_DEATH_HANDLER,
                    probe_builder.LIANA_DEATH_HANDLER_BYTES,
                ),
                (
                    probe_builder.PRIEST_ANNIHILATION_TRIGGER,
                    probe_builder.PRIEST_ANNIHILATION_TRIGGER_BYTES,
                ),
                (
                    probe_builder.PRIEST_ANNIHILATION_HANDLER,
                    probe_builder.PRIEST_ANNIHILATION_HANDLER_BYTES,
                ),
            ):
                self.assertEqual(data[offset : offset + len(expected)], expected)
        self.assertIn(
            probe_builder.PROTAGONIST_DEATH_TEXT.to_bytes(3, "big"),
            probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES,
        )
        for address in probe_builder.LIANA_DEATH_TEXTS:
            self.assertIn(
                address.to_bytes(3, "big"),
                probe_builder.LIANA_DEATH_HANDLER_BYTES,
            )
        for address in probe_builder.PRIEST_ANNIHILATION_DIRECT_TEXTS:
            self.assertIn(
                address.to_bytes(3, "big"),
                probe_builder.PRIEST_ANNIHILATION_HANDLER_BYTES,
            )

    def test_priest_annihilation_continuation_pages_are_translated(self):
        translations = json.loads(
            (ROOT / "localization/event_dialogue_ko.json").read_text(
                encoding="utf-8"
            )
        )
        scenario_addresses = {
            int(row["address"], 0)
            for row in translations["scenarios"]["4"]
        }
        self.assertLessEqual(
            set(probe_builder.PRIEST_ANNIHILATION_PHYSICAL_TEXTS),
            scenario_addresses,
        )
        for address in probe_builder.PRIEST_ANNIHILATION_PHYSICAL_TEXTS:
            builder.event_page_layout(self.source, address)
        for address, continuation in (
            probe_builder.PRIEST_ANNIHILATION_CONTINUATIONS.items()
        ):
            capacity, terminator, _controls = builder.event_page_layout(
                self.source,
                address,
            )
            self.assertEqual(terminator, 0xFFFD)
            self.assertEqual(address + capacity * 2 + 2, continuation)

    def test_death_modes_preserve_all_records_and_deployments(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        record_start = layout.records_offset
        record_end = record_start + layout.record_count * FIXED_RECORD_SIZE
        deployment_start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        deployment_end = (
            deployment_start + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4
        )
        for mode in (
            {"protagonist_death": True},
            {"liana_death": True},
            {"priest_annihilation": True},
        ):
            data = self.death_patched(**mode)
            self.assertEqual(
                data[record_start:record_end],
                self.source[record_start:record_end],
            )
            self.assertEqual(
                data[deployment_start:deployment_end],
                self.source[deployment_start:deployment_end],
            )

    def test_declared_runtime_groups_match_source_identities(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        liana_record = (
            probe_builder.LIANA_RUNTIME_GROUP
            - probe_builder.PLAYER_DEPLOYMENT_COUNT
        )
        liana_base = (
            layout.records_offset + liana_record * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            self.source[liana_base + FIELD_OFFSETS["name_id"]],
            0x02,
        )
        priest_ids = []
        for group in probe_builder.PRIEST_RUNTIME_GROUPS:
            fixed_record = group - probe_builder.PLAYER_DEPLOYMENT_COUNT
            base = layout.records_offset + fixed_record * FIXED_RECORD_SIZE
            priest_ids.append(
                self.source[base + FIELD_OFFSETS["name_id"]]
            )
        self.assertEqual(priest_ids, [0x70, 0x71, 0x1F])

    def test_death_wrappers_target_only_declared_runtime_groups(self):
        modes = (
            (
                (probe_builder.PROTAGONIST_RUNTIME_GROUP,),
                {probe_builder.PROTAGONIST_RUNTIME_GROUP},
            ),
            (
                (probe_builder.LIANA_RUNTIME_GROUP,),
                {probe_builder.LIANA_RUNTIME_GROUP},
            ),
            (
                probe_builder.PRIEST_RUNTIME_GROUPS,
                set(probe_builder.PRIEST_RUNTIME_GROUPS),
            ),
        )
        for groups, expected_groups in modes:
            code = probe_builder.runtime_death_wrapper_code(groups)
            for group in range(14):
                target = (
                    probe_builder.RUNTIME_GROUP_BASE
                    + group * probe_builder.RUNTIME_GROUP_SIZE
                )
                hp_address = (
                    target + probe_builder.RUNTIME_HP_OFFSET
                ).to_bytes(4, "big")
                if group in expected_groups:
                    self.assertIn(hp_address, code)
                else:
                    self.assertNotIn(hp_address, code)
            self.assertEqual(
                code[-6:],
                bytes.fromhex("4E F9")
                + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
            )

    def test_death_modes_change_only_wrapper_operand_and_checksum(self):
        modes = (
            (
                {"protagonist_death": True},
                (probe_builder.PROTAGONIST_RUNTIME_GROUP,),
            ),
            (
                {"liana_death": True},
                (probe_builder.LIANA_RUNTIME_GROUP,),
            ),
            (
                {"priest_annihilation": True},
                probe_builder.PRIEST_RUNTIME_GROUPS,
            ),
        )
        for mode, groups in modes:
            data = self.death_patched(**mode)
            wrapper = probe_builder.runtime_death_wrapper_code(groups)
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
                for offset, (before, after) in enumerate(zip(self.built, data))
                if before != after
            }
            self.assertLessEqual(changed, allowed)

    def test_death_modes_require_exactly_one_selection(self):
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            probe_builder.patch_death_probe(
                bytearray(self.built),
                self.source,
            )
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            probe_builder.patch_death_probe(
                bytearray(self.built),
                self.source,
                liana_death=True,
                protagonist_death=True,
            )


if __name__ == "__main__":
    unittest.main()
