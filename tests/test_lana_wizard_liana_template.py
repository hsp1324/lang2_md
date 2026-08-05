from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/assets/ai-class-source/latest/lana-wizard-liana-template-v1"


class LanaWizardLianaTemplateTests(unittest.TestCase):
    def test_lana_wizard_is_live_identity_locked_and_valid(self) -> None:
        report = json.loads((SOURCE / "validation-report.json").read_text())
        self.assertTrue(report["accepted"])
        logical = SOURCE / "logical16/03-15.png"
        live = ROOT / "editor/static/ai-class-sprites/3/15.png"
        self.assertEqual(logical.read_bytes(), live.read_bytes())
        image = Image.open(logical).convert("RGBA")
        self.assertLessEqual(len({c for c in image.get_flattened_data() if c[3]}), 15)
        self.assertNotIn((255, 0, 255, 255), image.get_flattened_data())
        self.assertNotIn((0, 0, 0, 255), image.get_flattened_data())


if __name__ == "__main__":
    unittest.main()
