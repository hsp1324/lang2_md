import unittest
from pathlib import Path

from scripts import build_korean_jp_probe as builder
from tools.class_change_data import transition_for_class


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

    def test_stock_chains_offer_the_requested_tier_two_branches(self) -> None:
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                transition = transition_for_class(
                    self.source,
                    commander_id,
                    row["tier1_class"],
                )
                self.assertEqual(
                    transition.candidates,
                    row["tier2_candidates"],
                )

    def test_original_combat_stats_and_residual_experience_are_preserved(self) -> None:
        for commander_id, row in builder.JOIN_CLASS_CHOICE_RECORDS.items():
            with self.subTest(commander_id=commander_id):
                source = row["source"]
                target = row["target"]
                self.assertEqual(target[1], source[1])
                self.assertEqual(target[3:6], source[3:6])
                self.assertEqual(target[12:14], source[12:14])

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


if __name__ == "__main__":
    unittest.main()
