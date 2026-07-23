from pathlib import Path
import unittest

from editor.model import class_change_editor_model, item_editor_model
from tools.build_item_icon_assets import icon_crop
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
        self.assertEqual(manifest["representative_class_count"], 157)
        self.assertEqual(manifest["commander_count"], 10)
        self.assertEqual(len(manifest["generic"]), 157)
        self.assertEqual(len(manifest["representatives"]), 157)
        for entry in manifest["generic"].values():
            self.assertEqual(len(entry["files"]), 4)
            for filename in entry["files"]:
                path = preview_dir / filename
                self.assertTrue(path.is_file(), path)
                with Image.open(path) as image:
                    self.assertEqual(image.size, (16, 16))
                    self.assertEqual(image.mode, "RGBA")
        for entry in manifest["representatives"].values():
            path = preview_dir / entry["file"]
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (16, 16))
                self.assertEqual(image.mode, "RGBA")

    def test_playable_class_representatives_avoid_aniki_placeholder(self):
        import json

        manifest = json.loads(
            (
                ROOT / "editor/static/class-sprites/manifest.json"
            ).read_text(encoding="utf-8")
        )
        for class_id in (0x03, 0x0E, 0x12, 0x1D, 0x2A):
            entry = manifest["representatives"][str(class_id)]
            self.assertEqual(entry["generic_sprite_id"], 0x18)
            self.assertNotEqual(entry["sprite_id"], 0x18)
            self.assertTrue(entry["uses_commander_override"])

    def test_bald_fighter_has_distinct_violet_representative_palette(self):
        import json
        from PIL import Image

        preview_dir = ROOT / "editor/static/class-sprites"
        manifest = json.loads(
            (preview_dir / "manifest.json").read_text(encoding="utf-8")
        )
        generic_path = preview_dir / manifest["representatives"][str(0x2D)]["file"]
        bald_entry = manifest["representatives"][str(0x2E)]
        bald_path = preview_dir / bald_entry["file"]
        self.assertTrue(bald_entry["uses_palette_override"])
        with Image.open(generic_path) as generic, Image.open(bald_path) as bald:
            bald_pixels = set(bald.get_flattened_data())
            self.assertNotEqual(generic.tobytes(), bald.tobytes())
            self.assertIn((255, 255, 255, 255), bald_pixels)
            self.assertIn((255, 0, 0, 255), bald_pixels)
            self.assertNotIn((36, 219, 36, 255), bald_pixels)

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

    def test_item_icon_crop_tracks_each_five_item_capture_page(self):
        self.assertEqual(icon_crop(1), (24, 42, 40, 58))
        self.assertEqual(icon_crop(5), (24, 106, 40, 122))
        self.assertEqual(icon_crop(6), (24, 42, 40, 58))
        self.assertEqual(icon_crop(8), (24, 74, 40, 90))
        self.assertEqual(icon_crop(37), (24, 58, 40, 74))


if __name__ == "__main__":
    unittest.main()
