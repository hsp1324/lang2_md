from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario27_ending_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS


ROOT = Path(__file__).resolve().parents[1]


class Scenario27EndingProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        return data

    def test_probe_only_changes_verified_bernhardt_fields_and_checksum(self):
        data = self.patched()
        base = probe_builder.BERNHARDT_RECORD_OFFSET
        expected_changes = {
            base + FIELD_OFFSETS["at"],
            base + FIELD_OFFSETS["df"],
            base + FIELD_OFFSETS["y"],
            *(base + FIELD_OFFSETS["mercenaries"] + index for index in range(6)),
            0x18E,
            0x18F,
            *(
                probe_builder.START_MENU_ENTRY_OPERAND + index
                for index, (before, after) in enumerate(
                    zip(
                        probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
                        probe_builder.RUNTIME_WRAPPER.to_bytes(4, "big"),
                        strict=True,
                    )
                )
                if before != after
            ),
            *(
                probe_builder.RUNTIME_WRAPPER + index
                for index, value in enumerate(
                    probe_builder.completion_hp_wrapper_code()
                )
                if value != 0xFF
            ),
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertEqual(changed, expected_changes)
        self.assertEqual(
            data[base + FIELD_OFFSETS["at"]],
            probe_builder.PROBE_BERNHARDT_AT_MODIFIER & 0xFF,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["df"]],
            probe_builder.PROBE_BERNHARDT_DF_MODIFIER & 0xFF,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["x"]], probe_builder.PROBE_BERNHARDT_X
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["y"]], probe_builder.PROBE_BERNHARDT_Y
        )
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)

    def test_start_wrapper_sets_only_runtime_bernhardt_hp_then_runs_stock_start(self):
        target_hp = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.BERNHARDT_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
            + probe_builder.RUNTIME_HP_OFFSET
        )
        self.assertEqual(probe_builder.BERNHARDT_RUNTIME_GROUP, 18)
        self.assertEqual(target_hp, 0xFFFF66FF)
        self.assertEqual(
            probe_builder.BERNHARDT_RUNTIME_HP_ADDRESS,
            target_hp,
        )
        self.assertEqual(
            probe_builder.completion_hp_wrapper_code(),
            bytes.fromhex(
                "13 FC 00 01 FF FF 66 FF "
                "41 F9 00 02 2C 1E "
                "4E F9 00 02 2C 1E"
            ),
        )

        data = self.patched()
        self.assertEqual(
            data[
                probe_builder.START_MENU_ENTRY_OPERAND :
                probe_builder.START_MENU_ENTRY_OPERAND + 4
            ],
            probe_builder.RUNTIME_WRAPPER.to_bytes(4, "big"),
        )
        wrapper = probe_builder.completion_hp_wrapper_code()
        self.assertEqual(
            data[
                probe_builder.RUNTIME_WRAPPER :
                probe_builder.RUNTIME_WRAPPER + len(wrapper)
            ],
            wrapper,
        )

    def test_start_wrapper_rejects_changed_operand_or_occupied_reservation(self):
        changed_operand = bytearray(self.built)
        changed_operand[probe_builder.START_MENU_ENTRY_OPERAND + 3] ^= 1
        with self.assertRaisesRegex(ValueError, "input Start-menu entry operand"):
            probe_builder.patch_probe(changed_operand, self.source)

        occupied = bytearray(self.built)
        occupied[probe_builder.RUNTIME_WRAPPER] = 0
        with self.assertRaisesRegex(ValueError, "wrapper region is not empty"):
            probe_builder.patch_probe(occupied, self.source)

    def test_probe_rejects_changed_scenario_layout(self):
        data = bytearray(self.built)
        data[probe_builder.BERNHARDT_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Bernhardt record differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_rejects_noncanonical_japanese_source_before_patching(self):
        changed = bytearray(self.source)
        changed[0x100] ^= 1
        with self.assertRaisesRegex(ValueError, "source ROM SHA-256 changed"):
            probe_builder.patch_probe(bytearray(self.built), bytes(changed))

    def test_probe_rejects_corruption_in_every_other_final_enemy_record(self):
        layout = probe_builder.scenario_layout(
            self.source,
            probe_builder.SCENARIO_NUMBER,
        )
        for index in range(layout.record_count):
            if index == probe_builder.BERNHARDT_RECORD_INDEX:
                continue
            with self.subTest(record=index):
                data = bytearray(self.built)
                base = layout.records_offset + index * probe_builder.FIXED_RECORD_SIZE
                data[base + FIELD_OFFSETS["name_id"]] ^= 1
                with self.assertRaisesRegex(
                    ValueError,
                    rf"fixed record {index} differs",
                ):
                    probe_builder.patch_probe(data, self.source)

    def test_balanced_input_allows_only_fields_overwritten_by_probe(self):
        data = bytearray(self.built)
        base = probe_builder.BERNHARDT_RECORD_OFFSET
        data[base + FIELD_OFFSETS["at"]] ^= 0x11
        data[base + FIELD_OFFSETS["df"]] ^= 0x22
        data[base + probe_builder.BALANCE_RECORD_TAG_OFFSET] = 0x42
        data[base + FIELD_OFFSETS["mercenaries"]] = 0x42
        probe_builder.patch_probe(
            data,
            self.source,
            allow_balanced_input=True,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["at"]],
            probe_builder.PROBE_BERNHARDT_AT_MODIFIER & 0xFF,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["df"]],
            probe_builder.PROBE_BERNHARDT_DF_MODIFIER & 0xFF,
        )
        self.assertEqual(
            data[
                base + FIELD_OFFSETS["mercenaries"]:
                base + FIELD_OFFSETS["mercenaries"] + 6
            ],
            b"\xFF" * 6,
        )
        self.assertEqual(
            data[base + probe_builder.BALANCE_RECORD_TAG_OFFSET],
            0x42,
        )

    def test_balanced_input_still_rejects_identity_or_position_changes(self):
        for offset in (
            0,
            FIELD_OFFSETS["name_id"],
            FIELD_OFFSETS["class_id"],
            FIELD_OFFSETS["level"],
            FIELD_OFFSETS["x"],
            FIELD_OFFSETS["y"],
        ):
            data = bytearray(self.built)
            data[probe_builder.BERNHARDT_RECORD_OFFSET + offset] ^= 1
            with self.assertRaisesRegex(ValueError, "protected fields"):
                probe_builder.patch_probe(
                    data,
                    self.source,
                    allow_balanced_input=True,
                )

    def test_balanced_input_checks_protected_fields_on_non_target_records(self):
        layout = probe_builder.scenario_layout(
            self.source,
            probe_builder.SCENARIO_NUMBER,
        )
        other = layout.records_offset
        allowed = bytearray(self.built)
        allowed[other + FIELD_OFFSETS["at"]] ^= 1
        allowed[other + FIELD_OFFSETS["df"]] ^= 1
        allowed[other + probe_builder.BALANCE_RECORD_TAG_OFFSET] ^= 1
        allowed[other + FIELD_OFFSETS["mercenaries"]] ^= 1
        probe_builder.patch_probe(
            allowed,
            self.source,
            allow_balanced_input=True,
        )

        changed_name = bytearray(self.built)
        changed_name[other + FIELD_OFFSETS["name_id"]] ^= 1
        with self.assertRaisesRegex(
            ValueError,
            "fixed record 0 protected fields",
        ):
            probe_builder.patch_probe(
                changed_name,
                self.source,
                allow_balanced_input=True,
            )

    def test_probe_updates_megadrive_checksum(self):
        data = self.patched()
        expected = sum(
            builder.be16(data, offset) for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(builder.be16(data, 0x18E), expected)


if __name__ == "__main__":
    unittest.main()
