import json
from pathlib import Path
import unittest

from tools.class_change_inventory import inventory, markdown_report


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
INVENTORY_JSON = ROOT / "localization/class_change_chains.json"
INVENTORY_MARKDOWN = ROOT / "docs/class_change_chain_inventory.md"


class ClassChangeInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inventory(JP_ROM.read_bytes())

    def test_source_baseline_and_live_scope(self):
        self.assertEqual(self.result["source_pointer_table"], "0x08253A")
        self.assertEqual(self.result["commander_count"], 10)
        self.assertEqual(self.result["transition_count"], 100)
        self.assertEqual(self.result["unique_transition_count"], 76)
        self.assertEqual(self.result["live_verified_transition_count"], 22)
        self.assertEqual(self.result["live_verified_unique_transition_count"], 22)
        self.assertEqual(self.result["application_verified_transition_count"], 2)

        verified = [
            (commander["id"], transition)
            for commander in self.result["commanders"]
            for transition in commander["transitions"]
            if transition["live_verified"]
        ]
        self.assertEqual(len(verified), 22)
        by_key = {
            (commander_id, transition["current"]["id"]): transition
            for commander_id, transition in verified
        }
        expected_candidates = {
            (1, 0x01): [0x04, 0x05, 0x0A],
            (2, 0x02): [0x0A, 0x08, 0x04],
            (2, 0x0A): [0x13, 0x0D, 0x11],
            (2, 0x08): [0x0D, 0x11, 0x12],
            (2, 0x04): [0x11, 0x12, 0x0B],
            (2, 0x13): [0x14, 0x1D, 0x19],
            (2, 0x0D): [0x1D, 0x19, 0x16],
            (2, 0x11): [0x19, 0x16, 0x15],
            (2, 0x12): [0x16, 0x15, 0x18],
            (2, 0x0B): [0x15, 0x18, 0x17],
            (2, 0x19): [0x28],
            (5, 0x03): [0x0A, 0x09, 0x04],
            (5, 0x0A): [0x11, 0x12, 0x13],
            (5, 0x09): [0x12, 0x13, 0x0D],
            (5, 0x04): [0x13, 0x0D, 0x0B],
            (5, 0x11): [0x16, 0x17, 0x15],
            (5, 0x12): [0x17, 0x15, 0x14],
            (5, 0x13): [0x15, 0x14, 0x18],
            (5, 0x0D): [0x14, 0x18, 0x19],
            (5, 0x0B): [0x18, 0x19, 0x1A],
            (5, 0x15): [0x28],
            (9, 0x10): [0x1D, 0x1F, 0x19],
        }
        self.assertEqual(set(by_key), set(expected_candidates))
        for key, candidates in expected_candidates.items():
            with self.subTest(key=key):
                self.assertEqual(
                    [
                        candidate["id"]
                        for candidate in by_key[key]["candidates"]
                    ],
                    candidates,
                )

        self.assertTrue(by_key[(1, 0x01)]["application_verified"])
        self.assertIn(
            "captures/analysis/eb00_class_change_turn2.gst",
            by_key[(1, 0x01)]["evidence"],
        )
        self.assertTrue(by_key[(5, 0x03)]["application_verified"])
        self.assertIn(
            "captures/analysis/a8d7_c5_s03_after_turn.gst",
            by_key[(5, 0x03)]["evidence"],
        )
        for key, transition in by_key.items():
            if key not in {(1, 0x01), (5, 0x03)}:
                self.assertFalse(transition["application_verified"])

    def test_generated_files_match(self):
        self.assertEqual(
            json.loads(INVENTORY_JSON.read_text(encoding="utf-8")), self.result
        )
        self.assertEqual(
            INVENTORY_MARKDOWN.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )


if __name__ == "__main__":
    unittest.main()
