import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario3_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario3ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def patched(
        self,
        *,
        liana_death: bool = False,
        liana_death_zorum_defeated: bool = False,
        protagonist_death: bool = False,
    ) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            liana_death=liana_death,
            liana_death_zorum_defeated=liana_death_zorum_defeated,
            protagonist_death=protagonist_death,
        )
        return data

    def test_probe_only_changes_verified_enemy_fields_and_checksum(self):
        data = self.patched()
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
                    base + FIELD_OFFSETS["x"],
                    base + FIELD_OFFSETS["y"],
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

    def test_probe_preserves_flags_names_classes_and_levels(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        preserved_offsets = (0x00, FIELD_OFFSETS["level"], FIELD_OFFSETS["name_id"], FIELD_OFFSETS["class_id"])
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            for field_offset in preserved_offsets:
                self.assertEqual(data[base + field_offset], self.source[base + field_offset])

    def test_probe_sets_expected_stats_coordinates_and_empty_mercenaries(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index, (x, y) in enumerate(
            probe_builder.PROBE_COORDINATES,
            start=probe_builder.FIRST_ENEMY_RECORD_INDEX,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], probe_builder.PROBE_AT)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], probe_builder.PROBE_DF)
            self.assertEqual(data[base + FIELD_OFFSETS["x"]], x)
            self.assertEqual(data[base + FIELD_OFFSETS["y"]], y)
            start = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[start : start + 6], b"\xFF" * 6)

    def test_probe_rejects_changed_enemy_record(self):
        data = bytearray(self.built)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        data[layout.records_offset + 2 * FIXED_RECORD_SIZE] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 2 differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_updates_megadrive_checksum(self):
        data = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)

    def test_source_owned_result_events_are_locked(self):
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
            ):
                self.assertEqual(data[offset : offset + len(expected)], expected)
        self.assertEqual(
            int.from_bytes(
                probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES[4:8],
                "big",
            ),
            probe_builder.PROTAGONIST_DEATH_TEXT,
        )
        for text in probe_builder.LIANA_DEATH_DIRECT_TEXTS:
            self.assertIn(
                text.to_bytes(3, "big"),
                probe_builder.LIANA_DEATH_HANDLER_BYTES,
            )

    def test_liana_death_continuation_pages_are_locked_and_translated(self):
        translations = json.loads(
            (ROOT / "localization/event_dialogue_ko.json").read_text(
                encoding="utf-8"
            )
        )
        scenario_addresses = {
            int(row["address"], 0)
            for row in translations["scenarios"]["3"]
        }
        self.assertLessEqual(
            set(probe_builder.LIANA_DEATH_PHYSICAL_TEXTS),
            scenario_addresses,
        )
        for address in probe_builder.LIANA_DEATH_PHYSICAL_TEXTS:
            builder.event_page_layout(self.source, address)
        for address, continuation in (
            probe_builder.LIANA_DEATH_CONTINUATIONS.items()
        ):
            capacity, terminator, _controls = builder.event_page_layout(
                self.source,
                address,
            )
            self.assertEqual(terminator, 0xFFFD)
            self.assertEqual(address + capacity * 2 + 2, continuation)

    def test_diagnostic_modes_preserve_all_records_and_deployments(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        record_start = layout.records_offset
        record_end = record_start + layout.record_count * FIXED_RECORD_SIZE
        deployment_start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        deployment_end = deployment_start + probe_builder.PLAYER_DEPLOYMENT_COUNT * 4
        for mode in (
            {"protagonist_death": True},
            {"liana_death": True},
            {"liana_death_zorum_defeated": True},
        ):
            data = self.patched(**mode)
            self.assertEqual(
                data[record_start:record_end],
                self.source[record_start:record_end],
            )
            self.assertEqual(
                data[deployment_start:deployment_end],
                self.source[deployment_start:deployment_end],
            )

    def test_death_wrappers_target_only_declared_runtime_groups(self):
        modes = (
            (
                (probe_builder.PROTAGONIST_RUNTIME_GROUP,),
                {
                    probe_builder.PROTAGONIST_RUNTIME_GROUP,
                },
            ),
            (
                (probe_builder.LIANA_RUNTIME_GROUP,),
                {
                    probe_builder.LIANA_RUNTIME_GROUP,
                },
            ),
            (
                (
                    probe_builder.LIANA_RUNTIME_GROUP,
                    probe_builder.ZORUM_RUNTIME_GROUP,
                ),
                {
                    probe_builder.LIANA_RUNTIME_GROUP,
                    probe_builder.ZORUM_RUNTIME_GROUP,
                },
            ),
        )
        for groups, expected_groups in modes:
            code = probe_builder.runtime_death_wrapper_code(groups)
            for group in range(13):
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
                {"liana_death_zorum_defeated": True},
                (
                    probe_builder.LIANA_RUNTIME_GROUP,
                    probe_builder.ZORUM_RUNTIME_GROUP,
                ),
            ),
        )
        for mode, groups in modes:
            data = self.patched(**mode)
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

    def test_diagnostic_modes_are_mutually_exclusive(self):
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            probe_builder.patch_probe(
                bytearray(self.built),
                self.source,
                liana_death=True,
                protagonist_death=True,
            )


if __name__ == "__main__":
    unittest.main()
