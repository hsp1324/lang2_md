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
        self.assertEqual(len(source_cells), 50)
        for filename in source_cells:
            self.assertTrue((AI_ASSET_DIR / filename).is_file(), filename)

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
