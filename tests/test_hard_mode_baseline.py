from pathlib import Path
import hashlib
import subprocess
import sys
import unittest

from tools import hard_mode_baseline


ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
NORMAL_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class HardModeBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normal_before = NORMAL_ROM.read_bytes()
        cls.inventory = hard_mode_baseline.build_inventory(JP_ROM, NORMAL_ROM)

    def test_normal_release_is_locked_and_not_modified(self):
        normal = self.inventory["normal_release"]
        self.assertTrue(normal["immutable"])
        self.assertEqual(normal["header_checksum"], "99FD")
        self.assertEqual(
            normal["sha256"],
            "526237277c8f46a4400c00980da704e6ebea23e74d967d89b6d223db28dd54d3",
        )
        self.assertEqual(NORMAL_ROM.read_bytes(), self.normal_before)
        self.assertEqual(
            hashlib.sha256(NORMAL_ROM.read_bytes()).hexdigest(),
            normal["sha256"],
        )

    def test_approval_gate_forbids_implementation(self):
        gate = self.inventory["approval_gate"]
        self.assertEqual(
            self.inventory["status"],
            "balance_discussion_required",
        )
        self.assertFalse(gate["user_approved"])
        self.assertFalse(gate["implementation_started"])
        self.assertFalse(gate["rom_values_may_be_applied"])
        self.assertEqual(len(gate["required_decisions"]), 5)

    def test_all_source_records_have_addresses_and_six_mercenary_slots(self):
        scenarios = self.inventory["scenarios"]
        self.assertEqual([row["number"] for row in scenarios], list(range(1, 32)))
        self.assertEqual(sum(row["record_count"] for row in scenarios), 340)
        for scenario in scenarios:
            self.assertEqual(
                len(scenario["records"]),
                scenario["record_count"],
            )
            for record in scenario["records"]:
                self.assertRegex(record["offset"], r"^0x[0-9A-F]{6}$")
                self.assertEqual(len(record["mercenaries"]), 6)

    def test_known_side_distribution_and_scenario_22_exception(self):
        self.assertEqual(
            self.inventory["source_model"]["side_counts"],
            {"01": 1, "03": 35, "04": 292, "08": 12},
        )
        scenario_22 = self.inventory["scenarios"][21]
        self.assertEqual(
            scenario_22["side_counts"],
            {"03": 1, "04": 1, "08": 10},
        )
        self.assertEqual(scenario_22["enemy_summary"]["record_count"], 1)

    def test_checked_in_artifacts_are_current(self):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/hard_mode_baseline.py"),
                "--check",
            ],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
