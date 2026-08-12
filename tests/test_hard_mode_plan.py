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
        if not NORMAL_ROM.is_file():
            raise unittest.SkipTest(
                "ignored legacy v1.0.0 normal reference ROM is absent; "
                "this suite audits the historical hard-mode plan, not the "
                "current v1.3.7 candidate"
            )
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

    def test_enemy_mercenary_sprite_cache_never_exceeds_engine_capacity(self):
        self.assertTrue(
            self.plan["implementation_policy"][
                "enemy_ordinary_mercenary_cache_reused"
            ]
        )
        self.assertEqual(
            self.plan["implementation_policy"][
                "enemy_dynamic_mercenary_cache_capacity"
            ],
            hard_mode_plan.MAX_DYNAMIC_ENEMY_MERCENARY_CLASSES,
        )
        for scenario in self.plan["scenarios"]:
            cache = scenario["enemy_mercenary_cache"]
            with self.subTest(scenario=scenario["number"]):
                self.assertTrue(
                    cache["ordinary_classes_reuse_fixed_cache"]
                )
                self.assertEqual(
                    cache["dynamic_class_count"],
                    len(cache["dynamic_class_ids"]),
                )
                self.assertLessEqual(
                    cache["dynamic_class_count"],
                    cache["dynamic_capacity"],
                )
        scenario_31 = next(
            row for row in self.plan["scenarios"] if row["number"] == 31
        )
        self.assertEqual(
            scenario_31["enemy_mercenary_cache"]["dynamic_class_ids"],
            [0x77, 0x7B, 0x7C, 0x88, 0x89],
        )

    def test_scenario_13_and_15_use_cache_safe_same_family_fallbacks(self):
        by_number = {
            row["number"]: row for row in self.plan["scenarios"]
        }
        scenario_13 = {
            row["offset"]: row for row in by_number[13]["records"]
        }
        self.assertEqual(
            scenario_13["0x181814"]["mercenaries"]["planned"],
            [0x63, 0x63, 0x7E, 0x7E, 0x7E, 0x7E],
        )
        self.assertEqual(
            scenario_13["0x1818C8"]["mercenaries"]["planned"],
            [0x73, 0x73, 0x73, 0x73, 0x7A, 0x7A],
        )
        scenario_15 = {
            row["offset"]: row for row in by_number[15]["records"]
        }
        self.assertEqual(
            scenario_15["0x181CCC"]["mercenaries"]["planned"],
            [0x6F, 0x6F, 0x82, 0x82, 0xFF, 0xFF],
        )
        self.assertEqual(
            by_number[13]["enemy_mercenary_cache"][
                "dynamic_class_count"
            ],
            10,
        )
        self.assertEqual(
            by_number[15]["enemy_mercenary_cache"][
                "dynamic_class_count"
            ],
            10,
        )

        catalog = {
            int(row["class_id"], 16): row
            for row in hard_mode_baseline.build_inventory(
                SOURCE_ROM,
                NORMAL_ROM,
            )["source_model"]["combat_class_catalog"]
        }
        for source_id, target_id in ((0x7E, 0x63), (0x82, 0x6F)):
            with self.subTest(
                source=f"0x{source_id:02X}",
                target=f"0x{target_id:02X}",
            ):
                source = catalog[source_id]
                target = catalog[target_id]
                self.assertEqual(
                    target["family_code"],
                    source["family_code"],
                )
                self.assertGreaterEqual(target["base_at"], source["base_at"])
                self.assertGreaterEqual(target["base_df"], source["base_df"])

    def test_summon_safe_fallback_changes_only_two_scenario_27_slots(self):
        self.assertEqual(
            self.plan["summary"]["summon_replacement_slot_count"],
            2,
        )
        self.assertTrue(
            self.plan["implementation_policy"]["summon_units_applied"]
        )
        self.assertFalse(
            self.plan["implementation_policy"][
                "fixed_summon_natural_magic_required"
            ]
        )
        changed = [
            (scenario["number"], record)
            for scenario in self.plan["scenarios"]
            for record in scenario["records"]
            if record["summon_replacement"]["planned"]
        ]
        self.assertEqual(len(changed), 1)
        scenario_number, record = changed[0]
        self.assertEqual(scenario_number, 27)
        self.assertEqual(record["offset"], "0x18321A")
        self.assertEqual(
            record["summon_replacement"]["changes"],
            [
                {
                    "slot": 4,
                    "source_class_id": 0x87,
                    "target_class_id": 0x8F,
                },
                {
                    "slot": 5,
                    "source_class_id": 0x87,
                    "target_class_id": 0x8F,
                },
            ],
        )
        self.assertEqual(
            record["mercenaries"]["original"],
            [0x89, 0x89, 0x89, 0x89, 0x87, 0x87],
        )
        self.assertEqual(
            record["mercenaries"]["planned"],
            [0x89, 0x89, 0x89, 0x89, 0x8F, 0x8F],
        )
        scenario_26 = next(
            row for row in self.plan["scenarios"] if row["number"] == 26
        )
        self.assertTrue(
            all(
                not record["summon_replacement"]["planned"]
                for record in scenario_26["records"]
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
