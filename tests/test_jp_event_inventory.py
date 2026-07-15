from pathlib import Path
import unittest

from tools.jp_event_inventory import event_block_starts, inventory


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean JP Probe).md"


class JapaneseEventInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()
        cls.result = inventory(cls.japanese, cls.korean)

    def test_event_pointer_table_has_31_ordered_blocks(self):
        starts = event_block_starts(self.japanese)
        self.assertEqual(len(starts), 31)
        self.assertEqual(starts[0], 0x18416A)
        self.assertEqual(starts[-1], 0x1B8378)

    def test_candidate_page_baseline_is_stable(self):
        self.assertEqual(self.result["page_count"], 2968)
        self.assertEqual(self.result["modified_page_count"], 2966)
        self.assertEqual(self.result["text_page_count"], 2966)
        self.assertEqual(self.result["modified_text_page_count"], 2966)
        self.assertEqual(self.result["structured_non_text_count"], 2)
        scenarios = self.result["scenarios"]
        self.assertEqual(scenarios[0]["page_count"], 121)
        self.assertEqual(scenarios[0]["modified_page_count"], 121)
        self.assertEqual(scenarios[1]["page_count"], 110)
        self.assertEqual(scenarios[1]["modified_page_count"], 110)
        self.assertEqual(scenarios[2]["page_count"], 89)
        self.assertEqual(scenarios[2]["modified_page_count"], 89)
        self.assertEqual(scenarios[13]["modified_page_count"], 125)
        self.assertEqual(self.result["physical_page_count"], 3567)
        self.assertEqual(self.result["modified_physical_page_count"], 3565)
        self.assertEqual(self.result["text_physical_page_count"], 3565)
        self.assertEqual(self.result["modified_text_physical_page_count"], 3565)
        self.assertEqual(scenarios[0]["physical_page_count"], 145)
        self.assertEqual(scenarios[0]["modified_physical_page_count"], 145)
        self.assertEqual(scenarios[1]["physical_page_count"], 137)
        self.assertEqual(scenarios[1]["modified_physical_page_count"], 137)
        self.assertEqual(scenarios[2]["physical_page_count"], 106)
        self.assertEqual(scenarios[2]["modified_physical_page_count"], 106)
        self.assertEqual(scenarios[3]["page_count"], 129)
        self.assertEqual(scenarios[3]["modified_page_count"], 129)
        self.assertEqual(scenarios[3]["physical_page_count"], 155)
        self.assertEqual(scenarios[3]["modified_physical_page_count"], 155)
        self.assertEqual(scenarios[13]["physical_page_count"], 162)
        self.assertEqual(scenarios[13]["modified_physical_page_count"], 162)
        self.assertEqual(scenarios[14]["page_count"], 110)
        self.assertEqual(scenarios[14]["modified_page_count"], 110)
        self.assertEqual(scenarios[14]["physical_page_count"], 118)
        self.assertEqual(scenarios[14]["modified_physical_page_count"], 118)
        self.assertEqual(scenarios[15]["page_count"], 87)
        self.assertEqual(scenarios[15]["modified_page_count"], 87)
        self.assertEqual(scenarios[15]["physical_page_count"], 98)
        self.assertEqual(scenarios[15]["modified_physical_page_count"], 98)
        self.assertEqual(scenarios[16]["page_count"], 108)
        self.assertEqual(scenarios[16]["modified_page_count"], 108)
        self.assertEqual(scenarios[16]["physical_page_count"], 135)
        self.assertEqual(scenarios[16]["modified_physical_page_count"], 135)
        self.assertEqual(scenarios[17]["page_count"], 95)
        self.assertEqual(scenarios[17]["modified_page_count"], 95)
        self.assertEqual(scenarios[17]["physical_page_count"], 117)
        self.assertEqual(scenarios[17]["modified_physical_page_count"], 117)
        self.assertEqual(scenarios[18]["page_count"], 98)
        self.assertEqual(scenarios[18]["modified_page_count"], 98)
        self.assertEqual(scenarios[18]["physical_page_count"], 116)
        self.assertEqual(scenarios[18]["modified_physical_page_count"], 116)
        self.assertEqual(scenarios[19]["page_count"], 88)
        self.assertEqual(scenarios[19]["modified_page_count"], 88)
        self.assertEqual(scenarios[19]["physical_page_count"], 111)
        self.assertEqual(scenarios[19]["modified_physical_page_count"], 111)
        self.assertEqual(scenarios[23]["page_count"], 53)
        self.assertEqual(scenarios[23]["modified_page_count"], 53)
        self.assertEqual(scenarios[23]["physical_page_count"], 65)
        self.assertEqual(scenarios[23]["modified_physical_page_count"], 65)
        self.assertEqual(scenarios[20]["page_count"], 71)
        self.assertEqual(scenarios[20]["modified_page_count"], 71)
        self.assertEqual(scenarios[20]["physical_page_count"], 80)
        self.assertEqual(scenarios[20]["modified_physical_page_count"], 80)
        self.assertEqual(scenarios[21]["page_count"], 151)
        self.assertEqual(scenarios[21]["modified_page_count"], 151)
        self.assertEqual(scenarios[21]["physical_page_count"], 191)
        self.assertEqual(scenarios[21]["modified_physical_page_count"], 191)
        self.assertEqual(scenarios[4]["page_count"], 79)
        self.assertEqual(scenarios[4]["modified_page_count"], 79)
        self.assertEqual(scenarios[4]["physical_page_count"], 87)
        self.assertEqual(scenarios[4]["modified_physical_page_count"], 87)
        self.assertEqual(scenarios[5]["page_count"], 102)
        self.assertEqual(scenarios[5]["modified_page_count"], 102)
        self.assertEqual(scenarios[5]["physical_page_count"], 122)
        self.assertEqual(scenarios[5]["modified_physical_page_count"], 122)
        self.assertEqual(scenarios[6]["page_count"], 101)
        self.assertEqual(scenarios[6]["modified_page_count"], 100)
        self.assertEqual(scenarios[6]["physical_page_count"], 118)
        self.assertEqual(scenarios[6]["modified_physical_page_count"], 117)
        self.assertEqual(scenarios[6]["text_page_count"], 100)
        self.assertEqual(scenarios[6]["modified_text_page_count"], 100)
        self.assertEqual(scenarios[6]["structured_non_text_count"], 1)
        self.assertEqual(scenarios[6]["text_physical_page_count"], 117)
        self.assertEqual(scenarios[6]["modified_text_physical_page_count"], 117)
        self.assertEqual(scenarios[7]["page_count"], 103)
        self.assertEqual(scenarios[7]["modified_page_count"], 103)
        self.assertEqual(scenarios[7]["physical_page_count"], 128)
        self.assertEqual(scenarios[7]["modified_physical_page_count"], 128)
        self.assertEqual(scenarios[8]["page_count"], 147)
        self.assertEqual(scenarios[8]["modified_page_count"], 147)
        self.assertEqual(scenarios[8]["physical_page_count"], 169)
        self.assertEqual(scenarios[8]["modified_physical_page_count"], 169)
        self.assertEqual(scenarios[9]["page_count"], 108)
        self.assertEqual(scenarios[9]["modified_page_count"], 108)
        self.assertEqual(scenarios[9]["physical_page_count"], 112)
        self.assertEqual(scenarios[9]["modified_physical_page_count"], 112)
        self.assertEqual(scenarios[10]["page_count"], 96)
        self.assertEqual(scenarios[10]["modified_page_count"], 96)
        self.assertEqual(scenarios[10]["physical_page_count"], 117)
        self.assertEqual(scenarios[10]["modified_physical_page_count"], 117)
        self.assertEqual(scenarios[11]["page_count"], 88)
        self.assertEqual(scenarios[11]["modified_page_count"], 88)
        self.assertEqual(scenarios[11]["physical_page_count"], 113)
        self.assertEqual(scenarios[11]["modified_physical_page_count"], 113)
        self.assertEqual(scenarios[12]["page_count"], 96)
        self.assertEqual(scenarios[12]["modified_page_count"], 96)
        self.assertEqual(scenarios[12]["physical_page_count"], 126)
        self.assertEqual(scenarios[12]["modified_physical_page_count"], 126)
        self.assertEqual(scenarios[24]["page_count"], 100)
        self.assertEqual(scenarios[24]["modified_page_count"], 99)
        self.assertEqual(scenarios[24]["physical_page_count"], 132)
        self.assertEqual(scenarios[24]["modified_physical_page_count"], 131)
        self.assertEqual(scenarios[24]["text_page_count"], 99)
        self.assertEqual(scenarios[24]["modified_text_page_count"], 99)
        self.assertEqual(scenarios[24]["structured_non_text_count"], 1)
        self.assertEqual(scenarios[24]["text_physical_page_count"], 131)
        self.assertEqual(scenarios[24]["modified_text_physical_page_count"], 131)
        self.assertEqual(scenarios[25]["page_count"], 71)
        self.assertEqual(scenarios[25]["modified_page_count"], 71)
        self.assertEqual(scenarios[25]["physical_page_count"], 102)
        self.assertEqual(scenarios[25]["modified_physical_page_count"], 102)
        self.assertEqual(scenarios[26]["page_count"], 97)
        self.assertEqual(scenarios[26]["modified_page_count"], 97)
        self.assertEqual(scenarios[26]["physical_page_count"], 126)
        self.assertEqual(scenarios[26]["modified_physical_page_count"], 126)
        self.assertEqual(scenarios[27]["page_count"], 104)
        self.assertEqual(scenarios[27]["modified_page_count"], 104)
        self.assertEqual(scenarios[27]["physical_page_count"], 116)
        self.assertEqual(scenarios[27]["modified_physical_page_count"], 116)
        self.assertEqual(scenarios[22]["page_count"], 83)
        self.assertEqual(scenarios[22]["modified_page_count"], 83)
        self.assertEqual(scenarios[22]["physical_page_count"], 92)
        self.assertEqual(scenarios[22]["modified_physical_page_count"], 92)
        self.assertEqual(scenarios[30]["page_count"], 44)
        self.assertEqual(scenarios[30]["modified_page_count"], 44)
        self.assertEqual(scenarios[30]["physical_page_count"], 46)
        self.assertEqual(scenarios[30]["modified_physical_page_count"], 46)
        self.assertEqual(scenarios[28]["page_count"], 49)
        self.assertEqual(scenarios[28]["modified_page_count"], 49)
        self.assertEqual(scenarios[28]["physical_page_count"], 55)
        self.assertEqual(scenarios[28]["modified_physical_page_count"], 55)
        self.assertEqual(scenarios[29]["page_count"], 65)
        self.assertEqual(scenarios[29]["modified_page_count"], 65)
        self.assertEqual(scenarios[29]["physical_page_count"], 70)
        self.assertEqual(scenarios[29]["modified_physical_page_count"], 70)
        self.assertTrue(
            all(
                item["modified_page_count"] == 0
                for index, item in enumerate(scenarios[3:], 3)
                if index not in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30)
            )
        )

    def test_scenario_7_structured_pointer_candidate_is_untouched(self):
        record = self.result["scenarios"][6]["pages"][0]
        self.assertEqual(record["address"], "0x18F610")
        self.assertEqual(record["source_refs"], ["0x18F358"])
        self.assertEqual(
            record["tokens"],
            "0202 0601 0019 0200 0201 0101 0019 020C 0202 0601 0019 0242 FFFF",
        )
        self.assertFalse(record["modified"])
        self.assertEqual(record["classification"], "structured_non_text")
        self.assertEqual(record["physical_pages"][0]["classification"], "structured_non_text")

    def test_scenario_25_structured_pointer_candidate_is_untouched(self):
        record = self.result["scenarios"][24]["pages"][0]
        self.assertEqual(record["address"], "0x1B0518")
        self.assertEqual(record["source_refs"], ["0x1B03E6"])
        self.assertEqual(
            record["tokens"],
            "0001 0001 001B 0544 0104 0002 001B 05E4 0204 0001 001B 05F4 0301 0002 001B 062A FFFF",
        )
        self.assertFalse(record["modified"])
        self.assertEqual(record["classification"], "structured_non_text")
        self.assertEqual(record["physical_pages"][0]["classification"], "structured_non_text")

    def test_regular_event_records_are_classified_as_text(self):
        record = self.result["scenarios"][0]["pages"][0]
        self.assertNotIn("classification", record)
        self.assertTrue(all("classification" not in page for page in record["physical_pages"]))

    def test_changed_structured_record_cannot_reuse_the_exclusion(self):
        changed = bytearray(self.japanese)
        changed[0x18F610:0x18F612] = (0x0203).to_bytes(2, "big")
        with self.assertRaisesRegex(ValueError, "known structured record changed at 0x18F610"):
            inventory(bytes(changed), self.korean)

    def test_first_known_page_and_terminator(self):
        first = self.result["scenarios"][0]["pages"][0]
        self.assertEqual(first["address"], "0x184858")
        self.assertEqual(first["terminator"], "0xFFFF")
        self.assertIn("0x18430E", first["source_refs"])

    def test_scenario_14_long_record_exposes_all_physical_pages(self):
        record = self.result["scenarios"][13]["pages"][5]
        self.assertEqual(record["address"], "0x19D020")
        self.assertEqual(record["physical_page_count"], 5)
        self.assertEqual(
            [page["address"] for page in record["physical_pages"]],
            ["0x19D020", "0x19D08C", "0x19D0E6", "0x19D13E", "0x19D17A"],
        )

    def test_last_record_follows_fffd_pages_to_first_ffff_only(self):
        record = self.result["scenarios"][13]["pages"][-1]
        self.assertEqual(
            [page["address"] for page in record["physical_pages"]],
            ["0x19EF02", "0x19EF3E"],
        )
        self.assertEqual(record["physical_pages"][-1]["terminator"], "0xFFFF")


if __name__ == "__main__":
    unittest.main()
