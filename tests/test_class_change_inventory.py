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
        self.assertEqual(self.result["live_verified_transition_count"], 6)
        self.assertEqual(self.result["live_verified_unique_transition_count"], 6)
        self.assertEqual(self.result["application_verified_transition_count"], 2)

        verified = [
            (commander["id"], transition)
            for commander in self.result["commanders"]
            for transition in commander["transitions"]
            if transition["live_verified"]
        ]
        self.assertEqual(len(verified), 6)
        commander_id, transition = verified[0]
        self.assertEqual(commander_id, 1)
        self.assertEqual(transition["current"]["id"], 1)
        self.assertEqual(
            [candidate["id"] for candidate in transition["candidates"]],
            [4, 5, 10],
        )
        self.assertTrue(transition["application_verified"])
        self.assertIn(
            "captures/analysis/eb00_class_change_turn2.gst",
            transition["evidence"],
        )

        commander_id, transition = verified[1]
        self.assertEqual(commander_id, 5)
        self.assertEqual(transition["current"]["id"], 0x03)
        self.assertEqual(
            [candidate["id"] for candidate in transition["candidates"]],
            [0x0A, 0x09, 0x04],
        )
        self.assertTrue(transition["application_verified"])
        self.assertIn(
            "captures/analysis/a8d7_c5_s03_after_turn.gst",
            transition["evidence"],
        )

        commander_id, transition = verified[2]
        self.assertEqual(commander_id, 5)
        self.assertEqual(transition["current"]["id"], 0x0A)
        self.assertEqual(
            [candidate["id"] for candidate in transition["candidates"]],
            [0x11, 0x12, 0x13],
        )
        self.assertFalse(transition["application_verified"])

        commander_id, transition = verified[3]
        self.assertEqual(commander_id, 5)
        self.assertEqual(transition["current"]["id"], 0x09)
        self.assertEqual(
            [candidate["id"] for candidate in transition["candidates"]],
            [0x12, 0x13, 0x0D],
        )
        self.assertFalse(transition["application_verified"])

        commander_id, transition = verified[4]
        self.assertEqual(commander_id, 5)
        self.assertEqual(transition["current"]["id"], 0x04)
        self.assertEqual(
            [candidate["id"] for candidate in transition["candidates"]],
            [0x13, 0x0D, 0x0B],
        )
        self.assertFalse(transition["application_verified"])

        commander_id, transition = verified[5]
        self.assertEqual(commander_id, 9)
        self.assertEqual(transition["current"]["id"], 0x10)
        self.assertEqual(
            [candidate["id"] for candidate in transition["candidates"]],
            [0x1D, 0x1F, 0x19],
        )
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
