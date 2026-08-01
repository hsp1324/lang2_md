import json
import unittest

from tools import verify_b104_glyph_lifetime_release as release


class B104GlyphLifetimeReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = release.build_report()

    def test_release_and_desktop_artifacts_are_exact(self) -> None:
        release.validate(self.report)
        result = self.report["release"]
        self.assertEqual(result["rom_sha256"], result["rebuilt_rom_sha256"])
        self.assertEqual(result["rom_sha256"], result["desktop_rom_sha256"])
        self.assertEqual(result["md_checksum"], "1991")

    def test_source_delta_preserves_design_balance_and_save_format(self) -> None:
        delta = self.report["source_delta"]
        self.assertTrue(delta["all_changes_classified"])
        self.assertTrue(delta["save_format_header_preserved"])
        self.assertTrue(
            all(row["matches_proven_reference"] for row in delta["glyph_fix_ranges"])
        )
        self.assertTrue(
            all(
                row["matches_b103_source"]
                for row in delta["preserved_hard_balance_ranges"]
            )
        )

    def test_pike_and_monk_runtime_contracts_pass(self) -> None:
        pike = self.report["pike_runtime"]
        monk = self.report["monk_runtime"]
        self.assertEqual((pike["hired_class"], pike["hired_count"]), ("파이크", 6))
        self.assertEqual((monk["hired_class"], monk["hired_count"]), ("몽크", 1))
        self.assertTrue(pike["both_active_frames_match_rom_source"])
        self.assertTrue(monk["both_active_frames_match_rom_source"])
        self.assertTrue(pike["gray_matches_stock_silhouette_expansion"])
        self.assertTrue(monk["gray_matches_stock_silhouette_expansion"])
        self.assertEqual(monk["non_checksum_changed_offsets"], ["0x05EE12"])

    def test_checked_report_is_current(self) -> None:
        checked = json.loads(release.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(checked, self.report)


if __name__ == "__main__":
    unittest.main()
