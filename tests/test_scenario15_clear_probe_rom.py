import hashlib
import unittest

from tools import build_scenario15_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario15ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(
        self,
        *,
        completion_layout: bool = False,
        protagonist_death: bool = False,
        turn_event: int | None = None,
        turn_event_branch: str = "stock",
    ) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            completion_layout=completion_layout,
            protagonist_death=protagonist_death,
            turn_event=turn_event,
            turn_event_branch=turn_event_branch,
        )
        return data

    def allowed_offsets(self, *, completion_layout: bool = False) -> set[int]:
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
        if completion_layout:
            allowed.update(
                {
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 1,
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 3,
                }
            )
        return allowed

    def test_changes_only_declared_enemy_fields_and_checksum(self):
        data = self.patched()
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, self.allowed_offsets())

    def test_preserves_allied_scott_record(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        base = (
            layout.records_offset
            + probe_builder.SCOTT_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            data[base : base + FIXED_RECORD_SIZE],
            self.source[base : base + FIXED_RECORD_SIZE],
        )
        self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], 0x06)
        self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], 0x05)

    def test_weakens_every_enemy_without_changing_identity(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(data[base + FIELD_OFFSETS["at"]], 0)
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)
            for offset in (
                0,
                FIELD_OFFSETS["level"],
                FIELD_OFFSETS["name_id"],
                FIELD_OFFSETS["class_id"],
                FIELD_OFFSETS["x"],
                FIELD_OFFSETS["y"],
            ):
                self.assertEqual(data[base + offset], self.source[base + offset])

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

    def test_protagonist_death_changes_only_start_wrapper_and_checksum(self):
        data = self.patched(protagonist_death=True)
        wrapper = probe_builder.protagonist_death_wrapper_code()
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
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, expected_changes)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        records_end = (
            layout.records_offset + layout.record_count * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            data[layout.records_offset:records_end],
            self.source[layout.records_offset:records_end],
        )

    def test_protagonist_death_wrapper_marks_only_runtime_elwin(self):
        code = probe_builder.protagonist_death_wrapper_code()
        record = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.PROTAGONIST_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            (record + probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET).to_bytes(
                4, "big"
            ),
            code,
        )
        self.assertIn(
            (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertIn(
            (record + probe_builder.RUNTIME_X_OFFSET).to_bytes(4, "big"),
            code,
        )
        self.assertEqual(
            code[-6:],
            bytes.fromhex("4E F9")
            + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
        )

    def test_protagonist_death_installs_wrapper_and_rejects_conflicts(self):
        data = self.patched(protagonist_death=True)
        wrapper = probe_builder.protagonist_death_wrapper_code()
        self.assertEqual(
            data[
                probe_builder.START_MENU_ENTRY_OPERAND :
                probe_builder.START_MENU_ENTRY_OPERAND + 4
            ],
            probe_builder.RUNTIME_WRAPPER.to_bytes(4, "big"),
        )
        self.assertEqual(
            data[
                probe_builder.RUNTIME_WRAPPER :
                probe_builder.RUNTIME_WRAPPER + len(wrapper)
            ],
            wrapper,
        )
        with self.assertRaisesRegex(ValueError, "diagnostic modes conflict"):
            probe_builder.patch_probe(
                bytearray(self.production),
                self.source,
                completion_layout=True,
                protagonist_death=True,
            )

    def test_turn_event_modes_change_only_wrapper_table_target_and_checksum(self):
        for target_turn in probe_builder.TURN_EVENT_COUNTER_VALUES:
            branches = (
                ("stock", "imperial-soldier")
                if target_turn == 3
                else ("stock",)
            )
            for branch in branches:
                with self.subTest(target_turn=target_turn, branch=branch):
                    data = self.patched(
                        turn_event=target_turn,
                        turn_event_branch=branch,
                    )
                    wrapper = probe_builder.turn_event_wrapper_code(target_turn)
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
                    if branch != "stock":
                        expected_changes.update(
                            range(
                                probe_builder.TURN_EVENT_TABLE_TURN3_TARGET,
                                probe_builder.TURN_EVENT_TABLE_TURN3_TARGET + 4,
                            )
                        )
                    changed = {
                        offset
                        for offset, (before, after) in enumerate(
                            zip(self.production, data)
                        )
                        if before != after
                    }
                    self.assertLessEqual(changed, expected_changes)

    def test_turn_event_modes_preserve_deployments_and_all_fixed_records(self):
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        deployment_start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        deployment_end = deployment_start + len(
            probe_builder.deployment_bytes(
                probe_builder.SOURCE_PLAYER_DEPLOYMENTS
            )
        )
        records_end = (
            layout.records_offset + layout.record_count * FIXED_RECORD_SIZE
        )
        for target_turn in probe_builder.TURN_EVENT_COUNTER_VALUES:
            with self.subTest(target_turn=target_turn):
                data = self.patched(turn_event=target_turn)
                self.assertEqual(
                    data[deployment_start:deployment_end],
                    self.source[deployment_start:deployment_end],
                )
                self.assertEqual(
                    data[layout.record_list_offset:records_end],
                    self.source[layout.record_list_offset:records_end],
                )

    def test_turn_event_wrapper_protects_only_players_and_scott(self):
        for target_turn, counter_value in (
            probe_builder.TURN_EVENT_COUNTER_VALUES.items()
        ):
            with self.subTest(target_turn=target_turn):
                code = probe_builder.turn_event_wrapper_code(target_turn)
                for group in probe_builder.TURN_EVENT_PROTECTED_RUNTIME_GROUPS:
                    record = (
                        probe_builder.RUNTIME_GROUP_BASE
                        + group * probe_builder.RUNTIME_GROUP_SIZE
                    )
                    self.assertIn(
                        bytes.fromhex("13 FC")
                        + probe_builder.TURN_EVENT_PROTECTED_DF.to_bytes(
                            2, "big"
                        )
                        + (
                            record + probe_builder.RUNTIME_DF_OFFSET
                        ).to_bytes(4, "big"),
                        code,
                    )
                first_enemy = (
                    probe_builder.RUNTIME_GROUP_BASE
                    + (
                        probe_builder.FIRST_FIXED_RUNTIME_GROUP
                        + probe_builder.FIRST_ENEMY_RECORD_INDEX
                    )
                    * probe_builder.RUNTIME_GROUP_SIZE
                    + probe_builder.RUNTIME_DF_OFFSET
                )
                self.assertNotIn(first_enemy.to_bytes(4, "big"), code)
                self.assertIn(
                    bytes.fromhex("13 FC")
                    + counter_value.to_bytes(2, "big")
                    + probe_builder.RUNTIME_TURN_COUNTER.to_bytes(4, "big"),
                    code,
                )
                self.assertEqual(
                    code[-6:],
                    bytes.fromhex("4E F9")
                    + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
                )

    def test_source_locks_event_pointer_table_scheduled_table_and_handlers(self):
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
        for handler, (start, end) in (
            probe_builder.TURN_EVENT_HANDLER_RANGES.items()
        ):
            self.assertEqual(
                hashlib.sha256(self.source[start:end]).hexdigest(),
                probe_builder.TURN_EVENT_HANDLER_SHA256[handler],
            )
        for address in probe_builder.TURN_EVENT_TEXTS:
            self.assertTrue(
                any(
                    address.to_bytes(4, "big") in self.source[start:end]
                    for start, end in
                    probe_builder.TURN_EVENT_HANDLER_RANGES.values()
                ),
                f"missing scheduled text pointer 0x{address:06X}",
            )
        turn6_start, turn6_end = (
            probe_builder.TURN_EVENT_HANDLER_RANGES["turn-6-end-body"]
        )
        for address in probe_builder.TURN6_FIRST_CALL_TEXTS:
            self.assertIn(
                address.to_bytes(4, "big"),
                self.source[turn6_start:turn6_end],
                f"missing turn-6 first-call text pointer 0x{address:06X}",
            )

    def test_turn3_imperial_soldier_branch_changes_only_scheduled_target(self):
        data = self.patched(
            turn_event=3,
            turn_event_branch="imperial-soldier",
        )
        self.assertEqual(
            int.from_bytes(
                data[
                    probe_builder.TURN_EVENT_TABLE_TURN3_TARGET :
                    probe_builder.TURN_EVENT_TABLE_TURN3_TARGET + 4
                ],
                "big",
            ),
            probe_builder.TURN3_BRANCH_HANDLERS["imperial-soldier"],
        )
        with self.assertRaisesRegex(
            ValueError,
            "non-stock turn-event branch requires",
        ):
            probe_builder.patch_probe(
                bytearray(self.production),
                self.source,
                turn_event=2,
                turn_event_branch="imperial-soldier",
            )

    def test_turn_event_probe_rejects_changed_source_surfaces(self):
        cases = (
            (
                probe_builder.PLAYER_NAME_TABLE + 2,
                "player name table",
            ),
            (
                probe_builder.SCENARIO_EVENT_POINTER_TABLE,
                "event pointer table",
            ),
            (
                probe_builder.TURN_EVENT_TABLE,
                "scheduled turn table",
            ),
            (
                probe_builder.TURN_EVENT_HANDLER_RANGES["turn-7-entry"][0],
                "turn handler turn-7-entry",
            ),
            (
                probe_builder.TURN_EVENT_HANDLER_RANGES[
                    "turn-6-end-body"
                ][0],
                "turn handler turn-6-end-body",
            ),
        )
        for offset, message in cases:
            with self.subTest(offset=f"0x{offset:06X}"):
                source = bytearray(self.source)
                source[offset] ^= 1
                with self.assertRaisesRegex(ValueError, message):
                    probe_builder.patch_probe(
                        bytearray(self.production),
                        bytes(source),
                        turn_event=7,
                    )

    def test_completion_layout_moves_only_elwin_above_escape_region(self):
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
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        expected = probe_builder.deployment_bytes(
            (
                probe_builder.COMPLETION_ELWIN_POSITION,
                *probe_builder.SOURCE_PLAYER_DEPLOYMENTS[1:],
            )
        )
        self.assertEqual(data[start : start + len(expected)], expected)

    def test_source_verified_completion_triggers_are_locked(self):
        for offset, expected in probe_builder.COMPLETION_TRIGGERS.items():
            self.assertEqual(
                self.source[offset : offset + len(expected)],
                expected,
            )
        escape = probe_builder.COMPLETION_TRIGGERS[0x19F148]
        self.assertEqual(escape[0], 0x0D)
        self.assertEqual(escape[1], 0x01)
        self.assertEqual(tuple(escape[4:8]), probe_builder.ESCAPE_BOUNDS)
        self.assertEqual(probe_builder.ESCAPE_TARGET, (3, 21))
        death = probe_builder.COMPLETION_TRIGGERS[0x19F154]
        self.assertEqual(death[0], 0x0E)
        self.assertEqual(death[1], 0x01)
        self.assertEqual(
            int.from_bytes(death[8:12], "big"),
            probe_builder.PROTAGONIST_DEATH_HANDLER,
        )
        start = probe_builder.PROTAGONIST_DEATH_HANDLER
        end = start + len(probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES)
        self.assertEqual(
            self.source[start:end],
            probe_builder.PROTAGONIST_DEATH_HANDLER_BYTES,
        )

    def test_default_and_completion_checksums_are_locked(self):
        default = bytearray(self.production)
        completion = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(default, self.source),
            0x630A,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                completion,
                self.source,
                completion_layout=True,
            ),
            0x631C,
        )
        death = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(
                death,
                self.source,
                protagonist_death=True,
            ),
            0x4B91,
        )
        for target_turn, checksum in (
            (2, 0x8289),
            (3, 0x828D),
            (6, 0x8291),
            (7, 0x8293),
            (8, 0x8295),
        ):
            with self.subTest(target_turn=target_turn):
                data = bytearray(self.production)
                self.assertEqual(
                    probe_builder.patch_probe(
                        data,
                        self.source,
                        turn_event=target_turn,
                    ),
                    checksum,
                )
        alternate = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(
                alternate,
                self.source,
                turn_event=3,
                turn_event_branch="imperial-soldier",
            ),
            0x82B7,
        )

    def test_preserves_imelda_and_hidden_enemy_identities(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            probe_builder.IMELDA_RECORD_INDEX: (0x15, 0x4A, False),
            8: (0x3E, 0x53, True),
            9: (0x0C, 0x60, True),
            10: (0x3F, 0x53, True),
            11: (0x52, 0x55, True),
        }
        for index, (name_id, class_id, hidden) in expected.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(bool(data[base] & 0x80), hidden)
            self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], class_id)
            if hidden:
                self.assertEqual(
                    data[
                        base + FIELD_OFFSETS["x"] : base + FIELD_OFFSETS["y"] + 1
                    ],
                    b"\xFF\xFF",
                )

    def test_rejects_non_source_fixed_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 0"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
