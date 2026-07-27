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

    def test_discussion_choices_remain_unselected(self):
        discussion = self.inventory["balance_discussion"]
        self.assertEqual(
            discussion["user_selections"],
            {
                "difficulty_target": None,
                "scenario_band_policy": None,
                "enemy_commander_and_soldier_formula": None,
                "stronger_mercenary_policy": None,
                "late_summon_unit_policy": None,
                "exception_policy": None,
            },
        )
        options = discussion["difficulty_options"]
        self.assertEqual(
            [option["id"] for option in options],
            ["standard_hard", "high_difficulty", "extreme"],
        )
        self.assertEqual(
            [option["recommended"] for option in options],
            [True, False, False],
        )

    def test_candidate_scenario_bands_cover_every_scenario_once(self):
        bands = self.inventory["balance_discussion"]["candidate_scenario_bands"]
        self.assertEqual(
            [(band["label"], band["scenarios"]) for band in bands],
            [
                ("초반", [1, 2, 3, 4, 5]),
                ("전반", [6, 7, 8, 9, 10]),
                ("중반", [11, 12, 13, 14, 15]),
                ("후반", [16, 17, 18, 19, 20]),
                ("종반", [21, 22, 23, 24, 25, 26, 27]),
                ("비밀", [28, 29, 30, 31]),
            ],
        )
        self.assertEqual(
            sorted(number for band in bands for number in band["scenarios"]),
            list(range(1, 32)),
        )
        self.assertTrue(all(not band["user_approved"] for band in bands))

    def test_candidate_band_original_aggregate_is_stable(self):
        bands = {
            band["id"]: band["original_side_04_summary"]
            for band in self.inventory["balance_discussion"][
                "candidate_scenario_bands"
            ]
        }
        self.assertEqual(
            {
                band_id: (
                    row["record_count"],
                    row["hidden_record_count"],
                    row["side_08_record_count"],
                    row["filled_mercenary_slots"],
                )
                for band_id, row in bands.items()
            },
            {
                "opening": (33, 10, 0, 174),
                "early_campaign": (51, 14, 0, 270),
                "mid_campaign": (56, 10, 0, 300),
                "late_campaign": (50, 11, 0, 286),
                "endgame": (64, 7, 11, 370),
                "secret": (38, 1, 1, 226),
            },
        )
        self.assertEqual(
            bands["opening"]["commander_at_modifier"],
            {"minimum": 19, "maximum": 40, "mean": 23.6},
        )
        self.assertEqual(
            bands["endgame"]["commander_df_modifier"],
            {"minimum": 26, "maximum": 41, "mean": 31.3},
        )

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

    def test_hidden_reinforcement_records_are_already_in_the_fixed_inventory(self):
        model = self.inventory["source_model"]["reinforcement_model"]
        self.assertEqual(
            model,
            {
                "hidden_fixed_records_included": True,
                "total_hidden_fixed_records": 63,
                "hidden_enemy_fixed_records": 53,
                "hidden_non_enemy_fixed_records": 10,
                "runtime_event_rewrites_require_audit": True,
            },
        )
        records = [
            record
            for scenario in self.inventory["scenarios"]
            for record in scenario["records"]
        ]
        self.assertEqual(sum(record["hidden"] for record in records), 63)
        self.assertEqual(
            sum(
                record["hidden"] and record["side_id"] == "04"
                for record in records
            ),
            53,
        )

    def test_known_runtime_exceptions_are_source_locked(self):
        exceptions = {
            row["scenario"]: row
            for row in self.inventory["source_model"]["known_runtime_exceptions"]
        }
        self.assertEqual(set(exceptions), {22, 25, 30})
        self.assertEqual(exceptions[22]["side_08_record_count"], 10)
        self.assertEqual(
            exceptions[22]["hidden_boss"],
            {
                "offset": "0x182822",
                "side_id": "04",
                "name_korean": "베른하르트",
                "class_id": "4E",
                "class_korean": "엠퍼러",
            },
        )
        self.assertEqual(
            exceptions[25]["fixed_record"],
            {
                "offset": "0x182D62",
                "side_id": "03",
                "name_korean": "제시카",
                "class_id": "03",
                "class_korean": "워록",
            },
        )
        self.assertEqual(
            exceptions[25]["verified_runtime_result"],
            {
                "class_id": "09",
                "class_korean": "소서러",
                "level": 5,
                "at": 29,
                "df": 17,
            },
        )
        self.assertEqual(
            exceptions[30]["phases"],
            [
                {
                    "offset": "0x183724",
                    "side_id": "04",
                    "hidden": False,
                    "class_id": "3F",
                    "class_korean": "메이지",
                },
                {
                    "offset": "0x183748",
                    "side_id": "04",
                    "hidden": True,
                    "class_id": "48",
                    "class_korean": "세인트",
                },
            ],
        )

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
                "base_at_offset": "0x0B",
                "base_df_offset": "0x0C",
                "movement_offset": "0x0D",
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

    def test_combat_class_catalog_covers_hire_enemy_and_summon_ranges(self):
        rows = self.inventory["source_model"]["combat_class_catalog"]
        self.assertEqual(
            [row["class_id"] for row in rows],
            [f"{class_id:02X}" for class_id in range(0x62, 0x95)],
        )
        groups = {}
        for row in rows:
            groups[row["group"]] = groups.get(row["group"], 0) + 1
        self.assertEqual(
            groups,
            {
                "ordinary_hireable": 16,
                "scenario_enemy_variant_or_monster": 27,
                "summon_class": 8,
            },
        )

    def test_known_combat_class_stats_and_usage_are_source_locked(self):
        rows = {
            row["class_id"]: row
            for row in self.inventory["source_model"]["combat_class_catalog"]
        }
        self.assertEqual(
            (
                rows["64"]["korean"],
                rows["64"]["base_at"],
                rows["64"]["base_df"],
                rows["64"]["movement"],
            ),
            ("솔저", 20, 14, 5),
        )
        self.assertEqual(
            (
                rows["7B"]["korean"],
                rows["7B"]["base_at"],
                rows["7B"]["base_df"],
                rows["7B"]["movement"],
            ),
            ("로얄호스", 34, 23, 13),
        )
        self.assertEqual(rows["72"]["first_enemy_scenario"], 1)
        self.assertEqual(rows["72"]["enemy_side_04_slot_count"], 90)
        self.assertEqual(rows["89"]["first_enemy_scenario"], 20)
        self.assertEqual(rows["89"]["enemy_side_04_slot_count"], 52)

    def test_summons_are_not_used_in_original_fixed_mercenary_slots(self):
        summons = [
            row
            for row in self.inventory["source_model"]["combat_class_catalog"]
            if row["group"] == "summon_class"
        ]
        self.assertEqual(
            [(row["class_id"], row["korean"]) for row in summons],
            [
                ("8D", "엘리멘탈"),
                ("8E", "프레이야"),
                ("8F", "화이트드래곤"),
                ("90", "발키리"),
                ("91", "슬레이프니르"),
                ("92", "펜릴"),
                ("93", "요르문간드"),
                ("94", "아니키"),
            ],
        )
        self.assertTrue(
            all(row["all_fixed_slot_count"] == 0 for row in summons)
        )
        self.assertTrue(
            all(row["enemy_side_04_slot_count"] == 0 for row in summons)
        )
        self.assertEqual(
            [
                (row["class_id"], row["base_at"], row["base_df"])
                for row in summons
            ],
            [
                ("8D", 22, 20),
                ("8E", 23, 25),
                ("8F", 33, 22),
                ("90", 29, 21),
                ("91", 31, 18),
                ("92", 31, 25),
                ("93", 29, 28),
                ("94", 35, 30),
            ],
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
        self.assertIn("63 hidden fixed records", rule["dynamic_event_spawns"])
        self.assertIn("53 side-04 enemy", rule["dynamic_event_spawns"])
        self.assertNotIn("not represented", rule["dynamic_event_spawns"])

    def test_exception_inventory_does_not_approve_or_propose_balance_values(self):
        gate = self.inventory["approval_gate"]
        self.assertFalse(gate["user_approved"])
        self.assertFalse(gate["implementation_started"])
        self.assertFalse(gate["rom_values_may_be_applied"])
        self.assertNotIn("proposed_values", self.inventory)
        self.assertNotIn("approved_values", self.inventory)

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
