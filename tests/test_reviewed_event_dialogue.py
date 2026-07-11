from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.jp_event_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class ReviewedEventDialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()
        cls.rows = builder.load_reviewed_event_translations(
            ROOT / "localization/event_dialogue_ko.json"
        )

    def test_scenario_14_intro_has_44_reviewed_pages(self):
        primary = [row for row in self.rows if not row.get("continuation")]
        continuations = [row for row in self.rows if row.get("continuation")]
        self.assertEqual(len(self.rows), 69)
        self.assertEqual(len(primary), 44)
        self.assertEqual(len(continuations), 25)
        self.assertTrue(all(row["scenario"] == 14 for row in self.rows))
        self.assertEqual(primary[0]["address"], "0x19CF7C")
        self.assertEqual(primary[-1]["address"], "0x19DFF8")
        self.assertEqual(
            [row["english_record"] for row in primary],
            [*range(385, 396), *range(397, 430)],
        )

    def test_dynamic_name_controls_and_terminators_are_preserved(self):
        for row in self.rows:
            address = int(row["address_int"])
            jp_capacity, jp_terminator, jp_controls = builder.event_page_layout(
                self.japanese, address
            )
            ko_capacity, ko_terminator, ko_controls = builder.event_page_layout(
                self.korean, address
            )
            self.assertEqual(ko_capacity, jp_capacity, row["address"])
            self.assertEqual(ko_terminator, jp_terminator, row["address"])
            self.assertEqual(ko_controls, jp_controls, row["address"])

    def test_only_declared_scenario_14_candidate_pages_changed(self):
        result = inventory(self.japanese, self.korean)
        scenario = result["scenarios"][13]
        modified = [page["address"] for page in scenario["pages"] if page["modified"]]
        declared = [row["address"] for row in self.rows if not row.get("continuation")]
        self.assertEqual(modified, declared)
        modified_physical = {
            physical["address"]
            for page in scenario["pages"]
            for physical in page["physical_pages"]
            if physical["modified"]
        }
        self.assertEqual(modified_physical, {row["address"] for row in self.rows})

    def test_live_verified_scenario_14_speaker_names_are_in_safe_patch_set(self):
        self.assertEqual(builder.DIRECT_STRING_PATCHES[0x97420], "쉐리")
        self.assertEqual(builder.DIRECT_STRING_PATCHES[0x97444], "아론")
        self.assertEqual(builder.DIRECT_STRING_PATCHES[0x9744E], "레스터")
        self.assertEqual(builder.DIRECT_STRING_PATCHES[0x97458], "제시카")
        for address in (0x97420, 0x97444, 0x9744E, 0x97458):
            capacity = builder.direct_string_capacity_words(self.japanese, address)
            self.assertEqual(
                builder.be16(self.korean, address + (capacity - 1) * 2),
                0xFFFF,
            )
            self.assertNotEqual(
                self.korean[address : address + capacity * 2],
                self.japanese[address : address + capacity * 2],
            )


if __name__ == "__main__":
    unittest.main()
