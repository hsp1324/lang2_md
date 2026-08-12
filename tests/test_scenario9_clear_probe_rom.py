from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario9_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario9ClearProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def diagnostic_patched(self, mode: str) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            npc_annihilation=mode == "npc",
            protagonist_death=mode == "protagonist",
            turn_event=mode == "turn",
            runtime_clear=mode == "clear",
        )
        return data

    def test_probe_only_changes_laird_setup_wrapper_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.LAIRD_RECORD_OFFSET
        wrapper = probe_builder.completion_wrapper_code()
        expected_changes = {
            0x18E,
            0x18F,
            base + FIELD_OFFSETS["at"],
            base + FIELD_OFFSETS["df"],
            base + FIELD_OFFSETS["x"],
            base + FIELD_OFFSETS["y"],
            *(base + FIELD_OFFSETS["mercenaries"] + slot for slot in range(6)),
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
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_completion_wrapper_sets_only_runtime_laird_hp_to_one(self):
        code = probe_builder.completion_wrapper_code()
        laird = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.LAIRD_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 01")
            + (laird + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        for group in range(20):
            if group == probe_builder.LAIRD_RUNTIME_GROUP:
                continue
            other_hp = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
                + probe_builder.RUNTIME_HP_OFFSET
            )
            self.assertNotIn(other_hp.to_bytes(4, "big"), code)
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_probe_preserves_every_other_fixed_record(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            if index == probe_builder.LAIRD_RECORD_INDEX:
                continue
            start = layout.records_offset + index * FIXED_RECORD_SIZE
            end = start + FIXED_RECORD_SIZE
            self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_weakens_and_moves_laird_only(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        base = probe_builder.LAIRD_RECORD_OFFSET
        self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
        self.assertEqual(data[base + FIELD_OFFSETS["x"]], 8)
        self.assertEqual(data[base + FIELD_OFFSETS["y"]], 27)
        self.assertEqual(
            data[base + FIELD_OFFSETS["name_id"]],
            probe_builder.SOURCE_LAIRD_NAME_ID,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["class_id"]],
            probe_builder.SOURCE_LAIRD_CLASS_ID,
        )
        mercenary_offset = base + FIELD_OFFSETS["mercenaries"]
        self.assertEqual(data[mercenary_offset : mercenary_offset + 6], b"\xFF" * 6)

    def test_hein_completion_moves_only_the_same_laird_setup(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            hein_completion=True,
        )
        base = probe_builder.LAIRD_RECORD_OFFSET
        self.assertEqual(
            data[base + FIELD_OFFSETS["x"]],
            probe_builder.HEIN_PROBE_LAIRD_X,
        )
        self.assertEqual(
            data[base + FIELD_OFFSETS["y"]],
            probe_builder.HEIN_PROBE_LAIRD_Y,
        )
        self.assertEqual(
            data[
                probe_builder.START_MENU_ENTRY_OPERAND :
                probe_builder.START_MENU_ENTRY_OPERAND + 4
            ],
            probe_builder.RUNTIME_WRAPPER.to_bytes(4, "big"),
        )

    def test_probe_rejects_changed_laird_record(self):
        data = bytearray(self.built)
        data[probe_builder.LAIRD_RECORD_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Laird record differs"):
            probe_builder.patch_probe(data, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_diagnostic_modes_change_only_wrapper_and_checksum(self):
        for mode, wrapper in (
            ("npc", probe_builder.npc_annihilation_wrapper_code()),
            ("protagonist", probe_builder.protagonist_death_wrapper_code()),
            ("turn", probe_builder.turn_event_wrapper_code()),
            ("clear", probe_builder.runtime_clear_wrapper_code()),
        ):
            with self.subTest(mode=mode):
                data = self.diagnostic_patched(mode)
                expected_changes = {
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
                    index
                    for index, (before, after) in enumerate(zip(self.built, data))
                    if before != after
                }
                self.assertLessEqual(changed, expected_changes)

    def test_diagnostic_modes_preserve_all_scenario_fixed_records(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for mode in ("npc", "protagonist", "turn", "clear"):
            data = self.diagnostic_patched(mode)
            for index in range(layout.record_count):
                start = layout.records_offset + index * FIXED_RECORD_SIZE
                end = start + FIXED_RECORD_SIZE
                self.assertEqual(data[start:end], self.source[start:end])

    def test_npc_annihilation_marks_only_runtime_groups_seven_to_nine(self):
        code = probe_builder.npc_annihilation_wrapper_code()
        for group in (7, 8, 9):
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertIn(
                bytes.fromhex("00 39 00 80")
                + (
                    record + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
                ).to_bytes(4, "big"),
                code,
            )
            self.assertIn(
                bytes.fromhex("13 FC 00 00")
                + (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
                code,
            )
            self.assertIn(
                bytes.fromhex("13 FC 00 FF")
                + (record + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
                code,
            )
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_protagonist_death_marks_only_runtime_group_zero(self):
        code = probe_builder.protagonist_death_wrapper_code()
        protagonist = probe_builder.RUNTIME_GROUP_BASE
        self.assertIn(
            bytes.fromhex("00 39 00 80")
            + (
                protagonist + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertNotIn(
            (
                probe_builder.RUNTIME_GROUP_BASE
                + 7 * probe_builder.RUNTIME_GROUP_SIZE
                + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )

    def test_runtime_clear_marks_only_runtime_laird_group_ten(self):
        code = probe_builder.runtime_clear_wrapper_code()
        laird = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.LAIRD_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("00 39 00 80")
            + (
                laird + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 00")
            + (laird + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertNotIn(
            (
                probe_builder.RUNTIME_GROUP_BASE
                + probe_builder.PROTAGONIST_RUNTIME_GROUP
                * probe_builder.RUNTIME_GROUP_SIZE
                + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET
            ).to_bytes(4, "big"),
            code,
        )

    def test_turn_event_mode_protects_only_player_and_npc_groups(self):
        code = probe_builder.turn_event_wrapper_code()
        for group in probe_builder.TURN_EVENT_PROTECTED_RUNTIME_GROUPS:
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertIn(
                bytes.fromhex("13 FC")
                + probe_builder.TURN_EVENT_PROTECTED_DF.to_bytes(2, "big")
                + (record + probe_builder.RUNTIME_DF_OFFSET).to_bytes(4, "big"),
                code,
            )
        first_enemy = (
            probe_builder.RUNTIME_GROUP_BASE
            + 10 * probe_builder.RUNTIME_GROUP_SIZE
            + probe_builder.RUNTIME_DF_OFFSET
        )
        self.assertNotIn(first_enemy.to_bytes(4, "big"), code)
        self.assertIn(
            bytes.fromhex("13 FC 00 01")
            + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
            code,
        )
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_source_locks_player_order_event_table_and_handlers(self):
        self.assertEqual(
            self.source[
                probe_builder.PLAYER_NAME_TABLE :
                probe_builder.PLAYER_NAME_TABLE
                + len(probe_builder.SOURCE_PLAYER_NAME_TABLE)
            ],
            probe_builder.SOURCE_PLAYER_NAME_TABLE,
        )
        self.assertEqual(
            self.source[
                probe_builder.SCENARIO_EVENT_POINTER_TABLE :
                probe_builder.SCENARIO_EVENT_POINTER_TABLE
                + len(probe_builder.SCENARIO_EVENT_POINTER_TABLE_BYTES)
            ],
            probe_builder.SCENARIO_EVENT_POINTER_TABLE_BYTES,
        )
        self.assertEqual(
            self.source[
                probe_builder.TURN_EVENT_TABLE :
                probe_builder.TURN_EVENT_TABLE
                + len(probe_builder.TURN_EVENT_TABLE_BYTES)
            ],
            probe_builder.TURN_EVENT_TABLE_BYTES,
        )
        for address in probe_builder.TURN_EVENT_TEXTS:
            self.assertTrue(
                any(
                    address.to_bytes(4, "big") in self.source[start:end]
                    for start, end in
                    probe_builder.TURN_EVENT_HANDLER_RANGES.values()
                ),
                f"missing turn-event text pointer 0x{address:06X}",
            )

    def test_probe_rejects_changed_turn_event_source_surfaces(self):
        for label, offset, message in (
            ("player names", probe_builder.PLAYER_NAME_TABLE + 2, "name table"),
            (
                "event pointers",
                probe_builder.SCENARIO_EVENT_POINTER_TABLE,
                "event pointer table",
            ),
            (
                "turn table",
                probe_builder.TURN_EVENT_TABLE,
                "scheduled turn table",
            ),
            (
                "turn handler",
                probe_builder.TURN_EVENT_HANDLER_RANGES["turn-2-entry"][0],
                "turn handler turn-2-entry",
            ),
        ):
            with self.subTest(label=label):
                source = bytearray(self.source)
                source[offset] ^= 1
                with self.assertRaisesRegex(ValueError, message):
                    probe_builder.patch_probe(
                        bytearray(self.built),
                        bytes(source),
                        turn_event=True,
                    )

    def test_diagnostic_modes_conflict(self):
        data = bytearray(self.built)
        with self.assertRaisesRegex(ValueError, "modes conflict"):
            probe_builder.patch_probe(
                data,
                self.source,
                npc_annihilation=True,
                turn_event=True,
            )

    def test_diagnostic_checksums_are_valid(self):
        for mode, checksum in (
            ("npc", 0xC643),
            ("protagonist", 0x1653),
            ("turn", 0x3D5D),
        ):
            with self.subTest(mode=mode):
                data = self.diagnostic_patched(mode)
                expected = sum(
                    int.from_bytes(data[offset : offset + 2], "big")
                    for offset in range(0x200, len(data), 2)
                ) & 0xFFFF
                self.assertEqual(
                    int.from_bytes(data[0x18E:0x190], "big"),
                    expected,
                )
                self.assertEqual(expected, checksum)


if __name__ == "__main__":
    unittest.main()
