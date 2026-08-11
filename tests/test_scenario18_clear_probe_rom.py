import unittest

from tools import build_scenario18_clear_probe_rom as probe_builder
from tools.scenario_data import FIELD_OFFSETS, FIXED_RECORD_SIZE, scenario_layout


class Scenario18ClearProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = probe_builder.DEFAULT_SOURCE_ROM.read_bytes()
        cls.production = probe_builder.DEFAULT_INPUT_ROM.read_bytes()

    def patched(
        self,
        *,
        completion_layout: bool = False,
        dark_princess_layout: bool = False,
        protagonist_death: bool = False,
        resident_annihilation: bool = False,
        resident_combat_loss: bool = False,
        resident_combat_loss_fix: bool = False,
        resident_combat_loss_same_bank_fix: bool = False,
        resident_combat_loss_inplace_fix: bool = False,
    ) -> bytearray:
        data = bytearray(self.production)
        probe_builder.patch_probe(
            data,
            self.source,
            completion_layout=completion_layout,
            dark_princess_layout=dark_princess_layout,
            protagonist_death=protagonist_death,
            resident_annihilation=resident_annihilation,
            resident_combat_loss=resident_combat_loss,
            resident_combat_loss_fix=resident_combat_loss_fix,
            resident_combat_loss_same_bank_fix=(
                resident_combat_loss_same_bank_fix
            ),
            resident_combat_loss_inplace_fix=(
                resident_combat_loss_inplace_fix
            ),
        )
        return data

    def allowed_offsets(
        self,
        *,
        completion_layout: bool = False,
        dark_princess_layout: bool = False,
    ) -> set[int]:
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
        if completion_layout or dark_princess_layout:
            allowed.update(
                {
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 1,
                    probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET + 3,
                }
            )
        if completion_layout:
            wrapper = probe_builder.completion_hp_wrapper_code()
            allowed.update(
                range(
                    probe_builder.START_MENU_ENTRY_OPERAND,
                    probe_builder.START_MENU_ENTRY_OPERAND + 4,
                )
            )
            allowed.update(
                range(
                    probe_builder.RUNTIME_WRAPPER,
                    probe_builder.RUNTIME_WRAPPER + len(wrapper),
                )
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

    def test_preserves_both_resident_records_byte_identical(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_RESIDENT_RECORD_INDEX,
            probe_builder.LAST_RESIDENT_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(
                data[base : base + FIXED_RECORD_SIZE],
                self.source[base : base + FIXED_RECORD_SIZE],
            )
            self.assertEqual(self.source[base + 0x08], 0x03)
            self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], 0x97)
            self.assertEqual(
                self.source[
                    base + FIELD_OFFSETS["mercenaries"] :
                    base + FIELD_OFFSETS["mercenaries"] + 4
                ],
                b"\x71" * 4,
            )

    def test_weakens_every_enemy_without_changing_identity(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        for index in range(
            probe_builder.FIRST_ENEMY_RECORD_INDEX,
            probe_builder.LAST_ENEMY_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(self.source[base + 0x08], 0x04)
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

    def test_preserves_great_dragon_and_lana_source_records(self):
        data = self.patched()
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        expected = {
            probe_builder.GREAT_DRAGON_RECORD_INDEX: (
                probe_builder.GREAT_DRAGON_NAME_ID,
                probe_builder.GREAT_DRAGON_CLASS_ID,
                1,
                39,
                34,
            ),
            probe_builder.LANA_RECORD_INDEX: (0x0C, 0x60, 3, 37, 34),
        }
        for index, (name_id, class_id, level, at, df) in expected.items():
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            self.assertEqual(self.source[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["class_id"]], class_id)
            self.assertEqual(self.source[base + FIELD_OFFSETS["level"]], level)
            self.assertEqual(self.source[base + FIELD_OFFSETS["at"]], at)
            self.assertEqual(self.source[base + FIELD_OFFSETS["df"]], df)
            self.assertEqual(data[base + FIELD_OFFSETS["name_id"]], name_id)
            self.assertEqual(data[base + FIELD_OFFSETS["class_id"]], class_id)
        dragon = layout.records_offset + (
            probe_builder.GREAT_DRAGON_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            (
                self.source[dragon + FIELD_OFFSETS["x"]],
                self.source[dragon + FIELD_OFFSETS["y"]],
            ),
            probe_builder.GREAT_DRAGON_POSITION,
        )

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

    def test_completion_layout_moves_only_elwin_below_source_dragon(self):
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

    def test_completion_wrapper_targets_only_the_source_great_dragon(self):
        wrapper = probe_builder.completion_hp_wrapper_code()
        record = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.GREAT_DRAGON_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        self.assertIn(
            bytes.fromhex("0C 39 00")
            + probe_builder.GREAT_DRAGON_NAME_ID.to_bytes(1, "big")
            + (record + probe_builder.RUNTIME_NAME_OFFSET).to_bytes(4, "big"),
            wrapper,
        )
        self.assertIn(
            bytes.fromhex("0C 39 00")
            + probe_builder.GREAT_DRAGON_CLASS_ID.to_bytes(1, "big")
            + record.to_bytes(4, "big"),
            wrapper,
        )
        self.assertIn(
            bytes.fromhex("13 FC 00 01")
            + (record + probe_builder.RUNTIME_HP_OFFSET).to_bytes(4, "big"),
            wrapper,
        )

    def test_dark_princess_layout_moves_only_elwin_below_source_lana(self):
        data = self.patched(dark_princess_layout=True)
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(
            changed,
            self.allowed_offsets(dark_princess_layout=True),
        )
        start = probe_builder.FIRST_PLAYER_DEPLOYMENT_OFFSET
        expected = probe_builder.deployment_bytes(
            (
                probe_builder.DARK_PRINCESS_ELWIN_POSITION,
                *probe_builder.SOURCE_PLAYER_DEPLOYMENTS[1:],
            )
        )
        self.assertEqual(data[start : start + len(expected)], expected)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        lana = (
            layout.records_offset
            + probe_builder.LANA_RECORD_INDEX * FIXED_RECORD_SIZE
        )
        self.assertEqual(
            (
                data[lana + FIELD_OFFSETS["x"]],
                data[lana + FIELD_OFFSETS["y"]],
            ),
            probe_builder.DARK_PRINCESS_POSITION,
        )

    def test_runtime_defeat_modes_change_only_wrapper_and_checksum(self):
        for mode in ("protagonist_death", "resident_annihilation"):
            with self.subTest(mode=mode):
                data = self.patched(**{mode: True})
                wrapper = (
                    probe_builder.protagonist_death_wrapper_code()
                    if mode == "protagonist_death"
                    else probe_builder.resident_annihilation_wrapper_code()
                )
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
                    for offset, (before, after) in enumerate(
                        zip(self.production, data)
                    )
                    if before != after
                }
                self.assertLessEqual(changed, expected_changes)
                layout = scenario_layout(
                    self.source, probe_builder.SCENARIO_NUMBER
                )
                records_end = (
                    layout.records_offset
                    + layout.record_count * FIXED_RECORD_SIZE
                )
                self.assertEqual(
                    data[layout.records_offset:records_end],
                    self.source[layout.records_offset:records_end],
                )

    def test_runtime_defeat_wrappers_target_only_declared_groups(self):
        protagonist_code = probe_builder.protagonist_death_wrapper_code()
        protagonist_record = (
            probe_builder.RUNTIME_GROUP_BASE
            + probe_builder.PROTAGONIST_RUNTIME_GROUP
            * probe_builder.RUNTIME_GROUP_SIZE
        )
        for offset in (
            probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET,
            probe_builder.RUNTIME_HP_OFFSET,
            probe_builder.RUNTIME_X_OFFSET,
        ):
            self.assertIn(
                (protagonist_record + offset).to_bytes(4, "big"),
                protagonist_code,
            )

        resident_code = probe_builder.resident_annihilation_wrapper_code()
        self.assertEqual(resident_code[:2], bytes.fromhex("2F 00"))
        self.assertEqual(resident_code[-14:-12], bytes.fromhex("20 1F"))
        self.assertIn(
            bytes.fromhex(
                "41 F9 FF FF 60 3C "
                "70 13 "
                "0C 28 00 20 00 01 "
                "67 08 "
                "0C 28 00 21 00 01 "
                "66 04 "
                "42 28 00 03 "
                "D0 FC 00 60 "
                "51 C8 FF E6"
            ),
            resident_code,
        )
        self.assertIn(
            bytes.fromhex(
                "41 F9 FF FF 60 3C "
                "70 13 "
                "0C 28 00 01 00 01 "
                "67 0A "
                "D0 FC 00 60 "
                "51 C8 FF F2 "
                "60 0C "
                "11 7C 00 09 00 06 "
                "11 7C 00 0C 00 07"
            ),
            resident_code,
        )
        for group in range(probe_builder.RUNTIME_GROUP_COUNT):
            record = (
                probe_builder.RUNTIME_GROUP_BASE
                + group * probe_builder.RUNTIME_GROUP_SIZE
            )
            for offset in (
                probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET,
                probe_builder.RUNTIME_HP_OFFSET,
                probe_builder.RUNTIME_X_OFFSET,
                probe_builder.RUNTIME_Y_OFFSET,
            ):
                self.assertNotIn(
                    (record + offset).to_bytes(4, "big"),
                    resident_code,
                )
        self.assertEqual(
            resident_code.count(
                probe_builder.RUNTIME_GROUP_BASE.to_bytes(4, "big")
            ),
            2,
        )
        for offset in (
            probe_builder.RUNTIME_DEFEATED_FLAG_OFFSET,
            probe_builder.RUNTIME_HP_OFFSET,
        ):
            self.assertNotIn(
                (protagonist_record + offset).to_bytes(4, "big"),
                resident_code,
            )
        for code in (protagonist_code, resident_code):
            self.assertEqual(
                code[-12:],
                bytes.fromhex("41 F9")
                + probe_builder.START_MENU_ENTRY.to_bytes(4, "big")
                + bytes.fromhex("4E F9")
                + probe_builder.START_MENU_ENTRY.to_bytes(4, "big"),
            )

    def test_runtime_defeat_modes_install_wrapper_and_reject_conflicts(self):
        for mode in ("protagonist_death", "resident_annihilation"):
            with self.subTest(mode=mode):
                data = self.patched(**{mode: True})
                wrapper = (
                    probe_builder.protagonist_death_wrapper_code()
                    if mode == "protagonist_death"
                    else probe_builder.resident_annihilation_wrapper_code()
                )
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
        conflict_pairs = (
            {"completion_layout": True, "dark_princess_layout": True},
            {"completion_layout": True, "protagonist_death": True},
            {"dark_princess_layout": True, "resident_annihilation": True},
            {"protagonist_death": True, "resident_annihilation": True},
            {"resident_annihilation": True, "resident_combat_loss": True},
            {"resident_combat_loss": True, "resident_combat_loss_fix": True},
            {
                "resident_combat_loss_fix": True,
                "resident_combat_loss_inplace_fix": True,
            },
            {
                "resident_combat_loss_fix": True,
                "resident_combat_loss_same_bank_fix": True,
            },
        )
        for modes in conflict_pairs:
            with self.subTest(modes=modes):
                with self.assertRaisesRegex(
                    ValueError, "diagnostic modes conflict"
                ):
                    probe_builder.patch_probe(
                        bytearray(self.production),
                        self.source,
                        **modes,
                    )

    def test_resident_combat_loss_stages_only_declared_fixed_fields(self):
        data = self.patched(resident_combat_loss=True)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        allowed = {0x18E, 0x18F}
        for index in range(
            probe_builder.FIRST_RESIDENT_RECORD_INDEX,
            probe_builder.LAST_RESIDENT_RECORD_INDEX + 1,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            allowed.add(base + FIELD_OFFSETS["df"])
            allowed.update(
                base + FIELD_OFFSETS["mercenaries"] + slot
                for slot in range(6)
            )
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
            self.assertEqual(data[base + FIELD_OFFSETS["df"]], 0)
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)

        for index, position in zip(
            probe_builder.RESIDENT_COMBAT_ATTACKER_RECORDS,
            probe_builder.RESIDENT_COMBAT_ATTACKER_POSITIONS,
        ):
            base = layout.records_offset + index * FIXED_RECORD_SIZE
            allowed.update(
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
            for offset in (
                0,
                0x08,
                FIELD_OFFSETS["level"],
                FIELD_OFFSETS["name_id"],
                FIELD_OFFSETS["class_id"],
            ):
                self.assertEqual(data[base + offset], self.source[base + offset])
            self.assertEqual(
                data[base + FIELD_OFFSETS["at"]],
                probe_builder.RESIDENT_COMBAT_ATTACKER_AT,
            )
            self.assertEqual(
                data[base + FIELD_OFFSETS["df"]],
                probe_builder.RESIDENT_COMBAT_ATTACKER_DF,
            )
            self.assertEqual(
                (
                    data[base + FIELD_OFFSETS["x"]],
                    data[base + FIELD_OFFSETS["y"]],
                ),
                position,
            )
            mercenaries = base + FIELD_OFFSETS["mercenaries"]
            self.assertEqual(data[mercenaries : mercenaries + 6], b"\xFF" * 6)

        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.production, data))
            if before != after
        }
        self.assertLessEqual(changed, allowed)

    def test_obsolete_resident_loss_diagnostics_reject_fixed_production(self):
        for mode in (
            {"resident_combat_loss_fix": True},
            {"resident_combat_loss_inplace_fix": True},
        ):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(
                    ValueError,
                    "defeat-trigger pointer|final group-death trigger",
                ):
                    self.patched(**mode)

    def test_resident_combat_loss_same_bank_fix_rehomes_dialogue(self):
        data = self.patched(resident_combat_loss_same_bank_fix=True)
        dialogue_size = (
            probe_builder.DISPLACED_DIALOGUE_CHAIN_END
            - probe_builder.DISPLACED_DIALOGUE_CHAIN_START
        )
        dialogue = self.production[
            probe_builder.RELOCATED_DIALOGUE_CHAIN :
            probe_builder.RELOCATED_DIALOGUE_CHAIN + dialogue_size
        ]
        relocated_end = (
            probe_builder.RELOCATED_DIALOGUE_CHAIN + len(dialogue)
        )
        self.assertEqual(
            data[
                probe_builder.RELOCATED_DIALOGUE_CHAIN : relocated_end
            ],
            dialogue,
        )
        self.assertEqual(
            data[
                probe_builder.DISPLACED_DIALOGUE_POINTER :
                probe_builder.DISPLACED_DIALOGUE_POINTER + 4
            ],
            probe_builder.RELOCATED_DIALOGUE_CHAIN.to_bytes(4, "big"),
        )
        self.assertEqual(
            data[
                probe_builder.DEFEAT_TRIGGER_POINTER :
                probe_builder.DEFEAT_TRIGGER_POINTER + 4
            ],
            probe_builder.SAME_BANK_DEFEAT_TRIGGER_LIST.to_bytes(4, "big"),
        )
        code = probe_builder.resident_loss_trigger_code(
            self.source,
            event_id=probe_builder.SAME_BANK_RESIDENT_LOSS_EVENT_ID,
        )
        self.assertEqual(
            data[
                probe_builder.SAME_BANK_DEFEAT_TRIGGER_LIST :
                probe_builder.SAME_BANK_DEFEAT_TRIGGER_LIST + len(code)
            ],
            code,
        )
        self.assertEqual(
            data[
                probe_builder.SAME_BANK_DEFEAT_TRIGGER_LIST :
                probe_builder.SAME_BANK_DEFEAT_TRIGGER_LIST
                + (
                    probe_builder.DEFEAT_TRIGGER_LIST_END
                    - probe_builder.DEFEAT_TRIGGER_LIST
                    - 2
                )
            ],
            self.source[
                probe_builder.DEFEAT_TRIGGER_LIST :
                probe_builder.DEFEAT_TRIGGER_LIST_END - 2
            ],
        )
        aggregate_offset = (
            probe_builder.DEFEAT_TRIGGER_LIST_END
            - probe_builder.DEFEAT_TRIGGER_LIST
            - 2
        )
        self.assertEqual(
            code[aggregate_offset],
            probe_builder.SAME_BANK_RESIDENT_LOSS_EVENT_ID,
        )
        self.assertEqual(
            code[-6:-2],
            probe_builder.RESIDENT_LOSS_HANDLER.to_bytes(4, "big"),
        )
        self.assertEqual(code[-2:], b"\xFF\xFF")

    def test_source_victory_and_defeat_events_are_locked(self):
        records = (
            (
                probe_builder.PROTAGONIST_DEATH_TRIGGER,
                probe_builder.PROTAGONIST_DEATH_TRIGGER_BYTES,
            ),
            (
                probe_builder.FIRST_RESIDENT_DEATH_TRIGGER,
                probe_builder.FIRST_RESIDENT_DEATH_TRIGGER_BYTES,
            ),
            (
                probe_builder.SECOND_RESIDENT_DEATH_TRIGGER,
                probe_builder.SECOND_RESIDENT_DEATH_TRIGGER_BYTES,
            ),
            (
                probe_builder.DARK_PRINCESS_DEATH_TRIGGER,
                probe_builder.DARK_PRINCESS_DEATH_TRIGGER_BYTES,
            ),
            (
                probe_builder.GREAT_DRAGON_DEATH_TRIGGER,
                probe_builder.GREAT_DRAGON_DEATH_TRIGGER_BYTES,
            ),
            (
                probe_builder.PROTAGONIST_DEATH_EVENT,
                probe_builder.PROTAGONIST_DEATH_EVENT_BYTES,
            ),
            (
                probe_builder.FIRST_RESIDENT_DEATH_EVENT,
                probe_builder.FIRST_RESIDENT_DEATH_EVENT_BYTES,
            ),
            (
                probe_builder.SECOND_RESIDENT_DEATH_EVENT,
                probe_builder.SECOND_RESIDENT_DEATH_EVENT_BYTES,
            ),
            (
                probe_builder.DARK_PRINCESS_DEATH_EVENT,
                probe_builder.DARK_PRINCESS_DEATH_EVENT_BYTES,
            ),
            (
                probe_builder.GREAT_DRAGON_DEATH_EVENT,
                probe_builder.GREAT_DRAGON_DEATH_EVENT_BYTES,
            ),
        )
        for start, expected in records:
            with self.subTest(start=f"0x{start:06X}"):
                self.assertEqual(
                    self.source[start : start + len(expected)],
                    expected,
                )

    def test_default_and_completion_checksums_are_locked(self):
        default = bytearray(self.production)
        completion = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(default, self.source),
            0x8E29,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                completion,
                self.source,
                completion_layout=True,
            ),
            0x6331,
        )
        dark_princess = bytearray(self.production)
        protagonist_death = bytearray(self.production)
        resident_annihilation = bytearray(self.production)
        resident_combat_loss = bytearray(self.production)
        resident_combat_loss_same_bank_fix = bytearray(self.production)
        self.assertEqual(
            probe_builder.patch_probe(
                dark_princess,
                self.source,
                dark_princess_layout=True,
            ),
            0x8E3C,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                protagonist_death,
                self.source,
                protagonist_death=True,
            ),
            0x4B91,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                resident_annihilation,
                self.source,
                resident_annihilation=True,
            ),
            0xD931,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                resident_combat_loss,
                self.source,
                resident_combat_loss=True,
            ),
            0x0725,
        )
        self.assertEqual(
            probe_builder.patch_probe(
                resident_combat_loss_same_bank_fix,
                self.source,
                resident_combat_loss_same_bank_fix=True,
            ),
            0x0725,
        )

    def test_rejects_non_source_fixed_record(self):
        damaged = bytearray(self.production)
        layout = scenario_layout(self.source, probe_builder.SCENARIO_NUMBER)
        damaged[layout.records_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "fixed record 0"):
            probe_builder.patch_probe(damaged, self.source)


if __name__ == "__main__":
    unittest.main()
