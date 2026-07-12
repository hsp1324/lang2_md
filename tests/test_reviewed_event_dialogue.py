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

    def test_scenario_14_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 14]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 162)
        self.assertEqual(len(primary), 125)
        self.assertEqual(len(continuations), 37)
        self.assertEqual(primary[0]["address"], "0x19CF7C")
        self.assertEqual(primary[-1]["address"], "0x19EF02")
        self.assertEqual(
            [row["english_record"] for row in primary],
            [*range(385, 396), *range(397, 511)],
        )

    def test_scenario_1_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 1]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 145)
        self.assertEqual(len(primary), 121)
        self.assertEqual(len(continuations), 24)
        self.assertEqual(primary[0]["address"], "0x184858")
        self.assertEqual(primary[-1]["address"], "0x18609C")
        # The English project split Japanese record 0x1849B4's second physical
        # page (0x1849DA) into its own record 2108.
        self.assertEqual(
            [row["english_record"] for row in primary],
            [*range(2101, 2108), *range(2109, 2223)],
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_2_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 2]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 137)
        self.assertEqual(len(primary), 110)
        self.assertEqual(len(continuations), 27)
        self.assertEqual(primary[0]["address"], "0x18688E")
        self.assertEqual(primary[-1]["address"], "0x1881A6")
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(1991, 2101)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_3_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 3]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 106)
        self.assertEqual(len(primary), 89)
        self.assertEqual(len(continuations), 17)
        self.assertEqual(primary[0]["address"], "0x188846")
        self.assertEqual(primary[-1]["address"], "0x189B64")
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(2223, 2312)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

    def test_scenario_31_has_all_reviewed_physical_pages(self):
        rows = [row for row in self.rows if row["scenario"] == 31]
        primary = [row for row in rows if not row.get("continuation")]
        continuations = [row for row in rows if row.get("continuation")]
        self.assertEqual(len(rows), 46)
        self.assertEqual(len(primary), 44)
        self.assertEqual(len(continuations), 2)
        self.assertEqual(primary[0]["address"], "0x1B87C2")
        self.assertEqual(primary[-1]["address"], "0x1B8D1A")
        # English record 1434 is a stray cross-scenario mapping. The 44
        # Japanese records align with the contiguous Death Tower run instead.
        self.assertEqual(
            [row["english_record"] for row in primary],
            list(range(1572, 1616)),
        )
        self.assertTrue(all("\n" not in row["text"] for row in rows))

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

    def test_declared_complete_scenarios_match_modified_pages(self):
        result = inventory(self.japanese, self.korean)
        for scenario_number in (1, 2, 3, 14, 31):
            rows = [row for row in self.rows if row["scenario"] == scenario_number]
            scenario = result["scenarios"][scenario_number - 1]
            modified = [page["address"] for page in scenario["pages"] if page["modified"]]
            declared = [row["address"] for row in rows if not row.get("continuation")]
            self.assertEqual(modified, declared)
            modified_physical = {
                physical["address"]
                for page in scenario["pages"]
                for physical in page["physical_pages"]
                if physical["modified"]
            }
            self.assertEqual(modified_physical, {row["address"] for row in rows})

    def test_live_reached_scenario_speaker_names_are_in_safe_patch_set(self):
        expected = {
            0x97420: "쉐리",
            0x97432: "스코트",
            0x97444: "아론",
            0x9744E: "레스터",
            0x97458: "제시카",
            0x97482: "발가스",
            0x974AA: "졸름",
            0x974B2: "에그베르트",
            0x97504: "지휘관",
            0x97526: "로렌",
        }
        for address, text in expected.items():
            self.assertEqual(builder.DIRECT_STRING_PATCHES[address], text)
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
