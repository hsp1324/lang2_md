from pathlib import Path
import json
import unittest

from PIL import Image

from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    render_sprite,
)
from tools.build_test_class_sprite_assets import (
    protected_face_points,
)
from tools.build_ai_class_sprite_assets import accent_hues, pixelize_cell


ROOT = Path(__file__).resolve().parents[1]
TEST_ASSET_DIR = ROOT / "editor/static/test-class-sprites"
AI_ASSET_DIR = ROOT / "editor/static/ai-class-sprites"


class ExperimentalClassSpriteAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = DEFAULT_ROM.read_bytes()
        cls.test_manifest = json.loads(
            (TEST_ASSET_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        cls.ai_manifest = json.loads(
            (AI_ASSET_DIR / "manifest.json").read_text(encoding="utf-8")
        )

    def test_test_change_assets_are_preview_only_and_complete(self):
        manifest = self.test_manifest
        self.assertEqual(manifest["commander_count"], 10)
        self.assertEqual(manifest["redesigned_count"], 102)
        self.assertIn("preview PNG assets only", manifest["rom_effect"])
        rows = [
            row
            for commander in manifest["commanders"].values()
            for row in commander["classes"].values()
        ]
        self.assertEqual(len(rows), 170)
        self.assertEqual(sum(row["redesigned"] for row in rows), 102)
        for row in rows:
            path = TEST_ASSET_DIR / row["file"]
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (16, 16))
                self.assertEqual(image.mode, "RGBA")

    def test_lowest_duplicate_class_stays_byte_exact(self):
        for commander in self.test_manifest["commanders"].values():
            for row in commander["classes"].values():
                if row["group_rank"] != 0:
                    continue
                expected = render_sprite(
                    self.rom,
                    row["source_sprite_id"],
                    1,
                )
                with Image.open(TEST_ASSET_DIR / row["file"]) as actual:
                    self.assertEqual(actual.tobytes(), expected.tobytes())
                self.assertEqual(row["changed_pixel_count"], 0)

    def test_redesigned_classes_restore_face_and_source_outline(self):
        for commander in self.test_manifest["commanders"].values():
            for row in commander["classes"].values():
                if not row["redesigned"]:
                    continue
                source = render_sprite(
                    self.rom,
                    row["source_sprite_id"],
                    1,
                )
                face = protected_face_points(source)
                self.assertEqual(
                    row["protected_face_pixel_count"],
                    len(face),
                )
                self.assertGreaterEqual(row["changed_pixel_count"], 36)
                with Image.open(TEST_ASSET_DIR / row["file"]) as actual:
                    for point in face:
                        self.assertEqual(
                            actual.getpixel(point),
                            source.getpixel(point),
                        )
                    for y in range(16):
                        for x in range(16):
                            if source.getpixel((x, y)) == (36, 36, 36, 255):
                                self.assertEqual(
                                    actual.getpixel((x, y)),
                                    source.getpixel((x, y)),
                                )

    def test_ai_assets_keep_source_cells_without_face_lock(self):
        manifest = self.ai_manifest
        self.assertEqual(
            manifest["ai_source_sheets"],
            ["docs/assets/allied_class_redesign_concept.png"],
        )
        self.assertEqual(manifest["commander_count"], 10)
        self.assertEqual(manifest["asset_count"], 170)
        self.assertEqual(manifest["redesigned_count"], 102)
        self.assertIn("preview PNG assets only", manifest["rom_effect"])
        source_cells = set()
        rows = [
            row
            for commander in manifest["commanders"].values()
            for row in commander["classes"].values()
        ]
        for row in rows:
            path = AI_ASSET_DIR / row["file"]
            source_cells.add(row["ai_source_cell_file"])
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (16, 16))
                source = render_sprite(
                    self.rom,
                    row["face_source_sprite_id"],
                    1,
                )
                if not row["redesigned"]:
                    self.assertEqual(image.tobytes(), source.tobytes())
                    self.assertEqual(row["face_pixel_count"], 0)
                    continue
                self.assertEqual(row["face_pixel_count"], 0)
                self.assertNotEqual(image.tobytes(), source.tobytes())
                self.assertLessEqual(
                    len(image.getcolors(maxcolors=256) or []),
                    16,
                )
                self.assertTrue(
                    {
                        color
                        for _, color in (
                            image.getchannel("A").getcolors(maxcolors=256)
                            or []
                        )
                    }.issubset({0, 255})
                )
        self.assertEqual(len(source_cells), 50)
        for filename in source_cells:
            self.assertTrue((AI_ASSET_DIR / filename).is_file(), filename)

    def test_ai_pixelizer_uses_full_extent_and_preserves_rare_accents(self):
        sheet = Image.open(
            ROOT / "docs/assets/allied_class_redesign_concept.png"
        ).convert("RGB")
        elwin_lord = pixelize_cell(sheet, 0, 1)
        self.assertEqual(elwin_lord.size, (16, 16))
        self.assertEqual(elwin_lord.getchannel("A").getbbox(), (0, 0, 16, 16))
        self.assertTrue(
            {
                color
                for _, color in (
                    elwin_lord.getchannel("A").getcolors(maxcolors=256) or []
                )
            }.issubset({0, 255})
        )
        self.assertLessEqual(
            len(elwin_lord.getcolors(maxcolors=256) or []),
            16,
        )
        self.assertTrue(
            any(
                green >= 96
                and green >= red + 40
                and green >= blue + 20
                and alpha == 255
                for y in range(elwin_lord.height)
                for x in range(elwin_lord.width)
                for red, green, blue, alpha in [
                    elwin_lord.getpixel((x, y))
                ]
            ),
            "Elwin Lord's one-pixel green shield accent was lost",
        )

    def test_ai_redesigns_retain_most_significant_source_hues(self):
        source_hue_count = 0
        retained_hue_count = 0
        for commander in self.ai_manifest["commanders"].values():
            for row in commander["classes"].values():
                if not row["redesigned"]:
                    continue
                with Image.open(
                    AI_ASSET_DIR / row["ai_source_cell_file"]
                ) as source:
                    wanted = accent_hues(source.convert("RGBA"))
                with Image.open(AI_ASSET_DIR / row["file"]) as converted:
                    retained = accent_hues(
                        converted.convert("RGBA"),
                        minimum=1,
                    )
                source_hue_count += len(wanted)
                retained_hue_count += len(wanted & retained)
        self.assertGreater(source_hue_count, 0)
        self.assertGreaterEqual(
            retained_hue_count / source_hue_count,
            0.70,
        )

    def test_preview_generators_are_not_imported_by_rom_builder(self):
        production_sources = (
            ROOT / "scripts/build_korean_jp_probe.py",
            ROOT / "editor/server.py",
        )
        for path in production_sources:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("build_test_class_sprite_assets", source)
            self.assertNotIn("build_ai_class_sprite_assets", source)

    def test_direct_16x16_generation_experiment_is_source_only(self):
        direct_sources = sorted(
            (ROOT / "docs/assets").glob("direct_16x16_*.png")
        )
        self.assertEqual(len(direct_sources), 10)
        for path in direct_sources:
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 1000)
                self.assertGreaterEqual(image.height, 500)
        manifest_text = (AI_ASSET_DIR / "manifest.json").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("direct_16x16_", manifest_text)


if __name__ == "__main__":
    unittest.main()
