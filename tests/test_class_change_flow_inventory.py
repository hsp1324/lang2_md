import json
from pathlib import Path
import unittest

from tools.class_change_flow_inventory import (
    inventory,
    markdown_report,
)


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
INVENTORY_JSON = ROOT / "localization/class_change_flow_inventory.json"
INVENTORY_MARKDOWN = ROOT / "docs/class_change_flow_inventory.md"


class ClassChangeFlowInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()
        cls.result = inventory(cls.jp, cls.ko)

    def test_complete_structural_scope(self):
        scope = self.result["scope"]
        self.assertEqual(scope["source_transition_count"], 100)
        self.assertEqual(scope["unique_screen_combination_count"], 76)
        self.assertEqual(scope["live_verified_source_row_count"], 79)
        self.assertEqual(scope["live_verified_unique_screen_count"], 76)
        self.assertEqual(
            scope["representative_natural_application_commander_count"], 10
        )
        self.assertEqual(scope["ordinary_save_persistence_proof_count"], 5)
        self.assertEqual(
            scope["structurally_covered_application_transition_count"], 100
        )
        self.assertEqual(
            scope["structurally_covered_persistence_transition_count"], 100
        )

    def test_production_control_flow_is_source_equivalent(self):
        rows = self.result["source_locked_ranges"]
        self.assertEqual(len(rows), 8)
        self.assertTrue(
            all(row["production_source_equivalent"] for row in rows)
        )
        self.assertEqual(
            self.result["control_flow"]["runtime_record_count"], 20
        )
        self.assertEqual(
            self.result["control_flow"]["persistent_commander_count"], 10
        )

    def test_complete_roster_is_owned_by_manual_save_descriptor(self):
        descriptor = self.result["manual_save_descriptor"]
        self.assertTrue(descriptor["roster_wholly_inside_first_segment"])
        self.assertEqual(descriptor["persistent_roster_size"], 0xF0)
        self.assertEqual(
            [
                (row["work_ram_address"], row["size"])
                for row in descriptor["segments"]
            ],
            [
                ("0xFFFFA49C", 0x154),
                ("0xFFFFBD6E", 0x002),
                ("0xFFFFC7F2", 0x050),
            ],
        )

    def test_five_retained_saves_match_exact_progress(self):
        rows = self.result["ordinary_save_evidence"]
        self.assertEqual(
            [
                (
                    row["commander_id"],
                    row["class_id"],
                    row["level"],
                    row["experience"],
                    row["at"],
                    row["df"],
                    row["checksum"],
                )
                for row in rows
            ],
            [
                (1, 0x04, 1, 9, 23, 18, 0x211E),
                (5, 0x0A, 1, 17, 23, 13, 0x2330),
                (5, 0x11, 1, 1, 23, 14, 0x457A),
                (5, 0x15, 1, 9, 23, 15, 0xD8C2),
                (5, 0x28, 1, 9, 24, 16, 0xF52F),
            ],
        )

    def test_source_lock_rejects_control_flow_mutation(self):
        mutated = bytearray(self.jp)
        mutated[0x014C36] ^= 1
        with self.assertRaisesRegex(ValueError, "source range changed"):
            inventory(bytes(mutated), self.ko)

    def test_production_lock_rejects_undeclared_control_flow_mutation(self):
        mutated = bytearray(self.ko)
        mutated[0x014C36] ^= 1
        with self.assertRaisesRegex(
            ValueError,
            "production logic differs from source",
        ):
            inventory(self.jp, bytes(mutated))

    def test_generated_files_match(self):
        self.assertEqual(
            json.loads(INVENTORY_JSON.read_text(encoding="utf-8")),
            self.result,
        )
        self.assertEqual(
            INVENTORY_MARKDOWN.read_text(encoding="utf-8"),
            markdown_report(self.result),
        )


if __name__ == "__main__":
    unittest.main()
