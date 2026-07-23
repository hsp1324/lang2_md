from pathlib import Path
import unittest

from editor.model import class_change_editor_model, item_editor_model
ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = ROOT / "roms/builds/Langrisser II (Korean).md"


class EditorModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japanese = JP_ROM.read_bytes()
        cls.korean = KO_ROM.read_bytes()

    def test_item_model_has_all_prices_effects_and_metadata(self):
        model = item_editor_model(self.korean)
        self.assertEqual(len(model["items"]), 37)
        self.assertEqual(model["items"][0]["name"], "단검")
        self.assertEqual(model["items"][0]["icon_url"], "/item-icons/01.png")
        self.assertEqual(model["items"][0]["purchase_price"], 50)
        self.assertEqual(model["items"][30]["name"], "크라운")
        self.assertEqual(
            [effect["effect_type"] for effect in model["items"][30]["effects"][:3]],
            [3, 4, 5],
        )
        self.assertIn(
            {"id": 6, "name": "마법 사거리"},
            model["effect_types"],
        )

    def test_class_change_model_has_ten_complete_commander_chains(self):
        model = class_change_editor_model(self.korean, self.japanese)
        self.assertEqual(len(model["commanders"]), 10)
        self.assertEqual(model["commanders"][0]["name"], "엘윈")
        self.assertTrue(
            all(len(commander["transitions"]) == 10
                for commander in model["commanders"])
        )
        self.assertEqual(
            model["commanders"][0]["transitions"][0],
            {
                "index": 0,
                "source_tier": 1,
                "current_class": 1,
                "candidates": [4, 5, 10],
                "offset": 0x082562,
            },
        )
        self.assertEqual(model["preview_class_ids"][:3], [1, 2, 3])
        self.assertEqual(len(model["class_hires"]), 157)
        self.assertEqual(
            model["class_hires"][1]["hire_class_ids"],
            [0x64, 0xFF],
        )
        self.assertEqual(model["hire_class_ids"], list(range(0x62, 0x72)))

    def test_committed_rom_sprite_manifest_is_self_contained(self):
        import json
        from PIL import Image

        preview_dir = ROOT / "editor/static/class-sprites"
        manifest = json.loads(
            (preview_dir / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["generic_class_count"], 157)
        self.assertEqual(manifest["commander_count"], 10)
        self.assertEqual(len(manifest["generic"]), 157)
        for entry in manifest["generic"].values():
            self.assertEqual(len(entry["files"]), 4)
            for filename in entry["files"]:
                path = preview_dir / filename
                self.assertTrue(path.is_file(), path)
                with Image.open(path) as image:
                    self.assertEqual(image.size, (16, 16))
                    self.assertEqual(image.mode, "RGBA")

    def test_committed_item_icon_manifest_is_self_contained(self):
        import json
        from PIL import Image

        icon_dir = ROOT / "editor/static/item-icons"
        manifest = json.loads(
            (icon_dir / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["asset_count"], 37)
        for entry in manifest["assets"].values():
            path = icon_dir / entry["file"]
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (16, 16))


if __name__ == "__main__":
    unittest.main()
