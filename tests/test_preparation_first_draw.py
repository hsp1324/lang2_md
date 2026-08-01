from __future__ import annotations

import argparse
from pathlib import Path
import tempfile
import unittest

from tools import verify_preparation_first_draw as verifier


ROOT = Path(__file__).resolve().parents[1]


class PreparationFirstDrawTest(unittest.TestCase):
    def args(self, output: Path) -> argparse.Namespace:
        return argparse.Namespace(
            capture_root=verifier.DEFAULT_CAPTURE_ROOT,
            normal_rom=verifier.DEFAULT_NORMAL_ROM,
            hard_rom=verifier.DEFAULT_HARD_ROM,
            output=output,
            check=False,
        )

    def test_current_capture_pairs_change_only_one_owned_tile(self):
        report = verifier.build_report(self.args(Path("unused.json")))
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["gst_states_checked"], 4)
        self.assertEqual(report["summary"]["hscroll_nonzero_states"], 0)
        self.assertEqual(report["summary"]["mercenary_icon_cache_changes"], 0)
        for profile in verifier.PROFILES:
            row = report["profiles"][profile]
            self.assertGreater(row["full_vram_changed_bytes"], 0)
            self.assertLessEqual(row["full_vram_changed_bytes"], 32)
            self.assertEqual(row["verified_tile_payload_bytes"], 32)
            self.assertTrue(row["all_other_vram_bytes_unchanged"])
            self.assertTrue(row["hscroll_unchanged_and_zero"])
            self.assertTrue(row["mercenary_icon_cache_unchanged"])

    def test_extra_vram_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for profile in verifier.PROFILES:
                target = root / profile
                target.mkdir(parents=True)
                for phase in ("before", "after"):
                    source = verifier.DEFAULT_CAPTURE_ROOT / profile / f"{phase}.gst"
                    (target / f"{phase}.gst").write_bytes(source.read_bytes())
            changed = bytearray((root / "normal/after.gst").read_bytes())
            extra = verifier.ownership.GST_VRAM_OFFSET + 0x100
            changed[extra] ^= 0x01
            (root / "normal/after.gst").write_bytes(changed)
            args = self.args(Path("unused.json"))
            args.capture_root = root
            with self.assertRaisesRegex(ValueError, "changed 2 VRAM tiles"):
                verifier.build_report(args)


if __name__ == "__main__":
    unittest.main()
