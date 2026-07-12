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
        scenarios = self.result["scenarios"]
        self.assertEqual(scenarios[0]["page_count"], 121)
        self.assertEqual(scenarios[0]["modified_page_count"], 121)
        self.assertEqual(scenarios[1]["page_count"], 110)
        self.assertEqual(scenarios[1]["modified_page_count"], 110)
        self.assertEqual(scenarios[2]["page_count"], 89)
        self.assertEqual(scenarios[2]["modified_page_count"], 89)
        self.assertEqual(scenarios[13]["modified_page_count"], 125)
        self.assertEqual(self.result["physical_page_count"], 3567)
        self.assertEqual(self.result["modified_physical_page_count"], 1143)
        self.assertEqual(scenarios[0]["physical_page_count"], 145)
        self.assertEqual(scenarios[0]["modified_physical_page_count"], 145)
        self.assertEqual(scenarios[1]["physical_page_count"], 137)
        self.assertEqual(scenarios[1]["modified_physical_page_count"], 137)
        self.assertEqual(scenarios[2]["physical_page_count"], 106)
        self.assertEqual(scenarios[2]["modified_physical_page_count"], 106)
        self.assertEqual(scenarios[13]["physical_page_count"], 162)
        self.assertEqual(scenarios[13]["modified_physical_page_count"], 162)
        self.assertEqual(scenarios[15]["page_count"], 87)
        self.assertEqual(scenarios[15]["modified_page_count"], 87)
        self.assertEqual(scenarios[15]["physical_page_count"], 98)
        self.assertEqual(scenarios[15]["modified_physical_page_count"], 98)
        self.assertEqual(scenarios[23]["page_count"], 53)
        self.assertEqual(scenarios[23]["modified_page_count"], 53)
        self.assertEqual(scenarios[23]["physical_page_count"], 65)
        self.assertEqual(scenarios[23]["modified_physical_page_count"], 65)
        self.assertEqual(scenarios[20]["page_count"], 71)
        self.assertEqual(scenarios[20]["modified_page_count"], 71)
        self.assertEqual(scenarios[20]["physical_page_count"], 80)
        self.assertEqual(scenarios[20]["modified_physical_page_count"], 80)
        self.assertEqual(scenarios[4]["page_count"], 79)
        self.assertEqual(scenarios[4]["modified_page_count"], 79)
        self.assertEqual(scenarios[4]["physical_page_count"], 87)
        self.assertEqual(scenarios[4]["modified_physical_page_count"], 87)
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
                if index not in (4, 13, 15, 20, 22, 23, 28, 29, 30)
            )
        )

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
