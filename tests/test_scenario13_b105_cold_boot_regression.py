import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "localization/scenario13_royalhorse_gray_regression.json"


class Scenario13B105ColdBootRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.release = cls.report["release_b105_cold_boot_revalidation"]

    def test_release_identity_and_user_save_slot_are_locked(self) -> None:
        self.assertEqual(self.release["release_rom"]["md_checksum"], "F296")
        self.assertEqual(
            self.release["release_rom"]["sha256"],
            "fcb38e375f410715f026453230319b6a4329605edecfa191e91d601d348a770d",
        )
        self.assertEqual(self.release["user_sram"]["slot_1_scenario"], 13)
        self.assertEqual(self.release["user_sram"]["elwin_class_id"], "0x14")

    def test_cold_boot_proves_elwin_and_two_phalanx_plane_linkage(self) -> None:
        cold = self.release["exact_user_sram_cold_boot"]
        self.assertEqual(cold["visual_result"], "pass")
        self.assertTrue(cold["elwin_acted_private_gray_vram_matches"])
        self.assertEqual(cold["elwin_complete_plane_a_tile_range"], "0x04B0..0x04B3")
        self.assertEqual(cold["phalanx_count"], 2)
        self.assertTrue(cold["phalanx_active_frame_1_vram_matches"])
        self.assertEqual(cold["phalanx_complete_plane_a_tile_range"], "0x044C..0x044F")

    def test_strengthened_probe_rejects_ui_only_visibility(self) -> None:
        probe = self.release["strengthened_formal_probe"]
        self.assertEqual(probe["status"], "pass")
        self.assertEqual(probe["hired_class_id"], "0x63")
        self.assertEqual(probe["complete_plane_a_sprite_occurrences"], 2)
        self.assertEqual(probe["real_move_acted_flag_transition"], "0->1")
        self.assertTrue(probe["both_active_frames_match_rom_source"])
        self.assertTrue(probe["acted_gray_vram_matches"])

        evidence = ROOT / probe["evidence"]
        if evidence.is_file():
            self.assertEqual(
                hashlib.sha256(evidence.read_bytes()).hexdigest(),
                probe["evidence_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
