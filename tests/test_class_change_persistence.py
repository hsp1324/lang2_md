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
        )
        self.assertEqual(progress["checksum"], 0x2330)
        self.assertEqual(progress["checksum"], progress["calculated_checksum"])
        self.assertEqual(progress["at"], 23)
        self.assertEqual(progress["df"], 13)

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
