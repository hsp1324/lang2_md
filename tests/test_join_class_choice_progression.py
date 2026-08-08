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

    def test_custom_hawk_and_croco_lord_class_records_use_tier_movement(self) -> None:
        patched = bytearray(self.source)
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
                self.assertNotIn(
                    0x01,
                    tuple(
                        transition.current_class
                        for transition in read_class_change_chain(
                            patched, commander_id
                        )
                    ),
                )

    def test_identity_and_residual_experience_are_preserved(self) -> None:
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                source = row["source"]
                target = row["target"]
                self.assertEqual(target[3], source[3])
                self.assertEqual(target[12:14], source[12:14])

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
                bytes.fromhex("0C 78")
                + first_scenario.to_bytes(2, "big")
                + builder.JOIN_CLASS_CHOICE_CURRENT_SCENARIO.to_bytes(2, "big"),
                routine,
            )

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

    def test_tier_two_target_is_original_join_level_plus_three(self) -> None:
        expected = {7: 4, 10: 8}
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                self.assertEqual(row["join_level_bonus"], 3)
                self.assertEqual(
                    row["target_tier2_level"],
                    row["original_tier2_level"] + 3,
                )
                if row["experience_policy"] == "target_level":
                    self.assertEqual(
                        row["target_tier2_level"], expected[commander_id]
                    )

    def test_target_level_wrapper_is_installed_at_both_stock_continuations(self) -> None:
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

    def test_target_level_wrapper_uses_stock_handler_and_all_candidate_classes(self) -> None:
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
                    bytes.fromhex("13 FC 00 5A")
                    + row["active_marker_address"].to_bytes(4, "big"),
                    routine,
                )
                if row["experience_policy"] == "target_level":
                    self.assertIn(
                        bytes.fromhex("11 7C 00")
                        + bytes((row["residual_experience"],))
                        + bytes.fromhex("00 2F"),
                        routine,
                    )
                else:
                    for experience in row["fixed_experience_by_class"].values():
                        self.assertIn(
                            bytes.fromhex("11 7C 00")
                            + bytes((experience,))
                            + bytes.fromhex("00 2F"),
                            routine,
                        )
                for class_id in row["tier2_candidates"]:
                    self.assertIn(
                        bytes.fromhex("0C 02 00") + bytes((class_id,)),
                        routine,
                    )

    def test_experience_cap_is_refilled_until_every_target_level(self) -> None:
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            if row["experience_policy"] != "target_level":
                continue
            for class_id in row["tier2_candidates"]:
                with self.subTest(commander_id=commander_id, class_id=class_id):
                    record = CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE
                    threshold = self.source[record + 0x14] << 3
                    level = 1
                    experience = row["residual_experience"]
                    while level < row["target_tier2_level"]:
                        experience = 0xFF
                        self.assertGreaterEqual(experience, threshold)
                        experience -= threshold
                        level += 1
                    experience = row["residual_experience"]
                    self.assertEqual(level, row["target_tier2_level"])
                    self.assertEqual(experience, row["residual_experience"])

    def test_lester_fixed_grants_naturally_end_at_branch_specific_levels(self) -> None:
        patched = bytearray(self.source)
        builder.patch_join_class_choice_class_data(patched, self.source)
        row = builder.JOIN_CLASS_CHOICE_RECORDS[9]
        expected_levels = {
            0x05: 8,
            builder.JOIN_CLASS_CHOICE_CROCO_LORD: 8,
            0x0A: 9,
        }
        for class_id, grant in row["fixed_experience_by_class"].items():
            with self.subTest(class_id=class_id):
                record = CLASS_RECORD_TABLE + class_id * CLASS_RECORD_SIZE
                threshold = patched[record + 0x14] << 3
                level = 1
                experience = grant
                while experience >= threshold:
                    experience -= threshold
                    level += 1
                self.assertEqual(level, expected_levels[class_id])


if __name__ == "__main__":
    unittest.main()
