import json
from pathlib import Path
import unittest

from tools.magic_flow_inventory import inventory, markdown_report


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
RUNTIME_INVENTORY = ROOT / "localization/runtime_verification.json"
INVENTORY_JSON = ROOT / "localization/magic_flow_inventory.json"
INVENTORY_MARKDOWN = ROOT / "docs/magic_flow_inventory.md"


class MagicFlowInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jp = JP_ROM.read_bytes()
        cls.ko = KO_ROM.read_bytes()
        cls.runtime = json.loads(
            RUNTIME_INVENTORY.read_text(encoding="utf-8")
        )
        cls.result = inventory(cls.jp, cls.ko, cls.runtime)

    def test_complete_scope_and_bounded_exception(self):
        scope = self.result["scope"]
        self.assertEqual(scope["magic_count"], 22)
        self.assertEqual(scope["source_natural_learnable_magic_count"], 21)
        self.assertEqual(scope["source_unreachable_magic_count"], 1)
        self.assertEqual(scope["source_unreachable_magic_ids"], [18])
        self.assertEqual(scope["diagnostic_application_evidence_count"], 22)
        self.assertEqual(scope["live_natural_learned_magic_count"], 11)
        self.assertEqual(scope["source_locked_range_count"], 9)

        teleport = self.result["magic"][18]
        self.assertEqual(teleport["name"], "텔레포트")
        self.assertEqual(teleport["owner_class_ids"], [0x25])
        self.assertEqual(teleport["natural_owner_class_ids"], [])
        self.assertEqual(teleport["natural_reachable_commander_ids"], [])
        self.assertFalse(teleport["natural_learnable"])
        self.assertIsNone(teleport["natural_witness"])
        self.assertEqual(teleport["fixed_scenario_owner_record_count"], 0)

    def test_every_reachable_magic_has_a_source_witness(self):
        for row in self.result["magic"]:
            if row["magic_id"] == 18:
                continue
            with self.subTest(magic_id=row["magic_id"]):
                self.assertTrue(row["natural_learnable"])
                witness = row["natural_witness"]
                self.assertIn(
                    witness["owner_class_id"],
                    witness["path_class_ids"],
                )
                self.assertIn(
                    witness["owner_class_id"],
                    row["natural_owner_class_ids"],
                )
                self.assertIn(
                    witness["commander_id"],
                    row["natural_reachable_commander_ids"],
                )
                self.assertLessEqual(row["required_level"], 9)

    def test_all_applications_match_source_mp_cost(self):
        expected_after = [
            11, 2, 8, 10, 4, 9, 10, 7, 0, 10, 8,
            9, 6, 10, 9, 10, 10, 6, 7, 10, 10, 6,
        ]
        for row, after in zip(self.result["magic"], expected_after):
            evidence = row["diagnostic_application"]
            with self.subTest(magic_id=row["magic_id"]):
                self.assertTrue(evidence["application_verified"])
                self.assertEqual(evidence["mp_before"], 12)
                self.assertEqual(evidence["mp_after"], after)
                self.assertEqual(
                    evidence["source_mp_cost"],
                    row["source_mp_cost"],
                )
                self.assertEqual(
                    (evidence["list_page"], evidence["list_row"]),
                    divmod(row["magic_id"], 6),
                )
                for key in (
                    "selected_capture",
                    "stable_capture",
                    "state",
                ):
                    self.assertTrue((ROOT / evidence[key]).is_file())

    def test_natural_evidence_is_exact(self):
        natural = self.result["natural_live_evidence"]
        self.assertEqual(natural["commander"], "헤인")
        self.assertEqual(natural["class"], "서머너")
        self.assertEqual(
            natural["learned_magic_ids"],
            [0, 1, 2, 4, 7, 10, 14, 16, 17, 19, 20],
        )
        self.assertEqual(natural["applied_magic_id"], 16)
        self.assertEqual((natural["mp_before"], natural["mp_after"]), (16, 14))
        self.assertTrue(natural["natural_application_verified"])

    def test_production_flow_is_source_equivalent(self):
        self.assertTrue(
            all(
                row["production_source_equivalent"]
                for row in self.result["source_locked_ranges"]
            )
        )
        self.assertEqual(
            self.result["control_flow"]["semantic_anchor_count"],
            23,
        )

    def test_source_lock_rejects_flow_mutation(self):
        mutated = bytearray(self.jp)
        mutated[0x021232] ^= 1
        with self.assertRaisesRegex(ValueError, "source range changed"):
            inventory(bytes(mutated), self.ko, self.runtime)

    def test_production_lock_rejects_flow_mutation(self):
        mutated = bytearray(self.ko)
        mutated[0x00EAC6] ^= 1
        with self.assertRaisesRegex(
            ValueError,
            "production logic/data differs from source",
        ):
            inventory(self.jp, bytes(mutated), self.runtime)

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
