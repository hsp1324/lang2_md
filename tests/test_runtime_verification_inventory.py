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
        self.assertEqual(data["production_checksum"], "C7AB")
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
        scenario14 = data["scenarios"][13]
        scenario15 = data["scenarios"][14]
        scenario16 = data["scenarios"][15]
        scenario17 = data["scenarios"][16]
        scenario18 = data["scenarios"][17]
        scenario19 = data["scenarios"][18]
        scenario20 = data["scenarios"][19]
        scenario21 = data["scenarios"][20]
        scenario22 = data["scenarios"][21]
        scenario23 = data["scenarios"][22]
        scenario27 = data["scenarios"][26]
        scenario31 = data["scenarios"][30]
        self.assertEqual(scenario1["description"], "verified_current")
        self.assertIn("captures/run/c7ab_s01_body_name4.png", scenario1["captures"])
        current_description_progress = {*range(2, 14), 15, *range(22, 32)}
        for scenario in data["scenarios"][1:]:
            expected = (
                "progressed_current"
                if scenario["scenario"] in current_description_progress
                else "historical"
            )
            self.assertEqual(scenario["description"], expected)
        self.assertEqual(scenario27["description"], "progressed_current")
        self.assertEqual(scenario1["turn_events"], "verified_current")
        self.assertIn("captures/run/c7ab_s02_body_final2.png", scenario2["captures"])
        self.assertEqual(scenario2["opening_events"], "progressed_current")
        self.assertEqual(scenario3["description"], "progressed_current")
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
        self.assertEqual(scenario9["description"], "progressed_current")
        self.assertEqual(scenario9["conditions"], "verified_current")
        self.assertEqual(scenario9["preparation"], "verified_current")
        self.assertEqual(scenario9["opening_events"], "verified_current")
        self.assertEqual(scenario9["battle_ui"], "verified_current")
        self.assertEqual(scenario9["turn_events"], "progressed_current")
        self.assertEqual(scenario10["description"], "progressed_current")
        self.assertEqual(scenario10["conditions"], "verified_current")
        self.assertEqual(scenario10["preparation"], "verified_current")
        self.assertEqual(scenario10["opening_events"], "verified_current")
        self.assertEqual(scenario10["battle_ui"], "verified_probe")
        self.assertEqual(scenario10["turn_events"], "progressed_current")
        self.assertEqual(scenario11["description"], "progressed_current")
        self.assertEqual(scenario11["conditions"], "verified_current")
        self.assertEqual(scenario11["preparation"], "verified_current")
        self.assertEqual(scenario11["opening_events"], "verified_current")
        self.assertEqual(scenario11["battle_ui"], "verified_current")
        self.assertEqual(scenario11["turn_events"], "progressed_current")
        self.assertEqual(scenario12["description"], "progressed_current")
        self.assertIn("captures/run/c7ab_s12_body_final2.png", scenario12["captures"])
        self.assertEqual(scenario12["conditions"], "verified_current")
        self.assertEqual(scenario12["preparation"], "verified_current")
        self.assertEqual(scenario12["opening_events"], "verified_current")
        self.assertEqual(scenario12["battle_ui"], "verified_current")
        self.assertEqual(scenario12["turn_events"], "progressed_current")
        self.assertEqual(scenario13["description"], "progressed_current")
        self.assertIn("captures/run/c7ab_s13_title.png", scenario13["captures"])
        self.assertEqual(scenario13["conditions"], "verified_current")
        self.assertEqual(scenario13["preparation"], "verified_current")
        self.assertEqual(scenario13["opening_events"], "verified_current")
        self.assertEqual(scenario13["battle_ui"], "verified_current")
        self.assertEqual(scenario13["turn_events"], "progressed_current")
        self.assertEqual(scenario14["description"], "historical")
        self.assertEqual(scenario14["conditions"], "verified_current")
        self.assertEqual(scenario14["preparation"], "verified_current")
        self.assertEqual(scenario14["opening_events"], "verified_current")
        self.assertEqual(scenario14["battle_ui"], "verified_probe")
        self.assertEqual(scenario14["turn_events"], "progressed_current")
        self.assertEqual(scenario15["description"], "progressed_current")
        self.assertIn("captures/run/c7ab_s15_title.png", scenario15["captures"])
        self.assertEqual(scenario15["conditions"], "verified_current")
        self.assertEqual(scenario15["preparation"], "verified_current")
        self.assertEqual(scenario15["opening_events"], "verified_current")
        self.assertEqual(scenario15["battle_ui"], "verified_probe")
        self.assertEqual(scenario15["turn_events"], "progressed_current")
        self.assertEqual(scenario16["description"], "historical")
        self.assertEqual(scenario16["conditions"], "verified_current")
        self.assertEqual(scenario16["preparation"], "verified_current")
        self.assertEqual(scenario16["opening_events"], "verified_current")
        self.assertEqual(scenario16["battle_ui"], "verified_probe")
        self.assertEqual(scenario16["turn_events"], "progressed_current")
        self.assertEqual(scenario17["description"], "historical")
        self.assertEqual(scenario17["conditions"], "verified_current")
        self.assertEqual(scenario17["preparation"], "verified_current")
        self.assertEqual(scenario17["opening_events"], "verified_current")
        self.assertEqual(scenario17["battle_ui"], "verified_current")
        self.assertEqual(scenario17["turn_events"], "progressed_current")
        self.assertEqual(scenario18["description"], "historical")
        self.assertEqual(scenario18["conditions"], "verified_current")
        self.assertEqual(scenario18["preparation"], "verified_current")
        self.assertEqual(scenario18["opening_events"], "verified_current")
        self.assertEqual(scenario18["battle_ui"], "verified_probe")
        self.assertEqual(scenario18["turn_events"], "progressed_current")
        self.assertEqual(scenario19["description"], "historical")
        self.assertEqual(scenario19["conditions"], "verified_current")
        self.assertEqual(scenario19["preparation"], "verified_current")
        self.assertEqual(scenario19["opening_events"], "verified_current")
        self.assertEqual(scenario19["battle_ui"], "verified_probe")
        self.assertEqual(scenario19["turn_events"], "progressed_current")
        self.assertEqual(scenario20["description"], "historical")
        self.assertEqual(scenario20["conditions"], "verified_current")
        self.assertEqual(scenario20["preparation"], "verified_current")
        self.assertEqual(scenario20["opening_events"], "verified_current")
        self.assertEqual(scenario20["battle_ui"], "verified_probe")
        self.assertEqual(scenario20["turn_events"], "progressed_current")
        self.assertEqual(scenario21["description"], "historical")
        self.assertEqual(scenario21["conditions"], "verified_current")
        self.assertEqual(scenario21["preparation"], "verified_current")
        self.assertEqual(scenario21["opening_events"], "verified_current")
        self.assertEqual(scenario21["battle_ui"], "verified_probe")
        self.assertEqual(scenario21["turn_events"], "progressed_current")
        self.assertEqual(scenario22["description"], "progressed_current")
        self.assertIn("captures/run/c7ab_s22_body_final2.png", scenario22["captures"])
        self.assertEqual(scenario22["preparation"], "pending")
        self.assertEqual(scenario22["opening_events"], "pending")
        self.assertEqual(scenario23["description"], "progressed_current")
        self.assertIn("captures/run/c7ab_s23_title.png", scenario23["captures"])
        self.assertEqual(scenario27["preparation"], "verified_current")
        self.assertEqual(scenario27["completion"], "verified_probe")
        self.assertIn("captures/run/c7ab_s27_body_final2.png", scenario27["captures"])
        self.assertEqual(scenario31["description"], "progressed_current")
        self.assertIn("captures/run/c7ab_s31_body_final2.png", scenario31["captures"])
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
