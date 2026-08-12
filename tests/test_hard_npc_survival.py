import copy
import json
from pathlib import Path
import unittest

from tools import build_hard_mode_rom as hard_builder
from tools import hard_mode_approval
from tools import hard_mode_npc_survival
from tools import hard_mode_plan
from tools import scenario_data
from tools import verify_hard_mode_runtime_evidence as runtime_evidence


ROOT = Path(__file__).resolve().parents[1]
NORMAL_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"
ORIGINAL_ROM = ROOT / "roms/original/Langrisser II (Japan).md"


class HardNpcSurvivalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normal_before = NORMAL_ROM.read_bytes()
        cls.original_before = ORIGINAL_ROM.read_bytes()
        cls.plan = hard_builder.load_applied_plan()
        cls.hard, cls.manifest = hard_builder.apply_hard_mode(
            cls.normal_before,
            cls.plan,
            hard_mode_approval.require_approved(),
        )
        cls.section = cls.plan["npc_survival_protection"]
        cls.records = list(
            hard_mode_npc_survival.protection_records(cls.section)
        )
        cls.pairs = hard_builder._correction_pairs(cls.plan)

    def test_scope_is_exactly_nineteen_loss_condition_npcs(self):
        self.assertEqual(self.section["scenario_count"], 9)
        self.assertEqual(self.section["record_count"], 19)
        self.assertEqual(len(self.records), 19)
        self.assertEqual(
            tuple(record["offset"] for _, record in self.records),
            hard_mode_npc_survival.EXPECTED_OFFSETS,
        )
        self.assertEqual(
            [row["number"] for row in self.section["scenarios"]],
            [1, 2, 3, 4, 6, 7, 9, 11, 18],
        )
        enemy_offsets = {
            record["offset"]
            for scenario in self.plan["scenarios"]
            for record in scenario["records"]
        }
        self.assertTrue(
            enemy_offsets.isdisjoint(
                hard_mode_npc_survival.EXPECTED_OFFSETS
            )
        )

    def test_tracked_ledger_matches_the_deterministic_generator(self):
        baseline = json.loads(
            (ROOT / "localization/hard_mode_baseline.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            self.section,
            hard_mode_npc_survival.build_section(
                baseline,
                hard_mode_plan.proposal_steps(),
            ),
        )

    def test_tracked_documentation_section_matches_the_renderer(self):
        rendered = hard_mode_plan.render_markdown(self.plan)
        tracked = (ROOT / "docs/hard_mode_changes.md").read_text(
            encoding="utf-8"
        )
        start = "## 패배 조건 NPC 생존 보정"
        end = "## 룬스톤 성장 전제"
        self.assertEqual(
            rendered[rendered.index(start):rendered.index(end)],
            tracked[tracked.index(start):tracked.index(end)],
        )

    def test_defense_exactly_offsets_each_scenario_enemy_attack_bonus(self):
        for scenario in self.section["scenarios"]:
            commander_delta = scenario["enemy_attack_offset"][
                "commander_at_delta"
            ]
            soldier_delta = scenario["enemy_attack_offset"][
                "soldier_at_correction_delta"
            ]
            for record in scenario["records"]:
                with self.subTest(
                    scenario=scenario["number"],
                    offset=record["offset"],
                ):
                    self.assertEqual(
                        record["commander_df"]["planned"]
                        - record["commander_df"]["original"],
                        commander_delta,
                    )
                    self.assertEqual(
                        record["soldier_correction"]["df"]["planned"]
                        - record["soldier_correction"]["df"]["original"],
                        soldier_delta,
                    )

    def test_each_npc_changes_only_df_and_the_per_record_correction_tag(self):
        for scenario, record in self.records:
            offset = int(record["offset"], 16)
            before = self.normal_before[
                offset:offset + hard_builder.FIXED_RECORD_SIZE
            ]
            after = self.hard[
                offset:offset + hard_builder.FIXED_RECORD_SIZE
            ]
            changed_fields = {
                index
                for index, (old, new) in enumerate(zip(before, after))
                if old != new
            }
            with self.subTest(scenario=scenario, offset=record["offset"]):
                self.assertEqual(
                    changed_fields,
                    {
                        hard_builder.COMMANDER_DF_OFFSET,
                        hard_builder.HARD_CORRECTION_INDEX_OFFSET,
                    },
                )
                self.assertEqual(
                    hard_builder._signed_byte(
                        after[hard_builder.COMMANDER_DF_OFFSET]
                    ),
                    record["commander_df"]["planned"],
                )
                tag = after[hard_builder.HARD_CORRECTION_INDEX_OFFSET]
                self.assertEqual(
                    self.pairs[tag],
                    (
                        record["soldier_correction"]["at"],
                        record["soldier_correction"]["df"]["planned"],
                    ),
                )

    def test_playable_npcs_use_live_roster_relative_defense_deltas(self):
        table = hard_builder._dynamic_npc_delta_table(
            self.plan,
            self.pairs,
        )
        protected_playable = []
        for scenario in self.section["scenarios"]:
            expected_delta = (
                scenario["enemy_attack_offset"]["commander_at_delta"],
                scenario["enemy_attack_offset"][
                    "soldier_at_correction_delta"
                ],
            )
            for record in scenario["records"]:
                if int(record["name_id"], 16) > 0x0B:
                    continue
                offset = int(record["offset"], 16)
                tag = self.hard[
                    offset + hard_builder.HARD_CORRECTION_INDEX_OFFSET
                ]
                actual_delta = tuple(table[tag * 2:tag * 2 + 2])
                protected_playable.append(
                    (scenario["number"], record["name_korean"])
                )
                with self.subTest(
                    scenario=scenario["number"],
                    name=record["name_korean"],
                ):
                    self.assertEqual(actual_delta, expected_delta)
        self.assertEqual(
            protected_playable,
            [
                (1, "리아나"),
                (2, "리아나"),
                (3, "리아나"),
                (4, "리아나"),
                (11, "제시카"),
            ],
        )

    def test_retained_xvfb_entries_match_all_nineteen_runtime_targets(self):
        rows = {
            1: 2,
            2: 3,
            3: 3,
            4: 3,
            6: 5,
            7: 6,
            9: 7,
            11: 6,
            18: 8,
        }
        total = 0
        for scenario, player_group_count in rows.items():
            gst = (
                ROOT
                / "captures/analysis"
                / (
                    "arca179646819-dynamic-npc_"
                    f"s{scenario:02d}_entry_turn1_entry.gst"
                )
            )
            if not gst.is_file():
                self.skipTest("retained article NPC runtime GSTs are absent")
            groups = runtime_evidence.verify_protected_npc_scenario(
                gst.read_bytes(),
                self.hard,
                scenario,
                player_group_count,
            )
            total += len(groups)
        self.assertEqual(total, 19)

    def test_at_class_ai_placement_level_name_and_mercenaries_are_unchanged(self):
        mutable = {
            hard_builder.COMMANDER_DF_OFFSET,
            hard_builder.HARD_CORRECTION_INDEX_OFFSET,
        }
        for scenario, record in self.records:
            offset = int(record["offset"], 16)
            before = self.normal_before[
                offset:offset + hard_builder.FIXED_RECORD_SIZE
            ]
            after = self.hard[
                offset:offset + hard_builder.FIXED_RECORD_SIZE
            ]
            with self.subTest(scenario=scenario, offset=record["offset"]):
                for index in range(hard_builder.FIXED_RECORD_SIZE):
                    if index not in mutable:
                        self.assertEqual(after[index], before[index])
                self.assertEqual(
                    after[hard_builder.COMMANDER_AT_OFFSET],
                    before[hard_builder.COMMANDER_AT_OFFSET],
                )
                self.assertEqual(
                    after[hard_builder.CLASS_ID_OFFSET],
                    before[hard_builder.CLASS_ID_OFFSET],
                )
                self.assertEqual(
                    after[hard_builder.X_OFFSET:hard_builder.Y_OFFSET + 1],
                    before[hard_builder.X_OFFSET:hard_builder.Y_OFFSET + 1],
                )
                self.assertEqual(
                    after[
                        hard_builder.MERCENARY_OFFSET:
                        hard_builder.FIXED_RECORD_SIZE
                    ],
                    before[
                        hard_builder.MERCENARY_OFFSET:
                        hard_builder.FIXED_RECORD_SIZE
                    ],
                )

    def test_no_other_side03_fixed_record_is_changed(self):
        changed_side03 = []
        for scenario in range(1, scenario_data.SCENARIO_COUNT + 1):
            layout = scenario_data.scenario_layout(
                self.normal_before,
                scenario,
            )
            for index in range(layout.record_count):
                offset = (
                    layout.records_offset
                    + index * scenario_data.FIXED_RECORD_SIZE
                )
                if (
                    self.normal_before[
                        offset + scenario_data.SIDE_OFFSET
                    ]
                    != 0x03
                ):
                    continue
                if self.hard[
                    offset:offset + scenario_data.FIXED_RECORD_SIZE
                ] != self.normal_before[
                    offset:offset + scenario_data.FIXED_RECORD_SIZE
                ]:
                    changed_side03.append(f"0x{offset:06X}")
        self.assertEqual(
            tuple(changed_side03),
            hard_mode_npc_survival.EXPECTED_OFFSETS,
        )

    def test_original_and_normal_profile_files_receive_zero_byte_changes(self):
        self.assertEqual(NORMAL_ROM.read_bytes(), self.normal_before)
        self.assertEqual(ORIGINAL_ROM.read_bytes(), self.original_before)
        impact = self.section["profile_impact"]
        self.assertEqual(impact["original"], "byte_identical")
        self.assertEqual(impact["normal"], "byte_identical")
        implementation = self.manifest["implementation"]
        self.assertFalse(implementation["original_profile_modified"])
        self.assertFalse(implementation["normal_profile_modified"])
        self.assertEqual(
            implementation["npc_survival_protection_record_count"],
            19,
        )
        self.assertEqual(implementation["total_fixed_record_count"], 319)

    def test_scope_validation_rejects_a_twentieth_record(self):
        expanded = copy.deepcopy(self.section)
        expanded["record_count"] = 20
        expanded["scenarios"][0]["record_count"] = 2
        expanded["scenarios"][0]["records"].append(
            copy.deepcopy(expanded["scenarios"][0]["records"][0])
        )
        with self.assertRaises(ValueError):
            hard_mode_npc_survival.validate_section(expanded)


if __name__ == "__main__":
    unittest.main()
