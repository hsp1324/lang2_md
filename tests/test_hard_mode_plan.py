from pathlib import Path
import hashlib
import json
import subprocess
import sys
import unittest

from tools import hard_mode_baseline
from tools import hard_mode_plan


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
NORMAL_ROM = ROOT / "roms/releases/Langrisser II (Korean v1.0.0).md"


class HardModePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normal_before = NORMAL_ROM.read_bytes()
        cls.plan = hard_mode_plan.build_plan(SOURCE_ROM, NORMAL_ROM)

    def test_plan_is_non_writing_and_records_current_approval(self):
        self.assertEqual(
            self.plan["status"],
            "approved_balance_plan",
        )
        self.assertEqual(self.plan["approval"]["status"], "approved")
        self.assertFalse(self.plan["rom_values_applied"])
        self.assertTrue(
            self.plan["implementation_policy"]["normal_release_immutable"]
        )
        self.assertFalse(
            self.plan["implementation_policy"]["shared_class_records_modified"]
        )
        self.assertEqual(NORMAL_ROM.read_bytes(), self.normal_before)
        self.assertEqual(
            hashlib.sha256(NORMAL_ROM.read_bytes()).hexdigest(),
            hard_mode_baseline.NORMAL_SHA256,
        )

    def test_plan_covers_all_scenarios_and_expected_targets(self):
        self.assertEqual(
            [row["number"] for row in self.plan["scenarios"]],
            list(range(1, 32)),
        )
        self.assertEqual(
            self.plan["summary"]["target_record_count"],
            300,
        )
        self.assertEqual(
            sum(
                row["target_record_count"]
                for row in self.plan["scenarios"]
            ),
            300,
        )

    def test_late_game_curve_requires_runestone_growth(self):
        expectation = self.plan["implementation_policy"][
            "runestone_expectation"
        ]
        self.assertIn("없이도", expectation["scenarios_1_15"])
        self.assertIn("누적 1개", expectation["scenarios_16_20"])
        self.assertIn("누적 1~2개", expectation["scenarios_21_24"])
        self.assertIn("누적 2개", expectation["scenarios_25_27"])
        budget = self.plan["implementation_policy"]["runestone_budget"]
        self.assertEqual(budget["scope"], "party_total_not_per_character")
        self.assertEqual(budget["required_party_total_cap"], 2)
        self.assertFalse(budget["optional_or_hidden_extra_required"])
        self.assertFalse(budget["all_commanders_retrained_required"])

        formulas = {
            scenario["number"]: scenario["formula"]
            for scenario in self.plan["scenarios"]
        }
        self.assertEqual(
            (
                formulas[15]["commander_at_delta"],
                formulas[16]["commander_at_delta"],
                formulas[21]["commander_at_delta"],
                formulas[25]["commander_at_delta"],
                formulas[26]["commander_at_delta"],
                formulas[27]["commander_at_delta"],
            ),
            (5, 8, 11, 13, 15, 17),
        )
        self.assertEqual(
            formulas[27]["stronger_mercenary_slots_per_six"],
            6,
        )

    def test_known_exclusions_are_not_targets(self):
        offsets = {
            record["offset"]
            for scenario in self.plan["scenarios"]
            for record in scenario["records"]
        }
        self.assertFalse(
            set(hard_mode_baseline.MAIN_STORY_AUTOMATIC_EXCLUDED_OFFSETS)
            & offsets
        )
        self.assertNotIn("0x182D62", offsets)
        self.assertNotIn("0x183902", offsets)

    def test_scenario_one_only_strengthens_real_ordinary_enemies(self):
        scenario = self.plan["scenarios"][0]
        self.assertEqual(
            [row["offset"] for row in scenario["records"]],
            ["0x1802D8", "0x180344"],
        )
        self.assertEqual(
            [
                (
                    row["commander"]["at"]["original"],
                    row["commander"]["at"]["planned"],
                    row["commander"]["df"]["original"],
                    row["commander"]["df"]["planned"],
                )
                for row in scenario["records"]
            ],
            [(21, 23, 18, 19), (19, 21, 18, 19)],
        )

    def test_shared_class_table_is_not_a_planned_write(self):
        for scenario in self.plan["scenarios"]:
            for row in scenario["records"]:
                self.assertIn(
                    "expanded-ROM per-record table",
                    row["enemy_soldier_correction"]["implementation"],
                )

    def test_runtime_rewrite_exceptions_have_a_separate_audited_manifest(self):
        relative_path = self.plan["implementation_policy"][
            "runtime_exception_manifest"
        ]
        manifest = json.loads(
            (ROOT / relative_path).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["status"], "runtime_audited")
        self.assertEqual(
            [
                (
                    row["scenario"],
                    row["fixed_record_index"],
                    row["fixed_record_offset"],
                    row["name_korean"],
                )
                for row in manifest["exceptions"]
            ],
            [(10, 1, "0x1811DE", "레스터")],
        )
        exception = manifest["exceptions"][0]
        self.assertEqual(
            set(exception["runtime_overridden_fields"]),
            {
                "commander_at",
                "commander_df",
                "soldier_at",
                "soldier_df",
            },
        )
        for key in ("gst", "capture"):
            evidence_path = ROOT / exception["retained_evidence"][key]
            self.assertTrue(evidence_path.is_file())
            self.assertEqual(
                hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                exception["retained_evidence"][f"{key}_sha256"],
            )

    def test_mercenary_changes_never_fill_empty_slots(self):
        for scenario in self.plan["scenarios"]:
            quota = scenario["formula"][
                "stronger_mercenary_slots_per_six"
            ]
            for row in scenario["records"]:
                original = row["mercenaries"]["original"]
                planned = row["mercenaries"]["planned"]
                self.assertLessEqual(
                    len(row["mercenaries"]["changes"]),
                    quota,
                )
                for before, after in zip(original, planned):
                    if before == 0xFF:
                        self.assertEqual(after, 0xFF)

    def test_summons_remain_deferred_until_runtime_guards_pass(self):
        self.assertEqual(
            self.plan["summary"]["summon_replacement_slot_count"],
            0,
        )
        self.assertFalse(
            self.plan["implementation_policy"]["summon_units_applied"]
        )
        self.assertTrue(
            all(
                not record["summon_replacement"]["planned"]
                for scenario in self.plan["scenarios"]
                for record in scenario["records"]
            )
        )

    def test_secret_scenarios_use_explicit_band_mapping(self):
        by_number = {
            row["number"]: row for row in self.plan["scenarios"]
        }
        self.assertEqual(
            {
                number: by_number[number]["mapped_from_scenario"]
                for number in range(28, 32)
            },
            {28: 11, 29: 16, 30: 21, 31: 27},
        )
        for record in by_number[31]["records"]:
            self.assertGreaterEqual(
                record["commander"]["at"]["planned"],
                record["commander"]["at"]["original"],
            )
            self.assertGreaterEqual(
                record["commander"]["df"]["planned"],
                record["commander"]["df"]["original"],
            )

    def test_checked_in_plan_and_change_log_are_current(self):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.hard_mode_plan",
                "--check",
            ],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
