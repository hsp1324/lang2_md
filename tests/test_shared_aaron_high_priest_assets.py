from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/assets/ai-class-source/latest/shared-high-priest-aaron-v1"
LIVE = ROOT / "editor/static/ai-class-sprites"
TARGETS = (2, 3, 5, 7, 8, 10)


class SharedAaronHighPriestTests(unittest.TestCase):
    def test_master_is_exact_latest_aaron_edit(self) -> None:
        self.assertEqual(
            (SOURCE / "master/08-16-user-edited.png").read_bytes(),
            (SOURCE / "logical16/08-16.png").read_bytes(),
        )

    def test_all_targets_are_live_and_valid(self) -> None:
        report = json.loads((SOURCE / "validation-report.json").read_text())
        self.assertTrue(report["all_accepted"])
        self.assertEqual(report["targets"], list(TARGETS))
        points = json.loads((SOURCE / "identity-points.json").read_text())["points"]
        for commander_id in TARGETS:
            logical_path = SOURCE / f"logical16/{commander_id:02d}-16.png"
            self.assertEqual(logical_path.read_bytes(), (LIVE / str(commander_id) / "16.png").read_bytes())
            logical = Image.open(logical_path).convert("RGBA")
            identity = Image.open(SOURCE / f"references/{commander_id:02d}-identity-source.png").convert("RGBA")
            self.assertEqual(logical.size, (16, 16))
            self.assertLessEqual(len({c for c in logical.get_flattened_data() if c[3]}), 15)
            for raw_point in points[str(commander_id)]:
                point = tuple(raw_point)
                if identity.getpixel(point)[3]:
                    self.assertEqual(logical.getpixel(point), identity.getpixel(point))


if __name__ == "__main__":
    unittest.main()
