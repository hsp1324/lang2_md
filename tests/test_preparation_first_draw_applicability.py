from __future__ import annotations

import argparse
from pathlib import Path
import tempfile
import unittest

from tools import verify_preparation_first_draw_applicability as verifier


class PreparationFirstDrawApplicabilityTest(unittest.TestCase):
    def args(
        self,
        normal_target: Path,
        hard_target: Path,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            source_report=verifier.DEFAULT_SOURCE_REPORT,
            source_normal_rom=verifier.DEFAULT_SOURCE_NORMAL_ROM,
            source_hard_rom=verifier.DEFAULT_SOURCE_HARD_ROM,
            target_normal_rom=normal_target,
            target_hard_rom=hard_target,
            output=Path("unused.json"),
            check=False,
        )

    def test_current_source_candidates_retain_every_preparation_owned_byte(self):
        root = Path(__file__).resolve().parents[1]
        report = verifier.build_report(
            self.args(
                root / "tmp/current-source-audit-normal.md",
                root / "tmp/current-source-audit-hard.md",
            )
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["changed_preparation_owned_ranges"], 0)
        for row in report["profiles"].values():
            self.assertTrue(row["all_preparation_owned_ranges_byte_identical"])
            self.assertEqual(
                len(row["preparation_owned_ranges"]),
                len(verifier.PREPARATION_OWNED_RANGES),
            )

    def test_changed_preparation_renderer_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            normal = root / "normal.md"
            hard = root / "hard.md"
            normal.write_bytes(verifier.DEFAULT_SOURCE_NORMAL_ROM.read_bytes())
            hard.write_bytes(verifier.DEFAULT_SOURCE_HARD_ROM.read_bytes())
            changed = bytearray(normal.read_bytes())
            changed[verifier.builder.BYTE_UI_PREP_DYNAMIC_GLYPH_RENDER_ROUTINE] ^= 1
            normal.write_bytes(changed)
            with self.assertRaisesRegex(
                ValueError,
                "preparation-owned range changed: preparation_renderer",
            ):
                verifier.build_report(self.args(normal, hard))


if __name__ == "__main__":
    unittest.main()
