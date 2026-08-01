import json
from pathlib import Path
import unittest

from scripts import build_korean_jp_probe as builder


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "localization/monk_sprite_cache_regression.json"


class MonkSpriteCacheRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_report_binds_the_exact_user_collision(self) -> None:
        root = self.report["root_cause"]
        self.assertEqual(root["class_id"], "0x6C")
        self.assertEqual(root["active_frame_0_tiles"], "0x0370..0x0373")
        self.assertEqual(
            root["released_b102_battle_dynamic_tiles"][6:8],
            ["0x0370", "0x0371"],
        )

    def test_current_battle_tiles_are_disjoint_from_all_monk_frames(self) -> None:
        active_0 = set(range(0x0370, 0x0374))
        active_1 = set(range(0x0470, 0x0474))
        acted = set(range(0x03D8, 0x03DC))
        current = set(builder.BYTE_UI_DYNAMIC_MAP_TILE_IDS)
        self.assertTrue(current.isdisjoint(active_0 | active_1 | acted))

    def test_both_runtime_profiles_pass_exact_payload_checks(self) -> None:
        self.assertEqual(self.report["status"], "pass")
        self.assertEqual(
            {row["status"] for row in self.report["runtime_results"].values()},
            {"pass"},
        )
        payloads = self.report["verified_payloads"]
        self.assertTrue(payloads["both_profiles_match_rom_sources"])
        self.assertTrue(payloads["both_profiles_moved_mercenary"])
        self.assertTrue(payloads["both_profiles_changed_acted_flag_0_to_1"])

    def test_probe_rom_changes_only_one_non_checksum_byte(self) -> None:
        delta = self.report["runtime_probe_derivation"]["only_non_checksum_delta"]
        self.assertEqual(delta["offset"], "0x05EE12")
        self.assertEqual(delta["candidate_value"], "0x02")
        self.assertEqual(delta["probe_value"], "0x0A")


if __name__ == "__main__":
    unittest.main()
