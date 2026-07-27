from pathlib import Path
import tempfile
import unittest

from tools.run_blastem_sequence import (
    MANUAL_SLOT_BASES,
    MANUAL_SLOT_COMMANDER_RECORD_SIZE,
    MANUAL_SLOT_COMMANDER_ROSTER_OFFSET,
)
from tools.verify_class_change_persistence import (
    commander_progress,
    verify_progress,
)


ROOT = Path(__file__).resolve().parents[1]
ELWIN_EVIDENCE = ROOT / "captures/analysis/b213_c1_s01_scenario2_save.sram"
HEIN_EVIDENCE = ROOT / "captures/analysis/b335_c5_s03_scenario2_save.sram"
HEIN_PRIEST_EVIDENCE = (
    ROOT / "captures/analysis/b33c_hein_priest_scenario2.sram"
)
HEIN_WIZARD_EVIDENCE = (
    ROOT / "captures/analysis/b353_hein_wizard_scenario2.sram"
)
HEIN_SUMMONER_EVIDENCE = (
    ROOT / "captures/analysis/b36f_hein_summoner_scenario2.sram"
)


class ClassChangePersistenceTests(unittest.TestCase):
    def test_elwin_lord_survives_scenario_two_save(self):
        progress = verify_progress(
            ELWIN_EVIDENCE,
            slot_index=0,
            commander_id=1,
            expected_scenario=2,
            expected_class=0x04,
            expected_level=1,
            expected_experience=9,
            expected_at=23,
            expected_df=18,
            expected_checksum=0x211E,
        )
        self.assertEqual(progress["checksum"], 0x211E)
        self.assertEqual(progress["checksum"], progress["calculated_checksum"])
        self.assertEqual(progress["at"], 23)
        self.assertEqual(progress["df"], 18)

    def test_hein_shaman_survives_scenario_two_save(self):
        progress = verify_progress(
            HEIN_EVIDENCE,
            slot_index=0,
            commander_id=5,
            expected_scenario=2,
            expected_class=0x0A,
            expected_level=1,
            expected_experience=17,
            expected_at=23,
            expected_df=13,
            expected_checksum=0x2330,
        )
        self.assertEqual(progress["checksum"], 0x2330)
        self.assertEqual(progress["checksum"], progress["calculated_checksum"])
        self.assertEqual(progress["at"], 23)
        self.assertEqual(progress["df"], 13)

    def test_hein_summoner_branch_survives_scenario_two_saves(self):
        proofs = (
            (HEIN_PRIEST_EVIDENCE, 0x11, 1, 23, 14, 0x457A),
            (HEIN_WIZARD_EVIDENCE, 0x15, 9, 23, 15, 0xD8C2),
            (HEIN_SUMMONER_EVIDENCE, 0x28, 9, 24, 16, 0xF52F),
        )
        for path, class_id, experience, at, df, checksum in proofs:
            with self.subTest(class_id=class_id):
                progress = verify_progress(
                    path,
                    slot_index=0,
                    commander_id=5,
                    expected_scenario=2,
                    expected_class=class_id,
                    expected_level=1,
                    expected_experience=experience,
                    expected_at=at,
                    expected_df=df,
                    expected_checksum=checksum,
                )
                self.assertEqual(
                    progress["checksum"],
                    progress["calculated_checksum"],
                )

    def test_expected_class_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "class_id=10"):
            verify_progress(
                HEIN_EVIDENCE,
                slot_index=0,
                commander_id=5,
                expected_scenario=2,
                expected_class=0x0B,
            )

    def test_invalid_slot_checksum_is_rejected_before_progress_read(self):
        data = bytearray(HEIN_EVIDENCE.read_bytes())
        record = (
            MANUAL_SLOT_BASES[0]
            + MANUAL_SLOT_COMMANDER_ROSTER_OFFSET
            + 4 * MANUAL_SLOT_COMMANDER_RECORD_SIZE
        )
        data[record] ^= 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.sram"
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "invalid checksum"):
                commander_progress(path, slot_index=0, commander_id=5)


if __name__ == "__main__":
    unittest.main()
