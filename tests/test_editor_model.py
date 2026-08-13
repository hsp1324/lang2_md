from pathlib import Path
import unittest

from editor.model import class_change_editor_model, item_editor_model
from tools.build_item_icon_assets import icon_crop
from tools.v138_release_identity import RELEASE_ROM_PATHS
ROOT = Path(__file__).resolve().parents[1]
JP_ROM = ROOT / "roms/original/Langrisser II (Japan).md"
KO_ROM = RELEASE_ROM_PATHS["normal"]


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
        self.assertEqual(
            {
                commander["commander_id"]: len(commander["transitions"])
                for commander in model["commanders"]
            },
            {
                1: 10,
                2: 10,
                3: 10,
                4: 10,
                5: 10,
                6: 10,
                7: 11,
                8: 10,
                9: 11,
                10: 10,
            },
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
        self.assertEqual(
            model["commanders"][0]["hidden_class_routes"],
            [
                {"current_class": 0x1A, "hidden_class": 0x22},
                {"current_class": 0x1B, "hidden_class": 0x29},
            ],
        )
        self.assertEqual(
            {
                row["hidden_class"]
                for row in model["commanders"][1][
                    "hidden_class_routes"
                ]
            },
            {0x25, 0x26, 0x28},
        )
        self.assertEqual(
            sum(
                len(commander["hidden_class_routes"])
                for commander in model["commanders"]
            ),
            20,
        )
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
            bald_pixels = set(bald.getdata())
            self.assertNotEqual(generic.tobytes(), bald.tobytes())
            self.assertIn((255, 255, 255, 255), bald_pixels)
            self.assertIn((255, 0, 0, 255), bald_pixels)
            self.assertNotIn((36, 219, 36, 255), bald_pixels)

    def test_sorcerer_shaman_and_priest_use_distinct_preview_palettes(self):
        import json
        from PIL import Image
        from tools import build_class_sprite_assets as sprite_assets

        preview_dir = ROOT / "editor/static/class-sprites"
        manifest = json.loads(
            (preview_dir / "manifest.json").read_text(encoding="utf-8")
        )
        sorcerer_entry = manifest["representatives"][str(0x09)]
        shaman_entry = manifest["representatives"][str(0x0A)]
        priest_entry = manifest["representatives"][str(0x9C)]
        sorcerer_path = preview_dir / sorcerer_entry["file"]
        shaman_path = preview_dir / shaman_entry["file"]
        priest_path = preview_dir / priest_entry["file"]
        self.assertFalse(sorcerer_entry["uses_palette_override"])
        self.assertTrue(shaman_entry["uses_palette_override"])
        self.assertTrue(priest_entry["uses_palette_override"])
        self.assertEqual(
            {
                sorcerer_entry["sprite_id"],
                shaman_entry["sprite_id"],
                priest_entry["sprite_id"],
            },
            {0x1D},
        )
        with Image.open(sorcerer_path) as sorcerer, Image.open(
            shaman_path
        ) as shaman, Image.open(
            priest_path
        ) as priest:
            self.assertNotEqual(sorcerer.tobytes(), shaman.tobytes())
            self.assertNotEqual(sorcerer.tobytes(), priest.tobytes())
            self.assertNotEqual(shaman.tobytes(), priest.tobytes())
            self.assertEqual(
                shaman.getpixel((7, 10)),
                (182, 146, 182, 255),
            )
            self.assertEqual(
                shaman.getpixel((6, 10)),
                (109, 73, 109, 255),
            )
            self.assertEqual(
                shaman.getpixel((4, 10)),
                (255, 255, 255, 255),
            )
            self.assertEqual(
                shaman.getpixel((11, 10)),
                (182, 146, 182, 255),
            )
            self.assertEqual(
                shaman.getpixel((7, 0)),
                (182, 146, 182, 255),
            )
            self.assertEqual(
                shaman.getpixel((6, 0)),
                (109, 73, 109, 255),
            )
            self.assertEqual(
                shaman.getpixel((8, 1)),
                (255, 255, 255, 255),
            )
            original_hood_gray = {
                (146, 146, 146, 255),
                (73, 73, 109, 255),
            }
            self.assertTrue(
                all(
                    shaman.getpixel((x, y)) not in original_hood_gray
                    for y in range(9)
                    for x in range(16)
                )
            )
            original_blue = {
                (73, 109, 255, 255),
                (0, 0, 219, 255),
                (109, 219, 255, 255),
            }
            self.assertTrue(
                all(
                    shaman.getpixel((x, y)) not in original_blue
                    for y in range(9, 16)
                    for x in range(16)
                )
            )
            self.assertEqual(
                sorcerer.getpixel((7, 10)),
                (73, 109, 255, 255),
            )
            self.assertEqual(
                priest.getpixel((7, 10)),
                (255, 251, 234, 255),
            )
            self.assertEqual(
                priest.getpixel((7, 0)),
                (219, 182, 109, 255),
            )
            self.assertEqual(
                priest.getpixel((6, 0)),
                (146, 73, 36, 255),
            )
            self.assertEqual(
                priest.getpixel((8, 1)),
                (255, 251, 234, 255),
            )
            self.assertEqual(
                priest.getpixel((6, 10)),
                (219, 182, 109, 255),
            )
            self.assertEqual(
                priest.getpixel((4, 10)),
                (146, 73, 36, 255),
            )
            militia_path = (
                preview_dir
                / manifest["representatives"][str(0x99)]["file"]
            )
            with Image.open(militia_path) as militia:
                paired_ivory_ramp = {
                    (255, 251, 234, 255),
                    (219, 182, 109, 255),
                    (146, 73, 36, 255),
                }
                self.assertTrue(
                    paired_ivory_ramp.issubset(set(priest.getdata()))
                )
                self.assertTrue(
                    paired_ivory_ramp.issubset(set(militia.getdata()))
                )
        for commander_id in (1, 2, 3, 4, 5, 8, 9):
            row = manifest["commanders"][str(commander_id)][str(0x0A)]
            path = preview_dir / row["file"]
            stock = sprite_assets.render_sprite(
                self.japanese,
                row["sprite_id"],
                1,
            )
            with Image.open(path) as shaman:
                self.assertNotEqual(
                    shaman.tobytes(),
                    stock.tobytes(),
                    f"commander {commander_id} Shaman stayed stock blue",
                )
                self.assertEqual(
                    shaman.crop((0, 0, 16, 9)).tobytes(),
                    stock.crop((0, 0, 16, 9)).tobytes(),
                    f"commander {commander_id} Shaman identity changed",
                )

    def test_militia_and_loren_use_paired_palettes_and_preserve_equipment(
        self,
    ):
        import json
        from PIL import Image
        from tools import build_class_sprite_assets as sprite_assets

        preview_dir = ROOT / "editor/static/class-sprites"
        manifest = json.loads(
            (preview_dir / "manifest.json").read_text(encoding="utf-8")
        )
        regular_path = (
            preview_dir / manifest["representatives"][str(0x0B)]["file"]
        )
        militia_entry = manifest["representatives"][str(0x99)]
        militia_path = preview_dir / militia_entry["file"]
        loren_entry = manifest["representatives"][str(0x9B)]
        loren_path = preview_dir / loren_entry["file"]
        self.assertEqual(militia_entry["sprite_id"], 0x1C)
        self.assertTrue(militia_entry["uses_palette_override"])
        self.assertEqual(loren_entry["sprite_id"], 0x1C)
        self.assertTrue(loren_entry["uses_palette_override"])
        with Image.open(regular_path) as regular, Image.open(
            militia_path
        ) as militia, Image.open(
            loren_path
        ) as loren:
            self.assertNotEqual(regular.tobytes(), loren.tobytes())
            self.assertNotEqual(regular.tobytes(), militia.tobytes())
            self.assertNotEqual(militia.tobytes(), loren.tobytes())
            self.assertEqual(
                militia.getpixel((10, 2)),
                (255, 251, 234, 255),
            )
            self.assertEqual(
                militia.getpixel((6, 0)),
                (219, 182, 109, 255),
            )
            self.assertEqual(
                militia.getpixel((5, 0)),
                (146, 73, 36, 255),
            )
            self.assertEqual(
                loren.getpixel((10, 2)),
                (255, 242, 238, 255),
            )
            self.assertEqual(
                loren.getpixel((6, 0)),
                (255, 109, 73, 255),
            )
            self.assertEqual(
                loren.getpixel((5, 0)),
                (146, 0, 0, 255),
            )
            for coords in sprite_assets.LOREN_BLADE_COORDS:
                self.assertEqual(
                    militia.getpixel(coords),
                    regular.getpixel(coords),
                )
                self.assertEqual(
                    loren.getpixel(coords),
                    regular.getpixel(coords),
                )
            for coords in ((2, 10), (4, 11)):
                self.assertEqual(
                    militia.getpixel(coords),
                    regular.getpixel(coords),
                )
                self.assertEqual(
                    loren.getpixel(coords),
                    regular.getpixel(coords),
                )

            priest_path = (
                preview_dir
                / manifest["representatives"][str(0x9C)]["file"]
            )
            shaman_path = (
                preview_dir
                / manifest["representatives"][str(0x0A)]["file"]
            )
            with Image.open(priest_path) as priest, Image.open(
                shaman_path
            ) as shaman:
                ivory_ramp = {
                    (255, 251, 234, 255),
                    (219, 182, 109, 255),
                    (146, 73, 36, 255),
                }
                crimson_ramp = {
                    (255, 109, 73, 255),
                    (146, 0, 0, 255),
                }
                violet_ramp = {
                    (182, 146, 182, 255),
                    (109, 73, 109, 255),
                }
                self.assertTrue(ivory_ramp.issubset(set(militia.getdata())))
                self.assertTrue(ivory_ramp.issubset(set(priest.getdata())))
                self.assertTrue(crimson_ramp.issubset(set(loren.getdata())))
                self.assertTrue(violet_ramp.issubset(set(shaman.getdata())))

    def test_pirates_use_sky_blue_naval_palette_and_preserve_equipment(
        self,
    ):
        import json
        from PIL import Image
        from tools import build_class_sprite_assets as sprite_assets

        preview_dir = ROOT / "editor/static/class-sprites"
        manifest = json.loads(
            (preview_dir / "manifest.json").read_text(encoding="utf-8")
        )
        regular_path = (
            preview_dir / manifest["representatives"][str(0x0B)]["file"]
        )
        pirates_entry = manifest["representatives"][str(0x9A)]
        pirates_path = preview_dir / pirates_entry["file"]
        self.assertEqual(pirates_entry["sprite_id"], 0x1C)
        self.assertTrue(pirates_entry["uses_palette_override"])
        with Image.open(regular_path) as regular, Image.open(
            pirates_path
        ) as pirates:
            self.assertNotEqual(regular.tobytes(), pirates.tobytes())
            self.assertEqual(
                pirates.getpixel((10, 2)),
                (240, 250, 255, 255),
            )
            self.assertEqual(
                pirates.getpixel((6, 0)),
                (182, 219, 255, 255),
            )
            self.assertEqual(
                pirates.getpixel((5, 0)),
                (109, 146, 182, 255),
            )
            for coords in sprite_assets.LOREN_BLADE_COORDS:
                self.assertEqual(
                    pirates.getpixel(coords),
                    regular.getpixel(coords),
                )
            for coords in ((2, 10), (4, 11)):
                self.assertEqual(
                    pirates.getpixel(coords),
                    regular.getpixel(coords),
                )

    def test_playable_and_loren_high_lords_are_distinct_rom_records(self):
        from tools.class_hire_data import read_class_hire_unlocks
        from tools.scenario_data import class_names

        classes = class_names(self.japanese)
        self.assertEqual(classes[0x0B]["jp"], classes[0x9B]["jp"])
        self.assertEqual(classes[0x0B]["ko"], "하이로드")
        self.assertEqual(classes[0x9B]["ko"], "하이로드")
        base = 0x05EDDC
        size = 0x1C
        self.assertNotEqual(
            self.japanese[base + 0x0B * size : base + 0x0C * size],
            self.japanese[base + 0x9B * size : base + 0x9C * size],
        )
        self.assertEqual(
            read_class_hire_unlocks(
                self.japanese, 0x0B
            ).hire_class_ids,
            (0x6A, 0x63),
        )
        self.assertEqual(
            read_class_hire_unlocks(
                self.japanese, 0x9B
            ).hire_class_ids,
            (0xFF, 0xFF),
        )

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
