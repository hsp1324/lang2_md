from pathlib import Path
import unittest

from tools import runtime_verification_inventory as inventory


ROOT = Path(__file__).resolve().parents[1]


class RuntimeVerificationInventoryTests(unittest.TestCase):
    def test_inventory_has_all_scenarios_and_surfaces(self):
        data = inventory.load_inventory()
        self.assertEqual(
            [entry["scenario"] for entry in data["scenarios"]],
            list(range(1, 32)),
        )
        for entry in data["scenarios"]:
            for surface in data["surfaces"]:
                self.assertIn(entry.get(surface, "pending"), data["states"])

    def test_current_evidence_matches_production_checksum(self):
        data = inventory.load_inventory()
        self.assertEqual(data["production_checksum"], "F0E3")
        scenario1 = data["scenarios"][0]
        scenario2 = data["scenarios"][1]
        scenario3 = data["scenarios"][2]
        scenario4 = data["scenarios"][3]
        scenario5 = data["scenarios"][4]
        scenario6 = data["scenarios"][5]
        scenario7 = data["scenarios"][6]
        scenario8 = data["scenarios"][7]
        scenario9 = data["scenarios"][8]
        scenario10 = data["scenarios"][9]
        scenario11 = data["scenarios"][10]
        scenario12 = data["scenarios"][11]
        scenario13 = data["scenarios"][12]
        scenario27 = data["scenarios"][26]
        self.assertEqual(scenario1["turn_events"], "verified_current")
        self.assertEqual(scenario2["opening_events"], "progressed_current")
        self.assertEqual(scenario3["description"], "verified_current")
        self.assertEqual(scenario3["turn_events"], "progressed_current")
        self.assertEqual(scenario4["opening_events"], "verified_current")
        self.assertEqual(scenario4["turn_events"], "progressed_current")
        self.assertEqual(scenario5["preparation"], "verified_current")
        self.assertEqual(scenario5["opening_events"], "verified_current")
        self.assertEqual(scenario6["conditions"], "verified_current")
        self.assertEqual(scenario6["battle_ui"], "verified_current")
        self.assertEqual(scenario6["turn_events"], "progressed_current")
        self.assertEqual(scenario7["opening_events"], "verified_current")
        self.assertEqual(scenario7["battle_ui"], "verified_current")
        self.assertEqual(scenario7["turn_events"], "progressed_current")
        self.assertEqual(scenario8["conditions"], "verified_current")
        self.assertEqual(scenario8["opening_events"], "verified_current")
        self.assertEqual(scenario8["turn_events"], "progressed_current")
        self.assertEqual(scenario9["description"], "verified_current")
        self.assertEqual(scenario9["conditions"], "verified_current")
        self.assertEqual(scenario9["preparation"], "verified_current")
        self.assertEqual(scenario9["opening_events"], "verified_current")
        self.assertEqual(scenario9["battle_ui"], "verified_current")
        self.assertEqual(scenario9["turn_events"], "progressed_current")
        self.assertEqual(scenario10["description"], "verified_current")
        self.assertEqual(scenario10["conditions"], "verified_current")
        self.assertEqual(scenario10["preparation"], "verified_current")
        self.assertEqual(scenario10["opening_events"], "verified_current")
        self.assertEqual(scenario10["battle_ui"], "verified_probe")
        self.assertEqual(scenario10["turn_events"], "progressed_current")
        self.assertEqual(scenario11["description"], "verified_current")
        self.assertEqual(scenario11["conditions"], "verified_current")
        self.assertEqual(scenario11["preparation"], "verified_current")
        self.assertEqual(scenario11["opening_events"], "verified_current")
        self.assertEqual(scenario11["battle_ui"], "verified_current")
        self.assertEqual(scenario11["turn_events"], "progressed_current")
        self.assertEqual(scenario12["description"], "verified_current")
        self.assertEqual(scenario12["conditions"], "verified_current")
        self.assertEqual(scenario12["preparation"], "verified_current")
        self.assertEqual(scenario12["opening_events"], "verified_current")
        self.assertEqual(scenario12["battle_ui"], "verified_current")
        self.assertEqual(scenario12["turn_events"], "progressed_current")
        self.assertEqual(scenario13["description"], "verified_current")
        self.assertEqual(scenario13["conditions"], "verified_current")
        self.assertEqual(scenario13["preparation"], "verified_current")
        self.assertEqual(scenario13["opening_events"], "verified_current")
        self.assertEqual(scenario13["battle_ui"], "verified_current")
        self.assertEqual(scenario13["turn_events"], "progressed_current")
        self.assertEqual(scenario27["preparation"], "verified_current")
        self.assertEqual(scenario27["completion"], "verified_probe")
        for evidence in data["global_evidence"]:
            self.assertIn(evidence["state"], data["states"])
            self.assertTrue(evidence["captures"])

    def test_generated_markdown_is_current(self):
        data = inventory.load_inventory()
        expected = inventory.render_markdown(data)
        actual = inventory.OUTPUT.read_text(encoding="utf-8")
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
