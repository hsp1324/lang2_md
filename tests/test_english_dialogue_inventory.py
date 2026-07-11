from pathlib import Path
import json
import unittest

from tools.english_dialogue_inventory import classify_records


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
ENGLISH = ROOT / "script_extract/english_records.json"
MACHINE = ROOT / "script_extract/korean_records_google.json"


class EnglishDialogueInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = classify_records(
            JP_ROM.read_bytes(),
            json.loads(ENGLISH.read_text(encoding="utf-8")),
            json.loads(MACHINE.read_text(encoding="utf-8")),
        )

    def test_record_ownership_baseline_is_stable(self):
        self.assertEqual(self.result["record_count"], 3082)
        self.assertEqual(self.result["scenario_record_count"], 2978)
        self.assertEqual(self.result["outside_event_record_count"], 104)
        self.assertEqual(len(self.result["scenarios"]), 31)

    def test_scenario_14_is_one_contiguous_english_record_run(self):
        scenario = self.result["scenarios"][13]
        self.assertEqual(scenario["block_start"], "0x19C736")
        self.assertEqual(scenario["block_end"], "0x19EFA2")
        self.assertEqual(scenario["record_count"], 128)
        self.assertEqual(scenario["record_index_runs"], [[383, 510]])

    def test_branch_scenarios_preserve_disjoint_record_runs(self):
        scenario_11 = self.result["scenarios"][10]
        self.assertEqual(scenario_11["record_index_runs"], [[0, 94], [3079, 3081]])

    def test_prefix_is_documented_as_continuation_not_text_address(self):
        record = self.result["scenarios"][13]["records"][0]
        self.assertEqual(record["continuation_prefix"], "0x19C766")
        self.assertEqual(record["translation_status"], "reference_only")
        self.assertIn("not the Japanese text-page address", self.result["mapping_semantics"])


if __name__ == "__main__":
    unittest.main()
