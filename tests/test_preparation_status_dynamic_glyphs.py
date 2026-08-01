import hashlib
import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_status_dynamic_glyphs.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PreparationStatusDynamicGlyphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL.read_text(encoding="utf-8"))

    def test_candidate_and_runtime_evidence_are_hash_locked(self) -> None:
        for key in ("candidate", "normal_candidate"):
            candidate = self.model[key]
            self.assertEqual(
                sha256(ROOT / candidate["path"]),
                candidate["sha256"],
            )
        self.assertEqual(
            self.model["historical_evidence_status"]["status"],
            "superseded_incomplete_screen_evidence",
        )
        for row in self.model["historical_runtime"]:
            with self.subTest(surface=row["surface"]):
                self.assertEqual(row["result"], "pass")
                self.assertEqual(
                    sha256(ROOT / row["capture"]),
                    row["sha256"],
                )
                if "gst" in row:
                    self.assertEqual(
                        sha256(ROOT / row["gst"]),
                        row["gst_sha256"],
                    )

    def test_runtime_model_matches_builder_slot_ownership(self) -> None:
        scope = self.model["scope"]
        self.assertEqual(
            scope["battle_map_cache_slots"],
            len(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS),
        )
        self.assertEqual(
            scope["battle_map_tile_ids"],
            [
                f"0x{tile:04X}"
                for tile in builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS
            ],
        )
        self.assertEqual(
            scope["preparation_slot_groups"],
            list(builder.BYTE_UI_PREP_DYNAMIC_SLOT_GROUPS),
        )
        self.assertEqual(
            scope["preparation_dynamic_slot_count"],
            len(builder.BYTE_UI_PREP_DYNAMIC_SLOT_GROUPS),
        )
        self.assertEqual(
            scope["preparation_dynamic_char_count"],
            len(builder.BYTE_UI_PREP_DYNAMIC_CHARS),
        )
        self.assertEqual(
            scope["preparation_extra_slots"],
            len(builder.BYTE_UI_PREP_EXTRA_TILE_IDS),
        )
        self.assertEqual(
            scope["preparation_extra_tiles"],
            [f"0x{tile:04X}" for tile in builder.BYTE_UI_PREP_EXTRA_TILE_IDS],
        )
        self.assertEqual(builder.BYTE_UI_PREP_DYNAMIC_CHARS[-1], "헬")
        self.assertEqual(builder.BYTE_UI_PREP_EXTRA_TILE_IDS[-1], 0x03E0)

    def test_shop_roundtrip_contract_covers_shared_labels_and_both_builds(self) -> None:
        contract = self.model["transition_contract"]
        self.assertEqual(
            contract["name"],
            "shop_roundtrip_preserves_shared_korean_labels",
        )
        self.assertTrue(
            {
                "preparation",
                "shop",
                "deployment",
                "hiring",
                "class_change",
                "commander_status",
                "map_status",
            }.issubset(contract["sequence"])
        )
        self.assertEqual(
            set(contract["protected_categories"]),
            {"commander_names", "class_names", "mercenary_names"},
        )
        self.assertEqual(
            set(contract["required_examples"]),
            {
                "쉐리",
                "글래디에이터",
                "기남",
                "제국지휘관",
                "네크로맨서",
                "좀비",
                "그레이트슬라임",
                "슬라임",
                "서펜나이트",
                "리자드맨",
                "로얄호스",
            },
        )
        self.assertEqual(
            set(contract["required_runtime_surfaces"]),
            {
                "deployment_commander_name_after_shop_roundtrip",
                "hiring_mercenary_name_after_shop_roundtrip",
                "class_change_commander_name_after_shop_roundtrip",
                "class_change_class_name_after_shop_roundtrip",
                "class_change_mercenary_name_after_shop_roundtrip",
            },
        )
        self.assertEqual(
            set(contract["applies_to"]),
            {"normal_candidate", "hard_candidate"},
        )

        runtime_surfaces = {
            row["surface"]
            for row in self.model["historical_runtime"]
            if "after_shop_roundtrip" in row["surface"]
        }
        self.assertEqual(
            runtime_surfaces,
            {
                "normal_scenario_6_enemy_deployment_after_shop_roundtrip",
                "hard_scenario_6_enemy_deployment_after_shop_roundtrip",
                "normal_scenario_6_preparation_commander_after_shop_roundtrip",
                "normal_scenario_6_class_change_after_shop_roundtrip",
                "hard_scenario_6_preparation_commander_after_shop_roundtrip",
                "hard_scenario_6_class_change_after_shop_roundtrip",
                "hard_scenario_7_ginam_after_shop_roundtrip",
                "hard_scenario_7_imperial_necromancer_after_shop_roundtrip",
            },
        )

    def test_shop_roundtrip_pending_runtime_matrix_covers_both_builds(self) -> None:
        pending = self.model["pending_runtime_acceptance"]
        self.assertEqual(
            {(row["build"], row["surface"]) for row in pending},
            {
                ("normal_candidate", "hiring_mercenary_name_after_shop_roundtrip"),
                ("hard_candidate", "hiring_mercenary_name_after_shop_roundtrip"),
            },
        )
        self.assertTrue(
            all(
                row["status"] == "pending_same_run_before_after_capture"
                for row in pending
            )
        )

    def test_replacement_probes_remain_partial_scenario_evidence(self) -> None:
        self.assertEqual(
            {
                (row["build"], row["scenario"])
                for row in self.model["replacement_runtime"]
            },
            {
                ("hard_candidate", 6),
                ("hard_candidate", 9),
                ("hard_candidate", 1),
                ("normal_candidate", 9),
                ("normal_candidate", 1),
            },
        )
        self.assertTrue(
            all(
                row["result"]
                in {
                    "partial_surface_pass_not_scenario_acceptance",
                    "preparation_surface_pass_battle_pending",
                }
                for row in self.model["replacement_runtime"]
            )
        )
        self.assertEqual(
            {
                row["result"]
                for row in self.model["replacement_runtime"]
                if row["scenario"] == 1
            },
            {"preparation_surface_pass_battle_pending"},
        )
        self.assertEqual(
            self.model["ownership_report"]["status"],
            "verified_static_and_scenario_9_roundtrip",
        )
        self.assertEqual(
            self.model["ownership_report"]["scenario_acceptance_status"],
            "partial_only",
        )
        hard_six = next(
            row
            for row in self.model["replacement_runtime"]
            if row["build"] == "hard_candidate" and row["scenario"] == 6
        )
        self.assertEqual(
            set(hard_six["captures"]),
            set(hard_six["capture_sha256"]),
        )
        for capture in hard_six["captures"]:
            with self.subTest(capture=capture):
                self.assertEqual(
                    sha256(ROOT / capture),
                    hard_six["capture_sha256"][capture],
                )
        self.assertEqual(
            sha256(ROOT / hard_six["gst"]),
            hard_six["gst_sha256"],
        )

    def test_scenario_7_first_enemy_turn_spawn_is_expected_stock_timing(self) -> None:
        expected = self.model["scenario_7_expected_behavior"]
        self.assertEqual(expected["first_enemy_turn_mercenary_spawn"], "stock_expected")
        self.assertEqual(expected["defect_scope"], "excluded")


if __name__ == "__main__":
    unittest.main()
