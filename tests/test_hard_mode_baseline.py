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

    def test_fixed_record_and_class_stat_ownership_is_source_locked(self):
        source = JP_ROM.read_bytes()
        model = self.inventory["source_model"]
        self.assertEqual(
            model["fixed_record_loader"],
            {
                "start": "0x010E46",
                "end": "0x010ED8",
                "commander_at_modifier_offset": "0x12",
                "commander_df_modifier_offset": "0x13",
                "value_encoding": "signed_byte",
            },
        )
        self.assertEqual(
            model["class_record_model"],
            {
                "table": "0x05EDDC",
                "record_size": 0x1C,
                "soldier_at_correction_offset": "0x0F",
                "soldier_df_correction_offset": "0x10",
                "scope": "global_per_class",
            },
        )
        self.assertEqual(
            source[
                hard_mode_baseline.FIXED_RECORD_LOADER:
                hard_mode_baseline.FIXED_RECORD_LOADER + 24
            ],
            bytes.fromhex(
                "23 58 00 08 23 58 00 14 23 58 00 20 "
                "23 58 00 2C 23 58 00 38 23 58 00 50"
            ),
        )
        self.assertEqual(
            source[0x010E84:0x010E9C],
            bytes.fromhex(
                "13 6A 00 0D 00 44 13 6A 00 0E 00 45 "
                "13 6A 00 0F 00 46 13 6A 00 10 00 47"
            ),
        )

    def test_known_scenario_one_stat_sources_are_not_conflated(self):
        records = self.inventory["scenarios"][0]["records"]
        bald = records[8]
        leon = records[9]
        self.assertEqual(
            (
                bald["class_id"],
                bald["commander_at_modifier"],
                bald["commander_df_modifier"],
                bald["soldier_at_correction"],
                bald["soldier_df_correction"],
            ),
            ("2E", 21, 18, 2, 0),
        )
        self.assertEqual(
            (
                leon["class_id"],
                leon["commander_at_modifier"],
                leon["commander_df_modifier"],
                leon["soldier_at_correction"],
                leon["soldier_df_correction"],
            ),
            ("45", 40, 31, 11, 8),
        )

    def test_hard_mode_rule_keeps_shared_class_records_immutable(self):
        rule = self.inventory["source_model"]["hard_mode_implementation_rule"]
        self.assertIn("fixed-record", rule["commander_stats"])
        self.assertIn("do not patch shared class records globally", rule["soldier_corrections"])
        self.assertIn("enemy-only expanded-ROM", rule["soldier_corrections"])
        self.assertIn("340 fixed records", rule["dynamic_event_spawns"])

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
