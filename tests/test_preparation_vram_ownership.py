from pathlib import Path
import json
import tempfile
import unittest

from scripts import build_korean_jp_probe as builder
from tools import analyze_preparation_vram_ownership as ownership


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "localization/preparation_vram_ownership.json"


class PreparationVramOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = ownership.build_report(
            ownership.DEFAULT_HISTORICAL_GST,
            ownership.DEFAULT_PRE_GST,
            ownership.DEFAULT_POST_GST,
        )

    def test_report_passes_all_ownership_and_roundtrip_checks(self) -> None:
        ownership.validate_report(self.report)

    def test_checked_in_report_is_current(self) -> None:
        self.assertEqual(
            json.loads(MODEL.read_text(encoding="utf-8")),
            self.report,
        )

    def test_builder_uses_only_the_audited_pattern_pool(self) -> None:
        replacement = self.report["replacement_pool"]
        source = replacement["retained_source_manifest"]
        self.assertEqual(
            replacement["tiles"],
            [f"0x{tile:04X}" for tile in builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS],
        )
        self.assertEqual(source["scope"], ownership.RETAINED_GST_SCOPE)
        self.assertEqual(source["state_count"], 212)
        self.assertEqual(source["preparation_state_count"], 8)
        self.assertTrue(source["unrelated_gst_files_are_out_of_scope"])
        self.assertTrue(replacement["current_preparation_renderer_is_exercised"])
        self.assertTrue(replacement["pool_has_no_current_sat_reference"])
        self.assertTrue(
            replacement[
                "strictly_preparation_only_tiles_are_absent_outside_preparation"
            ]
        )
        self.assertTrue(
            all(
                not 0xF400
                <= tile * ownership.TILE_BYTES
                < 0xF800
                for tile in builder.BYTE_UI_PREP_DYNAMIC_TILE_IDS
            )
        )
        self.assertTrue(
            replacement[
                "battle_map_avoids_ordinary_mercenary_active_second_and_gray"
            ]
        )

    def test_historical_gst_decodes_the_physical_hscroll_collision(self) -> None:
        historical = self.report["historical_collision"]
        self.assertEqual(historical["vdp_register_11"], "0x00")
        self.assertEqual(historical["vdp_register_13"], "0x3D")
        self.assertEqual(historical["hscroll_base"], "0xF400")
        self.assertEqual(historical["hscroll_end"], "0xF7FF")
        self.assertTrue(historical["historical_tiles_inside_hscroll"])
        self.assertEqual(historical["nonzero_hscroll_bytes"], 192)

    def test_scenario_9_full_screens_are_exact_across_shop(self) -> None:
        runtime = self.report["scenario_9_shop_roundtrip"]
        self.assertEqual(runtime["hard"]["pre_hscroll_nonzero_bytes"], 0)
        for profile in ("normal", "hard"):
            with self.subTest(profile=profile):
                profile_runtime = runtime[profile]
                self.assertEqual(profile_runtime["post_hscroll_nonzero_bytes"], 0)
                self.assertEqual(len(profile_runtime["capture_pairs"]), 3)
                self.assertTrue(
                    all(
                        row["byte_identical"]
                        for row in profile_runtime["capture_pairs"]
                    )
                )
        self.assertTrue(runtime["hard"]["pool_payloads_identical_before_after"])

    def test_retained_source_manifest_hash_drift_fails_closed(self) -> None:
        manifest = json.loads(
            ownership.DEFAULT_RETAINED_GST_MANIFEST.read_text(encoding="utf-8")
        )
        manifest["families"][0]["path_hash_aggregate_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.json"
            path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "hash changed"):
                ownership.retained_source_states(path)


if __name__ == "__main__":
    unittest.main()
