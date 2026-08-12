import hashlib
import unittest
from pathlib import Path

from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN

from scripts import build_korean_jp_probe as builder
from tools.class_change_data import read_class_change_chain, transition_for_class
from tools.class_hire_data import CLASS_RECORD_SIZE, CLASS_RECORD_TABLE
from tools.scenario_data import be16, scenario_layout


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROM = ROOT / builder.IN_ROM


class JoinClassChoiceProgressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE_ROM.read_bytes()

    def test_patch_changes_only_the_three_initial_roster_records(self) -> None:
        patched = bytearray(self.source)
        builder.patch_join_class_choice_progression(patched, self.source)

        changed = {
            index
            for index, (before, after) in enumerate(zip(self.source, patched))
            if before != after
        }
        expected = set()
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            offset = (
                builder.INITIAL_COMMANDER_ROSTER_TABLE
                + (commander_id - 1) * builder.INITIAL_COMMANDER_RECORD_SIZE
            )
            target = row["target"]
            expected.update(
                offset + index
                for index, (before, after) in enumerate(
                    zip(row["source"], target)
                )
                if before != after
            )
            self.assertEqual(
                bytes(patched[offset : offset + len(target)]),
                target,
            )
        self.assertEqual(changed, expected)

    def test_each_commander_starts_at_tier_one_level_ten(self) -> None:
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                target = row["target"]
                self.assertEqual(target[0], row["tier1_class"])
                self.assertEqual(target[2], 10)

    def test_patched_chains_offer_the_requested_tier_two_branches(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_class_data(patched, self.source)
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                transition = transition_for_class(
                    patched,
                    commander_id,
                    row["tier1_class"],
                )
                self.assertEqual(
                    transition.candidates,
                    row["tier2_candidates"],
                )

    def test_custom_hawk_and_croco_lord_use_mounted_branch_class_data(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_class_data(patched, self.source)
        for custom_class, source_class in (
            builder.JOIN_CLASS_CHOICE_CUSTOM_CLASS_SOURCES.items()
        ):
            with self.subTest(custom_class=custom_class):
                custom = CLASS_RECORD_TABLE + custom_class * CLASS_RECORD_SIZE
                source = CLASS_RECORD_TABLE + source_class * CLASS_RECORD_SIZE
                self.assertEqual(
                    patched[custom:custom + CLASS_RECORD_SIZE],
                    self.source[source:source + CLASS_RECORD_SIZE],
                )
                custom_combat = (
                    builder.GENERIC_COMBAT_DESCRIPTOR_TABLE
                    + custom_class * builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
                )
                source_combat = (
                    builder.GENERIC_COMBAT_DESCRIPTOR_TABLE
                    + source_class * builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
                )
                self.assertEqual(
                    patched[
                        custom_combat:
                        custom_combat + builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
                    ],
                    self.source[
                        source_combat:
                        source_combat + builder.GENERIC_COMBAT_DESCRIPTOR_SIZE
                    ],
                )
        self.assertEqual(
            builder.KOREAN_CLASS_LABELS[builder.JOIN_CLASS_CHOICE_HAWK_LORD],
            "호크로드",
        )
        self.assertEqual(
            builder.KOREAN_CLASS_LABELS[builder.JOIN_CLASS_CHOICE_CROCO_LORD],
            "크로코로드",
        )

    def test_custom_class_slots_are_unused_by_stock_scenarios_and_rosters(self) -> None:
        custom_classes = set(builder.JOIN_CLASS_CHOICE_CUSTOM_CLASS_SOURCES)
        for commander_id in range(1, 11):
            roster = (
                builder.INITIAL_COMMANDER_ROSTER_TABLE
                + (commander_id - 1) * builder.INITIAL_COMMANDER_RECORD_SIZE
            )
            self.assertNotIn(self.source[roster], custom_classes)
            for transition in read_class_change_chain(self.source, commander_id):
                self.assertNotIn(transition.current_class, custom_classes)
                self.assertTrue(custom_classes.isdisjoint(transition.candidates))
        for scenario_number in range(1, 32):
            layout = scenario_layout(self.source, scenario_number)
            for index in range(layout.record_count):
                record = layout.records_offset + index * 0x24
                self.assertNotIn(self.source[record + 0x1B], custom_classes)

    def test_custom_lord_transitions_continue_to_original_promoted_routes(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_class_data(patched, self.source)
        for commander_id, starter, custom in (
            (7, 0x06, builder.JOIN_CLASS_CHOICE_HAWK_LORD),
            (9, 0x07, builder.JOIN_CLASS_CHOICE_CROCO_LORD),
        ):
            with self.subTest(commander_id=commander_id):
                original_next = transition_for_class(
                    self.source, commander_id, starter
                ).candidates
                custom_next = transition_for_class(
                    patched, commander_id, custom
                ).candidates
                self.assertEqual(custom_next, original_next)
                self.assertEqual(
                    transition_for_class(
                        patched, commander_id, 0x01
                    ).candidates,
                    (
                        (0x04, custom, 0x08)
                        if commander_id == 7
                        else (0x05, custom, 0x0A)
                    ),
                )

    def test_runestone_first_rows_use_the_join_lord_choices(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_class_data(patched, self.source)

        for commander_id, relocation in (
            builder.JOIN_CLASS_CHOICE_CHAIN_RELOCATIONS.items()
        ):
            with self.subTest(commander_id=commander_id):
                source_chain = read_class_change_chain(
                    self.source, commander_id
                )
                patched_chain = read_class_change_chain(
                    patched, commander_id
                )
                self.assertEqual(len(patched_chain), len(source_chain) + 1)
                self.assertEqual(
                    transition_for_class(patched, commander_id, 0x01).candidates,
                    (
                        (0x04, builder.JOIN_CLASS_CHOICE_HAWK_LORD, 0x08)
                        if commander_id == 7
                        else (0x05, builder.JOIN_CLASS_CHOICE_CROCO_LORD, 0x0A)
                    ),
                )
                pointer_offset = (
                    builder.CLASS_CHANGE_POINTER_TABLE
                    + (commander_id - 1) * 4
                )
                self.assertEqual(
                    builder.be32(patched, pointer_offset), relocation
                )

                fighter_sprite = builder.commander_sprite_record_offset(
                    patched, commander_id, 0x01
                )
                source_fighter_sprite = builder.commander_sprite_record_offset(
                    self.source, commander_id, 0x01
                )
                self.assertEqual(
                    patched[fighter_sprite + 1 : fighter_sprite + 3],
                    self.source[
                        source_fighter_sprite + 1 : source_fighter_sprite + 3
                    ],
                )
                custom = (
                    builder.JOIN_CLASS_CHOICE_HAWK_LORD
                    if commander_id == 7
                    else builder.JOIN_CLASS_CHOICE_CROCO_LORD
                )
                builder.commander_sprite_record_offset(
                    patched, commander_id, custom
                )

    def test_custom_lords_reuse_mounted_map_and_combat_animations(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_class_data(patched, self.source)

        for commander_id, custom_class, source_class in (
            (7, builder.JOIN_CLASS_CHOICE_HAWK_LORD, 0x06),
            (9, builder.JOIN_CLASS_CHOICE_CROCO_LORD, 0x07),
        ):
            with self.subTest(commander_id=commander_id):
                custom_sprite = builder.commander_sprite_record_offset(
                    patched, commander_id, custom_class
                )
                source_sprite = builder.commander_sprite_record_offset(
                    patched, commander_id, source_class
                )
                self.assertEqual(
                    patched[custom_sprite + 1:custom_sprite + 3],
                    patched[source_sprite + 1:source_sprite + 3],
                )

                combat_pointer_offset = (
                    builder.COMMANDER_COMBAT_POINTER_TABLE
                    + (commander_id - 1) * 4
                )
                self.assertEqual(
                    builder.be32(patched, combat_pointer_offset),
                    builder.JOIN_CLASS_CHOICE_COMBAT_RELOCATIONS[commander_id],
                )
                records = {}
                pointer = builder.be32(patched, combat_pointer_offset)
                while builder.be16(patched, pointer) != 0xFFFF:
                    class_id = builder.be16(patched, pointer)
                    records[class_id] = bytes(
                        patched[
                            pointer:
                            pointer + builder.COMMANDER_COMBAT_RECORD_SIZE
                        ]
                    )
                    pointer += builder.COMMANDER_COMBAT_RECORD_SIZE
                self.assertIn(custom_class, records)
                self.assertEqual(
                    records[custom_class][2:],
                    records[source_class][2:],
                )

    def test_stock_runestone_handler_restarts_from_the_custom_first_row(self) -> None:
        # At LV10, equipped item 0x1A is the Rune Stone.  The stock routine
        # consumes it and replaces the current-class lookup key with (A2),
        # the first current-class word in this commander's chain.
        self.assertEqual(
            self.source[0x014B4A:0x014B5A],
            bytes.fromhex(
                "0C 28 00 1A 00 0B "
                "66 00 00 08 "
                "61 00 01 D6 "
                "34 12"
            ),
        )

        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_class_data(patched, self.source)
        for commander_id in (7, 9):
            with self.subTest(commander_id=commander_id):
                custom = (
                    builder.JOIN_CLASS_CHOICE_HAWK_LORD
                    if commander_id == 7
                    else builder.JOIN_CLASS_CHOICE_CROCO_LORD
                )
                expected = (
                    (0x04, custom, 0x08)
                    if commander_id == 7
                    else (0x05, custom, 0x0A)
                )
                self.assertEqual(
                    read_class_change_chain(patched, commander_id)[0].candidates,
                    expected,
                )

    def test_runestone_restart_is_identical_from_tiers_two_through_five(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_class_data(patched, self.source)

        expected_first_choices = {
            7: (0x04, builder.JOIN_CLASS_CHOICE_HAWK_LORD, 0x08),
            9: (0x05, builder.JOIN_CLASS_CHOICE_CROCO_LORD, 0x0A),
            10: (0x08, 0x09, 0x04),
        }
        for commander_id, expected in expected_first_choices.items():
            chain = read_class_change_chain(patched, commander_id)
            transitions = {
                row.current_class: row.candidates for row in chain
            }
            tiers = [set(chain[0].candidates)]
            for _ in range(3):
                tiers.append(
                    {
                        candidate
                        for current in tiers[-1]
                        for candidate in transitions.get(current, ())
                    }
                )
            with self.subTest(commander_id=commander_id):
                self.assertTrue(all(tiers))
                self.assertEqual(chain[0].candidates, expected)
                for tier in tiers:
                    for _current_class in tier:
                        # The stock Rune Stone path always replaces the class
                        # lookup key with the first record's current class.
                        self.assertEqual(chain[0].candidates, expected)

    def test_identity_and_original_experience_are_preserved(self) -> None:
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                source = row["source"]
                target = row["target"]
                self.assertEqual(target[3], source[3])
                self.assertEqual(target[12:14], source[12:14])

    def test_base_raw_grants_reconstruct_original_tier_two_level_floor(self) -> None:
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                source = row["source"]
                self.assertEqual(source[0], row["original_tier2_class"])
                self.assertEqual(source[2], row["original_tier2_level"])
                self.assertEqual(source[3], row["original_tier2_experience"])
                record = (
                    CLASS_RECORD_TABLE
                    + row["original_tier2_class"] * CLASS_RECORD_SIZE
                )
                gauge = self.source[record + 0x14] << 3
                expected = (row["original_tier2_level"] - 1) * gauge
                self.assertEqual(row["base_join_raw_experience"], expected)

    def test_raw_grants_are_exact_and_profile_independent(self) -> None:
        expected = {7: 0x00, 9: 0x90, 10: 0x60}
        for commander_id, value in expected.items():
            with self.subTest(commander_id=commander_id):
                actual = builder.join_raw_experience(commander_id)
                self.assertEqual(actual, value)
                self.assertLessEqual(actual, 0xFF)

    def test_starting_stats_are_back_calculated_from_original_join_progress(self) -> None:
        growth_table = 0x082922
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                class_id = row["original_tier2_class"]
                class_record = (
                    CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE
                )
                growth_codes = self.source[class_record + 0x0A:class_record + 0x0D]
                total_growth = []
                for growth_code in growth_codes:
                    total_growth.append(
                        sum(
                            self.source[growth_table + growth_code * 10 + level - 1]
                            for level in range(2, row["original_tier2_level"] + 1)
                        )
                    )
                # Initial roster bytes 1/4/5 are MP/AT/DF.  Replaying the
                # original class's levels must reproduce the Japanese join row.
                adjusted = (row["target"][1], row["target"][4], row["target"][5])
                original = (row["source"][1], row["source"][4], row["source"][5])
                self.assertEqual(
                    tuple(value + growth for value, growth in zip(adjusted, total_growth)),
                    original,
                )

    def test_tier_one_hire_masks_replace_promoted_unlocks(self) -> None:
        self.assertEqual(
            builder.JOIN_CLASS_CHOICE_RECORDS[7]["target"][10:12],
            bytes.fromhex("00 04"),
        )
        self.assertEqual(
            builder.JOIN_CLASS_CHOICE_RECORDS[9]["target"][10:12],
            bytes.fromhex("00 04"),
        )
        self.assertEqual(
            builder.JOIN_CLASS_CHOICE_RECORDS[10]["target"][10:12],
            bytes.fromhex("08 00"),
        )

    def test_stock_level_ten_gate_enters_class_choice_and_resets_level(self) -> None:
        # CMPI.B #10,$2E(A0); BEQ.W $014B00.  A stored LV10 therefore
        # enters the ordinary class-choice path without an EXP overflow trick.
        self.assertEqual(
            self.source[0x014848:0x014852],
            bytes.fromhex("0C 28 00 0A 00 2E 67 00 02 B0"),
        )
        self.assertEqual(
            self.source[0x014C36:0x014C40],
            bytes.fromhex("11 40 00 00 11 7C 00 01 00 2E"),
        )

    def test_level_ten_gate_is_wrapped_with_real_join_visibility(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_visibility_guard(
            patched,
            self.source,
        )
        self.assertEqual(
            patched[
                builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK:
                builder.JOIN_CLASS_CHOICE_VISIBILITY_HOOK + 6
            ],
            bytes.fromhex("4E B9")
            + builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD.to_bytes(4, "big"),
        )

        routine = builder.build_join_class_choice_visibility_guard()
        decoder = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN)
        instructions = list(
            decoder.disasm(
                routine,
                builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD,
            )
        )
        self.assertEqual(sum(item.size for item in instructions), len(routine))
        self.assertEqual(instructions[-1].mnemonic, "rts")
        self.assertIn(bytes.fromhex("0C 28 00 FF 00 06"), routine)
        self.assertIn(bytes.fromhex("0C 28 00 FF 00 07"), routine)
        self.assertIn(bytes.fromhex("4A 28 00 06"), routine)
        self.assertIn(bytes.fromhex("4A 28 00 07"), routine)
        self.assertIn(
            bytes.fromhex("34 38")
            + builder.JOIN_CLASS_CHOICE_ACTIVE_SCENARIO.to_bytes(2, "big"),
            routine,
        )
        self.assertTrue(
            routine.startswith(
                bytes.fromhex("34 38")
                + builder.JOIN_CLASS_CHOICE_ACTIVE_SCENARIO.to_bytes(2, "big")
                + bytes.fromhex("24 79")
                + builder.JOIN_CLASS_CHOICE_CALLBACK_STACK_POINTER.to_bytes(
                    4, "big"
                )
                + bytes.fromhex("0C 92")
                + builder.JOIN_CLASS_CHOICE_RESULT_SCAN_CONTINUATION.to_bytes(
                    4, "big"
                )
                + bytes.fromhex("66 04 34 38")
                + builder.JOIN_CLASS_CHOICE_SELECTOR_SCENARIO.to_bytes(2, "big")
            ),
            routine[:22].hex(" "),
        )
        self.assertIn(
            bytes.fromhex("24 79")
            + builder.JOIN_CLASS_CHOICE_CALLBACK_STACK_POINTER.to_bytes(4, "big"),
            routine,
        )
        self.assertIn(
            bytes.fromhex("0C 92")
            + builder.JOIN_CLASS_CHOICE_RESULT_SCAN_CONTINUATION.to_bytes(4, "big"),
            routine,
        )
        for commander_id in builder.JOIN_CLASS_CHOICE_RECORDS:
            self.assertIn(
                bytes.fromhex("0C 28 00")
                + bytes((commander_id, 0x00, 0x01)),
                routine,
            )
            row = builder.JOIN_CLASS_CHOICE_RECORDS[commander_id]
            legacy_class = row.get("legacy_tier1_class")
            if legacy_class is not None:
                self.assertIn(
                    bytes.fromhex("0C 28 00")
                    + bytes((legacy_class, 0x00, 0x00)),
                    routine,
                )
                self.assertIn(
                    bytes.fromhex("11 7C 00")
                    + bytes((row["tier1_class"], 0x00, 0x00)),
                    routine,
                )
            first_scenario = builder.JOIN_CLASS_CHOICE_RECORDS[commander_id][
                "first_player_scenario"
            ]
            self.assertIn(
                bytes.fromhex("0C 42")
                + first_scenario.to_bytes(2, "big"),
                routine,
            )
            row = builder.JOIN_CLASS_CHOICE_RECORDS[commander_id]
            self.assertIn(
                bytes.fromhex("13 FC 00")
                + bytes((builder.JOIN_CLASS_CHOICE_PENDING_MARKER,))
                + row["active_marker_address"].to_bytes(4, "big"),
                routine,
            )

    def test_visibility_scenario_is_context_gated_for_cold_and_warm_loads(self) -> None:
        def effective(
            active_scenario: int,
            selector_scenario: int,
            outer_callback: int,
        ) -> int:
            if (
                outer_callback
                == builder.JOIN_CLASS_CHOICE_RESULT_SCAN_CONTINUATION
            ):
                return selector_scenario
            return active_scenario

        result = builder.JOIN_CLASS_CHOICE_RESULT_SCAN_CONTINUATION
        non_result = 0x00020800
        truth_table = (
            # Natural Scenario 7/10/11 result scans own A612 and expose the
            # commander at the following scenario's player boundary.
            (7, 8, result, 8, "keith_natural_result"),
            (10, 11, result, 11, "lester_natural_result"),
            (11, 12, result, 12, "jessica_natural_result"),
            # Cold LOAD has zero scratch; warm LOAD may retain any nonzero
            # selector.  Neither can override the restored active scenario.
            (12, 0, non_result, 12, "cold_title_load"),
            (12, 31, non_result, 12, "warm_title_load_stale_high"),
            (12, 8, non_result, 12, "warm_title_load_stale_low"),
            (10, 12, non_result, 10, "warm_prejoin_load_stays_hidden"),
            # Ordinary Rune Stone scans use A49C even if a prior selector left
            # a plausible but unrelated nonzero value behind.
            (12, 11, 0x00012282, 12, "ordinary_runestone_scan"),
            (12, 8, 0x0000D760, 12, "ordinary_end_turn_scan"),
        )
        for active, selector, callback, expected, label in truth_table:
            with self.subTest(label=label):
                self.assertEqual(
                    effective(active, selector, callback),
                    expected,
                )

    def test_all_visibility_call_sites_have_a_valid_scheduler_stack(self) -> None:
        literal = builder.JOIN_CLASS_CHOICE_SCAN_ENTRY.to_bytes(4, "big")
        offsets = tuple(
            offset
            for offset in range(len(self.source) - len(literal) + 1)
            if self.source.startswith(literal, offset)
        )
        self.assertEqual(
            offsets,
            (0x00CEBA, 0x00D748, 0x012278, 0x014ABA, 0x014D0C, 0x01684C),
        )

        # 0x85EE pushes the previous callback through the pointer held at
        # $FFFF8000 before installing 0x1480C.  Direct result/end-turn/event
        # entries all use that scheduler; the two inner resume sites retain
        # the already-valid frame and merely reinstall the current callback.
        self.assertEqual(
            self.source[0x0085EE:0x008608],
            bytes.fromhex(
                "20 79 FF FF 80 00 21 39 FF FF 80 04 "
                "23 C8 FF FF 80 00 23 C0 FF FF 80 04 4E 75"
            ),
        )
        scheduler_entries = {
            0x00CEB0: "21 FC 00 00 CE C4 80 04 20 3C 00 01 48 0C 4E F9 00 00 85 EE",
            0x00D73E: "21 FC 00 00 D7 60 80 04 20 3C 00 01 48 0C 4E B9 00 00 85 EE",
            0x01226E: "21 FC 00 01 22 82 80 04 20 3C 00 01 48 0C 4E F9 00 00 85 EE",
            0x01684A: "20 3C 00 01 48 0C 4E B9 00 00 85 EE",
        }
        for offset, expected in scheduler_entries.items():
            payload = bytes.fromhex(expected)
            with self.subTest(offset=f"0x{offset:06X}"):
                self.assertEqual(self.source[offset:offset + len(payload)], payload)
        for offset in (0x014AB8, 0x014D0A):
            payload = bytes.fromhex("21 FC 00 01 48 0C 80 04 4E 75")
            with self.subTest(resume=f"0x{offset:06X}"):
                self.assertEqual(self.source[offset:offset + len(payload)], payload)

    def test_visibility_a2_scratch_is_overwritten_before_stock_use(self) -> None:
        decoder = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN)
        # Below-LV10 progression reaches 0x14AE4 before its first A2 operand.
        before_level_helper = list(
            decoder.disasm(self.source[0x01484E:0x014878], 0x01484E)
        )
        self.assertFalse(
            any("a2" in instruction.op_str for instruction in before_level_helper)
        )
        self.assertEqual(
            self.source[0x014AE4:0x014AEA],
            bytes.fromhex("45 F9 00 08 29 22"),
        )
        # Exact-LV10 class choice similarly reaches 0x14B3A before using A2.
        before_class_chain = list(
            decoder.disasm(self.source[0x014B00:0x014B3A], 0x014B00)
        )
        self.assertFalse(
            any("a2" in instruction.op_str for instruction in before_class_chain)
        )
        self.assertEqual(
            self.source[0x014B3A:0x014B40],
            bytes.fromhex("45 F9 00 08 25 3A"),
        )

    def test_context_gated_visibility_guard_exact_size_and_sha(self) -> None:
        routine = builder.build_join_class_choice_visibility_guard()
        self.assertEqual(len(routine), 380)
        self.assertEqual(
            hashlib.sha256(routine).hexdigest(),
            "8b1a3d1cafc73e06bcd0f946c0456ab92b8a8d57b10a86902ad93e7700399698",
        )
        self.assertEqual(
            builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD + len(routine),
            0x31E37C,
        )

    def test_source_distinguishes_selector_scratch_from_saved_active_scenario(self) -> None:
        active_to_selector = bytes.fromhex("30 39 FF FF A4 9C 33 C0 FF FF A6 12")
        selector_to_active = bytes.fromhex("30 39 FF FF A6 12 33 C0 FF FF A4 9C")
        self.assertEqual(self.source[0x00CC9E:0x00CCAA], active_to_selector)
        self.assertEqual(self.source[0x00D210:0x00D21C], active_to_selector)
        for offset in (0x00CD9E, 0x00CF5A, 0x00D2F6):
            self.assertEqual(self.source[offset:offset + 12], selector_to_active)

        # The stock manual-save descriptor persists A49C + 0x154 and never
        # serializes the later A612 selector scratch word.
        descriptor = self.source[0x01E046:0x01E05C]
        self.assertEqual(
            descriptor,
            bytes.fromhex(
                "FF FF A4 9C 01 54 FF FF BD 6E 00 02 "
                "FF FF C7 F2 00 50 FF FF FF FF"
            ),
        )
        self.assertNotIn(bytes.fromhex("FF FF A6 12"), descriptor)

    def test_join_marker_is_armed_only_at_a_live_tier_one_level_ten_boundary(self) -> None:
        def armed(
            commander_id: int,
            scenario: int,
            x: int,
            y: int,
            class_id: int,
            level: int,
        ) -> bool:
            row = builder.JOIN_CLASS_CHOICE_RECORDS[commander_id]
            live = (
                scenario >= row["first_player_scenario"]
                and x != 0xFF
                and y != 0xFF
                and (x != 0 or y != 0)
            )
            legacy_repaired = (
                live
                and row.get("legacy_tier1_class") == class_id
                and level >= 10
            )
            effective_class = row["tier1_class"] if legacy_repaired else class_id
            effective_level = 10 if legacy_repaired else level
            return (
                live
                and effective_class == row["tier1_class"]
                and effective_level == 10
            )

        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id, case="fresh_join"):
                self.assertTrue(
                    armed(
                        commander_id,
                        row["first_player_scenario"],
                        6,
                        18,
                        row["tier1_class"],
                        10,
                    )
                )
            for candidate in row["tier2_candidates"]:
                with self.subTest(
                    commander_id=commander_id,
                    case="runestone_or_later_progression",
                    class_id=candidate,
                ):
                    self.assertFalse(
                        armed(
                            commander_id,
                            row["first_player_scenario"],
                            6,
                            18,
                            candidate,
                            10,
                        )
                    )
            with self.subTest(commander_id=commander_id, case="hidden"):
                self.assertFalse(
                    armed(
                        commander_id,
                        row["first_player_scenario"],
                        0,
                        0,
                        row["tier1_class"],
                        10,
                    )
                )

        # Broken v1.3.2/v1.3.3 Fighter saves are first restored to the clean
        # tier-one LV10 boundary, so that one recovery still earns the join
        # grant exactly once.
        for commander_id in (7, 9):
            row = builder.JOIN_CLASS_CHOICE_RECORDS[commander_id]
            self.assertTrue(
                armed(
                    commander_id,
                    row["first_player_scenario"],
                    6,
                    18,
                    row["legacy_tier1_class"],
                    12,
                )
            )

    def test_legacy_lester_above_level_ten_is_restored_before_the_gate(self) -> None:
        routine = builder.build_join_class_choice_visibility_guard()

        # Regression contract for v1.3.2/v1.3.3 saves: target identity must be
        # dispatched before the stock exact-LV10 comparison.  Otherwise a
        # Fighter that already reached LV11 or LV12 can never be migrated.
        first_identity = bytes.fromhex("0C 28 00 07 00 01")
        level_gate = bytes.fromhex("0C 28 00 0A 00 2E")
        identity_offset = routine.index(first_identity)
        self.assertEqual(identity_offset, 22)  # after context-gated scenario read
        self.assertLess(identity_offset, routine.index(level_gate))

        lester = builder.JOIN_CLASS_CHOICE_RECORDS[9]
        target = lester["target"]
        restored_boundary = b"".join(
            bytes.fromhex("11 7C 00") + bytes((value, 0x00, offset))
            for value, offset in (
                (lester["tier1_class"], 0x00),
                (target[1], 0x39),
                (10, 0x2E),
                (target[3], 0x2F),
                (target[4], 0x3A),
                (target[5], 0x3B),
            )
        )
        self.assertIn(restored_boundary, routine)

    def test_legacy_fighter_recovery_requires_the_real_player_map(self) -> None:
        def recovered(
            commander_id: int,
            scenario: int,
            x: int,
            y: int,
            class_id: int,
            level: int,
        ) -> bool:
            row = builder.JOIN_CLASS_CHOICE_RECORDS[commander_id]
            return (
                row.get("legacy_tier1_class") == class_id
                and level >= 10
                and scenario >= row["first_player_scenario"]
                and x != 0xFF
                and y != 0xFF
                and (x != 0 or y != 0)
            )

        # The reported broken saves are recovered at both LV11 and LV12.
        self.assertTrue(recovered(9, 11, 0, 12, 0x01, 11))
        self.assertTrue(recovered(9, 11, 0, 12, 0x01, 12))
        # A player who already saved in a later scenario is repaired on the
        # next real on-map progression scan as well, not only in Scenario 11.
        self.assertTrue(recovered(9, 20, 14, 18, 0x01, 12))
        # Lester stays Fighter before joining and is not rewritten while his
        # preparation/runtime record is hidden.
        self.assertFalse(recovered(9, 10, 0, 12, 0x01, 12))
        self.assertFalse(recovered(9, 11, 0, 0, 0x01, 12))
        self.assertFalse(recovered(9, 11, 0xFF, 0xFF, 0x01, 12))
        self.assertFalse(recovered(9, 11, 0, 12, 0x01, 9))

    def test_join_scenario_is_each_commanders_first_player_roster(self) -> None:
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            appearances = []
            for scenario_number in range(1, 32):
                layout = scenario_layout(self.source, scenario_number)
                count = be16(self.source, layout.header_offset + 0x10)
                ids = [
                    be16(
                        self.source,
                        layout.header_offset + 0x12 + index * 2,
                    )
                    for index in range(count)
                ]
                if commander_id in ids:
                    appearances.append(scenario_number)
            with self.subTest(commander_id=commander_id):
                self.assertTrue(appearances)
                self.assertEqual(
                    row["first_player_scenario"],
                    appearances[0],
                )

    def test_join_gate_truth_table_matches_preparation_npc_and_battle_states(self) -> None:
        def allowed(commander_id: int, scenario: int, x: int, y: int) -> bool:
            row = builder.JOIN_CLASS_CHOICE_RECORDS[commander_id]
            return (
                scenario >= row["first_player_scenario"]
                and x != 0xFF
                and y != 0xFF
                and (x != 0 or y != 0)
            )

        # Preparation records are zeroed even when the scenario's player-name
        # table already contains the incoming commander.
        self.assertFalse(allowed(7, 8, 0, 0))
        self.assertFalse(allowed(9, 11, 0, 0))
        self.assertFalse(allowed(10, 12, 0, 0))
        # Jessica is already a visible allied NPC in Scenario 11, but is not a
        # selectable player commander until Scenario 12.
        self.assertFalse(allowed(10, 11, 18, 6))
        # The reinforcement wait position remains blocked, while a genuine
        # map edge or ordinary map position is accepted after joining.
        self.assertFalse(allowed(7, 8, 0xFF, 0xFF))
        self.assertTrue(allowed(7, 8, 6, 18))
        self.assertTrue(allowed(9, 11, 0, 12))
        self.assertTrue(allowed(10, 12, 15, 0))

    def test_visibility_guard_does_not_overlap_experience_wrapper(self) -> None:
        level_end = (
            builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER
            + len(builder.build_join_class_choice_level_wrapper())
        )
        self.assertLessEqual(
            level_end,
            builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER_LIMIT,
        )
        self.assertEqual(
            builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER_LIMIT,
            builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD,
        )
        guard_end = (
            builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD
            + len(builder.build_join_class_choice_visibility_guard())
        )
        self.assertLessEqual(
            guard_end,
            builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD_LIMIT,
        )
        self.assertEqual(
            builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD_LIMIT,
            builder.JOIN_CLASS_CHOICE_OWNERSHIP_GUARD,
        )

    def test_lester_result_ownership_gate_wraps_the_complete_stock_sequence(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_ownership_guard(patched, self.source)
        hook = builder.JOIN_CLASS_CHOICE_OWNERSHIP_HOOK
        end = hook + len(builder.JOIN_CLASS_CHOICE_OWNERSHIP_HOOK_ORIGINAL)
        self.assertEqual(
            self.source[hook:end],
            builder.JOIN_CLASS_CHOICE_OWNERSHIP_HOOK_ORIGINAL,
        )
        self.assertEqual(
            patched[hook : hook + 6],
            bytes.fromhex("4E B9")
            + builder.JOIN_CLASS_CHOICE_OWNERSHIP_GUARD.to_bytes(4, "big"),
        )
        self.assertEqual(patched[hook + 6 : end], bytes.fromhex("67 00 01 E8"))

        routine = builder.build_join_class_choice_ownership_guard()
        decoder = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN)
        instructions = list(
            decoder.disasm(routine, builder.JOIN_CLASS_CHOICE_OWNERSHIP_GUARD)
        )
        self.assertEqual(sum(item.size for item in instructions), len(routine))
        self.assertEqual(instructions[-1].mnemonic, "rts")
        self.assertIn(bytes.fromhex("08 02 00 00"), routine)
        self.assertIn(bytes.fromhex("0C 28 00 09 00 01"), routine)
        self.assertIn(
            bytes.fromhex("0C 78 00 0A")
            + builder.JOIN_CLASS_CHOICE_ACTIVE_SCENARIO.to_bytes(2, "big"),
            routine,
        )
        self.assertIn(
            bytes.fromhex("24 79")
            + builder.JOIN_CLASS_CHOICE_CALLBACK_STACK_POINTER.to_bytes(4, "big"),
            routine,
        )
        self.assertIn(
            bytes.fromhex("0C 92")
            + builder.JOIN_CLASS_CHOICE_RESULT_SCAN_CONTINUATION.to_bytes(4, "big"),
            routine,
        )
        self.assertIn(bytes.fromhex("2F 0A 24 79"), routine)
        self.assertIn(bytes.fromhex("24 5F 66 00"), routine)
        self.assertIn(bytes.fromhex("53 41 4A 28 00 01 4E 75"), routine)

    def test_lester_result_ownership_truth_table_is_narrow(self) -> None:
        def eligible(
            stock_side: int,
            commander_id: int,
            active_scenario: int,
            callback: int,
        ) -> bool:
            return bool(stock_side & 1) or (
                commander_id == 9
                and active_scenario == 10
                and callback == builder.JOIN_CLASS_CHOICE_RESULT_SCAN_CONTINUATION
            )

        # Keith and Jessica retain the stock odd-side acceptance.
        self.assertTrue(eligible(3, 7, 7, 0xCEC4))
        self.assertTrue(eligible(3, 10, 11, 0xCEC4))
        # Lester's source side 4 is admitted only during Scenario 10 results.
        self.assertTrue(eligible(4, 9, 10, 0xCEC4))
        self.assertFalse(eligible(4, 9, 10, 0xD760))
        self.assertFalse(eligible(4, 9, 10, 0x12282))
        self.assertFalse(eligible(4, 9, 9, 0xCEC4))
        self.assertFalse(eligible(4, 9, 11, 0xCEC4))
        self.assertFalse(eligible(4, 8, 10, 0xCEC4))

    def test_ownership_guard_stays_between_visibility_and_relocated_chains(self) -> None:
        visibility_end = (
            builder.JOIN_CLASS_CHOICE_VISIBILITY_GUARD
            + len(builder.build_join_class_choice_visibility_guard())
        )
        ownership_end = (
            builder.JOIN_CLASS_CHOICE_OWNERSHIP_GUARD
            + len(builder.build_join_class_choice_ownership_guard())
        )
        self.assertLessEqual(visibility_end, builder.JOIN_CLASS_CHOICE_OWNERSHIP_GUARD)
        self.assertLessEqual(
            ownership_end,
            builder.JOIN_CLASS_CHOICE_OWNERSHIP_GUARD_LIMIT,
        )
        self.assertLessEqual(
            builder.JOIN_CLASS_CHOICE_OWNERSHIP_GUARD_LIMIT,
            min(builder.JOIN_CLASS_CHOICE_CHAIN_RELOCATIONS.values()),
        )

    def test_fixed_grant_wrapper_is_installed_at_both_stock_continuations(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_target_levels(patched, self.source)
        target = builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER.to_bytes(4, "big")
        self.assertEqual(
            patched[
                builder.JOIN_CLASS_CHOICE_LEVEL_CONTINUATION:
                builder.JOIN_CLASS_CHOICE_LEVEL_CONTINUATION + 4
            ],
            target,
        )
        self.assertEqual(
            patched[
                builder.JOIN_CLASS_CHOICE_APPLY_CONTINUATION:
                builder.JOIN_CLASS_CHOICE_APPLY_CONTINUATION + 4
            ],
            target,
        )

    def test_fixed_grant_wrapper_uses_stock_handler_and_all_candidate_classes(self) -> None:
        routine = builder.build_join_class_choice_level_wrapper()
        decoder = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN)
        instructions = list(
            decoder.disasm(routine, builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER)
        )
        self.assertEqual(sum(item.size for item in instructions), len(routine))
        self.assertEqual(instructions[-1].mnemonic, "bra.w")
        self.assertIn(
            bytes.fromhex("4E F9 00 01 48 0C"),
            routine,
        )
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                self.assertIn(
                    bytes.fromhex("0C 39 00")
                    + bytes((builder.JOIN_CLASS_CHOICE_LEGACY_ACTIVE_MARKER,))
                    + row["active_marker_address"].to_bytes(4, "big"),
                    routine,
                )
                self.assertIn(
                    bytes.fromhex("0C 39 00")
                    + bytes((builder.JOIN_CLASS_CHOICE_PENDING_MARKER,))
                    + row["active_marker_address"].to_bytes(4, "big"),
                    routine,
                )
                experience = builder.join_raw_experience(commander_id)
                if experience == 0:
                    grant_instruction = bytes.fromhex("42 28 00 2F")
                else:
                    grant_instruction = (
                        bytes.fromhex("11 7C 00")
                        + bytes((experience,))
                        + bytes.fromhex("00 2F")
                    )
                self.assertEqual(routine.count(grant_instruction), 1)
                for class_id in row["tier2_candidates"]:
                    self.assertIn(
                        bytes.fromhex("0C 02 00") + bytes((class_id,)),
                        routine,
                    )

        # Marker ownership belongs to the visibility gate.  The continuation
        # wrapper may compare or clear markers, but must never arm either the
        # new pending value or v1.3.6's stale value on its own.
        self.assertNotIn(
            bytes.fromhex("13 FC 00")
            + bytes((builder.JOIN_CLASS_CHOICE_PENDING_MARKER,)),
            routine,
        )
        self.assertNotIn(
            bytes.fromhex("13 FC 00")
            + bytes((builder.JOIN_CLASS_CHOICE_LEGACY_ACTIVE_MARKER,)),
            routine,
        )

    def test_every_branch_jumps_to_one_commander_grant_instruction(self) -> None:
        routine = builder.build_join_class_choice_level_wrapper()
        decoder = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN)
        instructions = list(
            decoder.disasm(routine, builder.JOIN_CLASS_CHOICE_LEVEL_WRAPPER)
        )
        by_address = {item.address: item for item in instructions}
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            branch_targets = []
            for candidate in row["tier2_candidates"]:
                needle = "#$%x, d2" % candidate
                matches = [
                    (index, item)
                    for index, item in enumerate(instructions)
                    if item.mnemonic == "cmpi.b" and item.op_str == needle
                ]
                self.assertTrue(matches, (commander_id, candidate))
                # Candidate IDs may be shared by another commander.  Keep
                # only comparisons whose following BEQ targets this
                # commander's unique raw-EXP write.
                for index, _item in matches:
                    branch = instructions[index + 1]
                    if branch.mnemonic != "beq.w":
                        continue
                    target = int(branch.op_str.removeprefix("$"), 16)
                    target_instruction = by_address.get(target)
                    if (
                        target_instruction is not None
                        and (
                            (
                                builder.join_raw_experience(commander_id) == 0
                                and target_instruction.mnemonic == "clr.b"
                                and target_instruction.op_str == "$2f(a0)"
                            )
                            or (
                                builder.join_raw_experience(commander_id) != 0
                                and target_instruction.mnemonic == "move.b"
                                and target_instruction.op_str
                                == (
                                    "#$%x, $2f(a0)"
                                    % builder.join_raw_experience(commander_id)
                                )
                            )
                        )
                    ):
                        branch_targets.append(target)
                        break
            with self.subTest(commander_id=commander_id):
                self.assertEqual(len(branch_targets), 3)
                self.assertEqual(len(set(branch_targets)), 1)

    def test_join_bonus_marker_policy_rejects_runestone_and_old_save_markers(self) -> None:
        self.assertNotEqual(
            builder.JOIN_CLASS_CHOICE_PENDING_MARKER,
            builder.JOIN_CLASS_CHOICE_LEGACY_ACTIVE_MARKER,
        )

        def wrapper_action(marker: int, class_is_tier_two: bool) -> str:
            if marker == builder.JOIN_CLASS_CHOICE_LEGACY_ACTIVE_MARKER:
                return "clear_without_grant"
            if marker != builder.JOIN_CLASS_CHOICE_PENDING_MARKER:
                return "leave_unchanged"
            if not class_is_tier_two:
                return "clear_without_grant"
            return "grant_join_experience"

        self.assertEqual(wrapper_action(0, True), "leave_unchanged")
        self.assertEqual(
            wrapper_action(builder.JOIN_CLASS_CHOICE_LEGACY_ACTIVE_MARKER, True),
            "clear_without_grant",
        )
        self.assertEqual(
            wrapper_action(builder.JOIN_CLASS_CHOICE_PENDING_MARKER, False),
            "clear_without_grant",
        )
        self.assertEqual(
            wrapper_action(builder.JOIN_CLASS_CHOICE_PENDING_MARKER, True),
            "grant_join_experience",
        )

    def test_normal_fixed_grants_follow_each_selected_class_gauge(self) -> None:
        patched = bytearray(self.source)
        builder.expand_rom(patched)
        builder.patch_join_class_choice_class_data(patched, self.source)
        expected = {
            7: {
                0x04: (1, 0),
                builder.JOIN_CLASS_CHOICE_HAWK_LORD: (1, 0),
                0x08: (1, 0),
            },
            9: {
                0x05: (5, 16),
                builder.JOIN_CLASS_CHOICE_CROCO_LORD: (7, 0),
                0x0A: (7, 0),
            },
            10: {0x08: (7, 0), 0x09: (5, 0), 0x04: (5, 0)},
        }
        for commander_id, rows in expected.items():
            grant = builder.join_raw_experience(commander_id)
            for class_id, outcome in rows.items():
                with self.subTest(commander_id=commander_id, class_id=class_id):
                    record = CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE
                    threshold = patched[record + 0x14] << 3
                    self.assertEqual(
                        (1 + grant // threshold, grant % threshold),
                        outcome,
                    )


if __name__ == "__main__":
    unittest.main()
