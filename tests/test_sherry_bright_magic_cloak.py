from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = ROOT / "editor/static/ai-class-sprites"
SOURCE_ROOT = (
    ROOT / "docs/assets/ai-class-source/latest/shared-elwin-magic-v1/logical16"
)


class SherryBrightMagicCloakTests(unittest.TestCase):
    def test_mage_and_archmage_use_bright_princess_cyan(self) -> None:
        for class_id in (0x13, 0x14):
            with Image.open(SOURCE_ROOT / f"04-{class_id:02X}.png") as opened:
                source = opened.convert("RGBA")
            with Image.open(AI_ROOT / f"4/{class_id:02X}.png") as opened:
                live = opened.convert("RGBA")
            self.assertEqual(
                list(source.get_flattened_data()),
                list(live.get_flattened_data()),
            )
            colors = Counter(live.get_flattened_data())
            self.assertGreaterEqual(colors[(109, 219, 255, 255)], 12)
            self.assertGreaterEqual(colors[(0, 109, 146, 255)], 12)
            self.assertEqual(colors[(0, 36, 73, 255)], 0)
            self.assertGreater(colors[(36, 36, 36, 255)], 0)

    def test_manifest_explains_the_bright_cloak(self) -> None:
        manifest = json.loads(
            (AI_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        for class_id in (0x13, 0x14):
            row = manifest["commanders"]["4"]["classes"][str(class_id)]
            self.assertIn("밝은 청록", row["feature"])


if __name__ == "__main__":
    unittest.main()
