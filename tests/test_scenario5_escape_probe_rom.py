import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools import build_scenario5_escape_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


ROOT = Path(__file__).resolve().parents[1]


class Scenario5EscapeProbeRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / builder.IN_ROM).read_bytes()
        cls.built = (ROOT / builder.OUT_ROM).read_bytes()

    def annihilation_patched(self) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            enemy_annihilation=True,
        )
        return data

    def result_patched(
        self,
        *,
        protagonist_death: bool = False,
        timeout: bool = False,
        timeout_alternate: bool = False,
        turn_event: int | None = None,
        turn_event_alternate: bool = False,
    ) -> bytearray:
        data = bytearray(self.built)
        probe_builder.patch_probe(
            data,
            self.source,
            protagonist_death=protagonist_death,
            timeout=timeout,
            timeout_alternate=timeout_alternate,
            turn_event=turn_event,
            turn_event_alternate=turn_event_alternate,
        )
        return data

    def annihilation_allowed_offsets(self) -> set[int]:
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {0x18E, 0x18F}
        allowed.update(
            range(
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET,
                probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
                + len(
                    probe_builder.deployment_bytes(
                        probe_builder.SOURCE_PLAYER_DEPLOYMENTS
                    )
                ),
            )
        )
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
        wrapper = probe_builder.annihilation_wrapper_code()
        allowed.update(
            range(
                probe_builder.START_MENU_ENTRY_OPERAND,
                probe_builder.START_MENU_ENTRY_OPERAND + 4,
            )
        )
        allowed.update(
            range(
                probe_builder.ANNIHILATION_WRAPPER,
                probe_builder.ANNIHILATION_WRAPPER + len(wrapper),
            )
        )
        return allowed

    def test_probe_only_changes_first_deployment_y_and_checksum(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        expected_changes = {
            0x18E,
            0x18F,
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 2,
            probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 3,
        }
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)

    def test_probe_preserves_scenario_layout_and_all_fixed_records(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        source_layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        probe_layout = scenario_layout(data, probe_builder.SCENARIO_NUMBER)
        self.assertEqual(probe_layout, source_layout)
        start = source_layout.records_offset
        end = start + source_layout.record_count * FIXED_RECORD_SIZE
        self.assertEqual(data[start:end], self.source[start:end])

    def test_probe_moves_only_elwin_to_north_threshold(self):
        data = bytearray(self.built)
        probe_builder.patch_probe(data, self.source)
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        self.assertEqual(
            data[start : start + 4],
            bytes.fromhex(
                f"{probe_builder.SOURCE_FIRST_PLAYER_X:04X} "
                f"{probe_builder.PROBE_FIRST_PLAYER_Y:04X}"
            ),
        )

    def test_annihilation_changes_only_declared_diagnostic_fields(self):
        data = self.annihilation_patched()
        changed = {
            index
            for index, (before, after) in enumerate(zip(self.built, data))
            if before != after
        }
        self.assertLessEqual(changed, self.annihilation_allowed_offsets())

    def test_annihilation_preserves_fixed_identity_and_coordinates(self):
        data = self.annihilation_patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(layout.record_count):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base] & 0x80, self.source[base] & 0x80)
            self.assertEqual(data[base + 0x08], self.source[base + 0x08])
            for field in (
                "level",
                "name_id",
                "class_id",
                "x",
                "y",
            ):
                offset = FIELD_OFFSETS[field]
                self.assertEqual(data[base + offset], self.source[base + offset])
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)

    def test_annihilation_moves_only_first_player_below_source_target(self):
        data = self.annihilation_patched()
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        expected = probe_builder.deployment_bytes(
            probe_builder.ANNIHILATION_PLAYER_DEPLOYMENTS
        )
        self.assertEqual(data[start : start + len(expected)], expected)
        self.assertEqual(
            probe_builder.ANNIHILATION_PLAYER_DEPLOYMENTS[1:],
            probe_builder.SOURCE_PLAYER_DEPLOYMENTS[1:],
        )

    def test_annihilation_wrapper_isolates_one_living_enemy(self):
        code = probe_builder.annihilation_wrapper_code()
        target = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.ANNIHILATION_TARGET_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 01")
            + (target + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        for group in probe_builder.ANNIHILATION_HIDDEN_RUNTIME_GROUPS:
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertIn(
                bytes.fromhex("13 FC 00 FF")
                + (record + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
                code,
            )
            self.assertIn(
                bytes.fromhex("13 FC 00 00")
                + (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
                code,
            )
        self.assertTrue(code.endswith(bytes.fromhex("4E F9 00 02 2C 1E")))

    def test_probe_rejects_changed_deployment_or_fixed_record(self):
        changed_deployment = bytearray(self.built)
        changed_deployment[probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "player deployments differ"):
            probe_builder.patch_probe(changed_deployment, self.source)

        changed_record = bytearray(self.built)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        changed_record[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed records differ"):
            probe_builder.patch_probe(changed_record, self.source)

    def test_probe_checksum_is_valid(self):
        data = bytearray(self.built)
        checksum = probe_builder.patch_probe(data, self.source)
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(checksum, expected)
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

    def test_annihilation_checksum_is_valid(self):
        data = self.annihilation_patched()
        expected = sum(
            int.from_bytes(data[offset : offset + 2], "big")
            for offset in range(0x200, len(data), 2)
        ) & 0xFFFF
        self.assertEqual(int.from_bytes(data[0x18E:0x190], "big"), expected)

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
                    probe_builder.TIMEOUT_TRIGGER,
                    probe_builder.TIMEOUT_TRIGGER_BYTES,
                ),
                (
                    probe_builder.TIMEOUT_HANDLER,
                    probe_builder.TIMEOUT_HANDLER_BYTES,
                ),
            ):
                self.assertEqual(data[offset : offset + len(expected)], expected)
        for address in probe_builder.PROTAGONIST_DEATH_TEXTS:
            self.assertIn(
                address.to_bytes(3, "big"),
                probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES,
            )
        for address in probe_builder.TIMEOUT_TEXTS:
            self.assertIn(
                address.to_bytes(3, "big"),
                probe_builder.TIMEOUT_HANDLER_BYTES,
            )
        table_end = (
            probe_builder.TURN_EVENT_TABLE
            + len(probe_builder.TURN_EVENT_TABLE_BYTES)
        )
        for data in (self.source, self.built):
            self.assertEqual(
                data[probe_builder.TURN_EVENT_TABLE:table_end],
                probe_builder.TURN_EVENT_TABLE_BYTES,
            )
            for turn, offset in probe_builder.TURN_EVENT_HANDLERS.items():
                expected = probe_builder.TURN_EVENT_HANDLER_BYTES[turn]
                self.assertEqual(data[offset : offset + len(expected)], expected)

    def test_result_text_pages_are_reviewed_and_structurally_valid(self):
        translations = json.loads(
            (ROOT / "localization/event_dialogue_ko.json").read_text(
                encoding="utf-8"
            )
        )
        scenario_addresses = {
            int(row["address"], 0)
            for row in translations["scenarios"]["5"]
        }
        expected = {
            *probe_builder.PROTAGONIST_DEATH_PHYSICAL_TEXTS,
            *probe_builder.TIMEOUT_TEXTS,
            *(
                address
                for texts in probe_builder.TURN_EVENT_TEXTS.values()
                for address in texts
            ),
        }
        self.assertLessEqual(expected, scenario_addresses)
        for address in expected:
            capacity, terminator, _controls = builder.event_page_layout(
                self.source,
                address,
            )
            continuation = probe_builder.PROTAGONIST_DEATH_CONTINUATIONS.get(
                address
            )
            if continuation is None:
                self.assertEqual(terminator, 0xFFFF)
            else:
                self.assertEqual(terminator, 0xFFFD)
                self.assertEqual(address + capacity * 2 + 2, continuation)

    def test_result_modes_preserve_all_deployments_and_records(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        record_start = layout.records_offset
        record_end = record_start + layout.record_count * FIXED_RECORD_SIZE
        deployment_start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        deployment_end = deployment_start + len(
            probe_builder.deployment_bytes(
                probe_builder.SOURCE_PLAYER_DEPLOYMENTS
            )
        )
        for mode in (
            {"protagonist_death": True},
            {"timeout": True},
            {"timeout_alternate": True},
            *(
                {"turn_event": turn}
                for turn in probe_builder.TURN_EVENT_HANDLERS
            ),
            {"turn_event_alternate": True},
        ):
            data = self.result_patched(**mode)
            self.assertEqual(
                data[record_start:record_end],
                self.source[record_start:record_end],
            )
            self.assertEqual(
                data[deployment_start:deployment_end],
                self.source[deployment_start:deployment_end],
            )

    def test_protagonist_wrapper_targets_only_player_group_zero(self):
        code = probe_builder.protagonist_death_wrapper_code()
        target = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.PROTAGONIST_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("00 39 00 80")
            + (target + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(
                4,
                "big",
            ),
            code,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 00")
            + (target + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        for group in range(1, 14):
            other = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            self.assertNotIn(
                (other + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
                code,
            )
        self.assertTrue(code.endswith(bytes.fromhex("4E F9 00 02 2C 1E")))

    def test_timeout_wrapper_sets_only_verified_turn_counter(self):
        self.assertEqual(probe_builder.TIMEOUT_LAST_ALLOWED_TURN, 22)
        code = probe_builder.timeout_wrapper_code()
        self.assertEqual(
            code[:8],
            bytes.fromhex("0C 39")
            + probe_builder.TIMEOUT_LAST_ALLOWED_TURN.to_bytes(2, "big")
            + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
        )
        self.assertEqual(code[8:10], bytes.fromhex("64 08"))
        self.assertEqual(
            code[10:18],
            bytes.fromhex("13 FC")
            + probe_builder.TIMEOUT_LAST_ALLOWED_TURN.to_bytes(2, "big")
            + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
        )
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_turn_event_wrappers_set_only_the_preceding_turn(self):
        self.assertEqual(tuple(probe_builder.TURN_EVENT_HANDLERS), (16, 20, 22))
        for target_turn in probe_builder.TURN_EVENT_HANDLERS:
            preceding_turn = target_turn - 1
            code = probe_builder.turn_event_wrapper_code(target_turn)
            expected_write = (
                bytes.fromhex("13 FC")
                + preceding_turn.to_bytes(2, "big")
                + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big")
            )
            self.assertEqual(
                code[:8],
                bytes.fromhex("0C 39")
                + preceding_turn.to_bytes(2, "big")
                + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
            )
            self.assertEqual(code[8:10], bytes.fromhex("64 08"))
            self.assertEqual(code[10:18], expected_write)
            self.assertEqual(
                code[-6:],
                bytes.fromhex("4E F9")
                + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
            )

    def test_turn_event_wrapper_rejects_unknown_turn(self):
        for target_turn in (1, 15, 17, 21, 23):
            with self.assertRaisesRegex(ValueError, "must be one of"):
                probe_builder.turn_event_wrapper_code(target_turn)

    def test_turn_20_alternate_bridges_only_to_source_owned_body(self):
        data = self.result_patched(turn_event_alternate=True)
        offset = probe_builder.TURN_EVENT_ALTERNATE_TRIGGER_TARGET_OFFSET
        self.assertEqual(
            data[offset : offset + 3],
            probe_builder.TURN_EVENT_ALTERNATE_HANDLER.to_bytes(3, "big"),
        )
        alternate = probe_builder.TURN_EVENT_ALTERNATE_HANDLER
        handler_end = probe_builder.TURN_EVENT_HANDLERS[22]
        self.assertEqual(
            data[alternate:handler_end],
            self.source[alternate:handler_end],
        )
        self.assertIn(
            probe_builder.TURN_EVENT_ALTERNATE_TEXT.to_bytes(3, "big"),
            data[alternate:handler_end],
        )

    def test_result_modes_change_only_wrapper_operand_and_checksum(self):
        for mode, wrapper in (
            (
                {"protagonist_death": True},
                probe_builder.protagonist_death_wrapper_code(),
            ),
            (
                {"timeout": True},
                probe_builder.timeout_wrapper_code(),
            ),
            (
                {"timeout_alternate": True},
                probe_builder.timeout_wrapper_code(),
            ),
            *(
                (
                    {"turn_event": turn},
                    probe_builder.turn_event_wrapper_code(turn),
                )
                for turn in probe_builder.TURN_EVENT_HANDLERS
            ),
            (
                {"turn_event_alternate": True},
                probe_builder.turn_event_wrapper_code(
                    probe_builder.TURN_EVENT_ALTERNATE_TARGET
                ),
            ),
        ):
            data = self.result_patched(**mode)
            allowed = {
                0x18E,
                0x18F,
                *range(
                    probe_builder.START_MENU_ENTRY_OPERAND,
                    probe_builder.START_MENU_ENTRY_OPERAND + 4,
                ),
                *range(
                    probe_builder.ANNIHILATION_WRAPPER,
                    probe_builder.ANNIHILATION_WRAPPER + len(wrapper),
                ),
            }
            if mode.get("timeout_alternate"):
                allowed.update(
                    range(
                        probe_builder.TIMEOUT_TRIGGER_TARGET_OFFSET,
                        probe_builder.TIMEOUT_TRIGGER_TARGET_OFFSET + 3,
                    )
                )
            if mode.get("turn_event_alternate"):
                allowed.update(
                    range(
                        probe_builder.TURN_EVENT_ALTERNATE_TRIGGER_TARGET_OFFSET,
                        probe_builder.TURN_EVENT_ALTERNATE_TRIGGER_TARGET_OFFSET
                        + 3,
                    )
                )
            changed = {
                offset
                for offset, (before, after) in enumerate(zip(self.built, data))
                if before != after
            }
            self.assertLessEqual(changed, allowed)

    def test_timeout_alternate_bridges_only_to_source_owned_body(self):
        data = self.result_patched(timeout_alternate=True)
        offset = probe_builder.TIMEOUT_TRIGGER_TARGET_OFFSET
        self.assertEqual(
            data[offset : offset + 3],
            probe_builder.TIMEOUT_ALTERNATE_HANDLER.to_bytes(3, "big"),
        )
        alternate = probe_builder.TIMEOUT_ALTERNATE_HANDLER
        source_body = probe_builder.TIMEOUT_HANDLER_BYTES[
            alternate - probe_builder.TIMEOUT_HANDLER :
        ]
        self.assertEqual(
            data[alternate : alternate + len(source_body)],
            source_body,
        )

    def test_result_modes_are_mutually_exclusive_with_annihilation(self):
        for modes in (
            {"protagonist_death": True, "timeout": True},
            {"protagonist_death": True, "timeout_alternate": True},
            {"timeout": True, "timeout_alternate": True},
            {"enemy_annihilation": True, "protagonist_death": True},
            {"enemy_annihilation": True, "timeout": True},
            {"enemy_annihilation": True, "timeout_alternate": True},
            {"enemy_annihilation": True, "turn_event": 16},
            {"protagonist_death": True, "turn_event": 20},
            {"timeout": True, "turn_event": 22},
            {"timeout_alternate": True, "turn_event": 16},
            {"turn_event": 20, "turn_event_alternate": True},
            {"timeout": True, "turn_event_alternate": True},
        ):
            with self.assertRaisesRegex(ValueError, "mutually exclusive"):
                probe_builder.patch_probe(
                    bytearray(self.built),
                    self.source,
                    **modes,
                )


if __name__ == "__main__":
    unittest.main()
