import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder
from tools.ending_credits_inventory import build_inventory


ROOT = Path(__file__).resolve().parents[1]


class EndingCreditsInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_inventory(
            (ROOT / builder.IN_ROM).read_bytes(),
            (ROOT / builder.OUT_ROM).read_bytes(),
            json.loads(
                (ROOT / "localization/runtime_verification.json").read_text(
                    encoding="utf-8"
                )
            ),
            json.loads(
                (ROOT / "localization/ui_patch_surfaces.json").read_text(
                    encoding="utf-8"
                )
            ),
        )

    def test_full_ending_inventory_is_complete(self):
        self.assertTrue(self.result["complete"])
        self.assertEqual(self.result["ending_slot_count"], 16)

    def test_every_credit_record_is_referenced_once(self):
        sequences = self.result["credits"]["sequence_inventory"]
        self.assertEqual(sequences["source_record_ids"], list(range(60)))
        self.assertEqual(sequences["production_record_ids"], list(range(61)))
        self.assertEqual(sequences["final_sequence_record_ids"], [59, 60])

    def test_all_ending_text_resources_are_counted(self):
        self.assertEqual(self.result["ending_montage"]["record_count"], 12)
        self.assertEqual(self.result["epilogues"]["record_count"], 90)
        self.assertEqual(self.result["epilogues"]["page_count"], 515)
        self.assertEqual(self.result["ending_visits"]["record_count"], 23)
        self.assertEqual(self.result["ending_visits"]["page_count"], 83)

    def test_runtime_evidence_covers_complete_flow_and_visits(self):
        evidence = self.result["runtime_evidence"]
        self.assertIn(
            evidence["complete_ending_credits"]["state"],
            {"verified_current", "verified_probe"},
        )
        self.assertIn(
            evidence["ending_visit_dialogue"]["state"],
            {"verified_current", "verified_probe"},
        )


if __name__ == "__main__":
    unittest.main()
