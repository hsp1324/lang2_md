from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = ROOT / "editor/static/sample-class-sprites"
AI_ROOT = ROOT / "editor/static/ai-class-sprites"
SOURCE_ROOT = (
    ROOT
    / "docs/assets/ai-class-source/latest/"
    / "sample-class-variants-v4-free-five"
)


class SampleClassSpriteAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (STATIC_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        cls.ai_manifest = json.loads(
            (AI_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        cls.validation = json.loads(
            (STATIC_ROOT / "validation-report.json").read_text(encoding="utf-8")
        )

    def test_catalog_has_five_samples_for_each_actual_tree_class(self) -> None:
        groups = self.manifest["groups"]
        self.assertEqual(len(groups), 5)
        self.assertEqual(
            {
                (row["commander_id"], row["class_id"])
                for row in groups
            },
            {
                (1, 0x22),
                (2, 0x18),
                (3, 0x18),
                (5, 0x18),
                (10, 0x18),
            },
        )
        for group in groups:
            self.assertTrue(group["complete"])
            self.assertEqual(group["expected_sample_count"], 5)
            self.assertEqual(len(group["samples"]), 5)
            self.assertEqual(
                [sample["id"] for sample in group["samples"]],
                [f"{number:02d}" for number in range(1, 6)],
            )
            self.assertFalse(any(sample["preserved"] for sample in group["samples"]))

    def test_published_assets_are_native_and_identity_locked(self) -> None:
        self.assertEqual(
            self.manifest["asset_version"],
            "sample-classes-v6-elwin-purple-ornament",
        )
        self.assertTrue(self.validation["all_accepted"])
        self.assertEqual(len(self.validation["diversity_groups"]), 5)
        self.assertTrue(
            all(row["accepted"] for row in self.validation["diversity_groups"])
        )
        for group in self.manifest["groups"]:
            identity_metadata = json.loads(
                (
                    SOURCE_ROOT
                    / group["id"]
                    / "references/identity-mask-expanded.json"
                ).read_text(encoding="utf-8")
            )
            lock_points = [tuple(point) for point in identity_metadata["points"]]
            policy = json.loads(
                (SOURCE_ROOT / group["id"] / "design-policy.json").read_text(
                    encoding="utf-8"
                )
            )
            with Image.open(
                AI_ROOT
                / str(group["commander_id"])
                / f"{group['class_id']:02X}.png"
            ) as opened:
                identity_source = opened.convert("RGBA")
            centers = {
                row["sample"]: row
                for row in json.loads(
                    (SOURCE_ROOT / group["id"] / "centering-report.json").read_text(
                        encoding="utf-8"
                    )
                )
            }
            for sample in group["samples"]:
                variant_points = {
                    tuple(point)
                    for point in policy.get(
                        "identity_color_variant_points_by_sample",
                        {},
                    ).get(sample["id"], [])
                }
                free_points = {
                    tuple(point)
                    for point in policy.get("identity_color_free_points", [])
                }
                ai_path = ROOT / "editor/static" / sample["ai_source"]
                logical_path = ROOT / "editor/static" / sample["logical16"]
                preview_path = ROOT / "editor/static" / sample["preview"]
                self.assertTrue(ai_path.is_file(), ai_path)
                self.assertTrue(logical_path.is_file(), logical_path)
                self.assertTrue(preview_path.is_file(), preview_path)
                with Image.open(ai_path) as opened:
                    self.assertLessEqual(max(opened.size), 384)
                    self.assertGreaterEqual(min(opened.size), 128)
                with Image.open(logical_path) as opened:
                    logical = opened.convert("RGBA")
                self.assertEqual(logical.size, (16, 16))
                colors = {
                    color
                    for _, color in logical.getcolors(maxcolors=256) or []
                    if color[3]
                }
                self.assertLessEqual(len(colors), 15)
                self.assertNotIn((0, 0, 0, 255), colors)
                self.assertNotIn((255, 0, 255, 255), colors)
                self.assertIsNotNone(logical.getchannel("A").getbbox())
                opaque = sum(
                    1 for color in logical.get_flattened_data() if color[3]
                )
                self.assertGreaterEqual(opaque, 55)
                self.assertLessEqual(opaque, 245)
                self.assertLessEqual(abs(centers[sample["id"]]["center_offset_x"]), 1.0)
                self.assertLessEqual(abs(centers[sample["id"]]["center_offset_y"]), 0.5)
                for point in set(lock_points) - free_points - variant_points:
                    self.assertEqual(
                        logical.getpixel(point),
                        identity_source.getpixel(point),
                        f"{group['id']} {sample['id']} identity {point}",
                    )
                expected_variant_pixels = policy.get(
                    "identity_color_variant_expected_pixels_by_sample",
                    {},
                ).get(sample["id"], {})
                if expected_variant_pixels:
                    self.assertTrue(variant_points)
                    expected_points = {
                        tuple(int(value) for value in key.split(","))
                        for key in expected_variant_pixels
                    }
                    self.assertEqual(expected_points, variant_points)
                    for key, expected_variant in expected_variant_pixels.items():
                        point = tuple(
                            int(value) for value in key.split(",")
                        )
                        expected_rgba = (
                            int(expected_variant[1:3], 16),
                            int(expected_variant[3:5], 16),
                            int(expected_variant[5:7], 16),
                            255,
                        )
                        self.assertEqual(
                            logical.getpixel(point),
                            expected_rgba,
                            f"{group['id']} {sample['id']} variant {point}",
                        )
                with Image.open(preview_path) as opened:
                    self.assertEqual(opened.size, (256, 256))

    def test_ai_originals_are_centered_before_native_conversion(self) -> None:
        for group in self.manifest["groups"]:
            report = json.loads(
                (SOURCE_ROOT / group["id"] / "centering-report.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(report), 5)
            for row in report:
                self.assertLessEqual(abs(row["center_offset_x"]), 1.0)
                self.assertLessEqual(abs(row["center_offset_y"]), 0.5)

    def test_unfinished_rows_use_one_approved_template_shape(self) -> None:
        for group in self.manifest["groups"]:
            root = SOURCE_ROOT / group["id"]
            points = {
                tuple(point)
                for point in json.loads(
                    (root / "references/identity-mask-expanded.json").read_text(
                        encoding="utf-8"
                    )
                )["points"]
            }
            template_class = 0x20 if group["id"] == "01-elwin-22-hero" else 0x14
            with Image.open(
                AI_ROOT / str(group["commander_id"]) / f"{template_class:02X}.png"
            ) as opened:
                template = opened.convert("RGBA")
            candidate_alpha = []
            for sample in group["samples"]:
                with Image.open(
                    ROOT / "editor/static" / sample["logical16"]
                ) as opened:
                    logical = opened.convert("RGBA")
                candidate_alpha.append(
                    bytes(logical.getchannel("A").get_flattened_data())
                )
                for y in range(16):
                    for x in range(16):
                        if (x, y) in points:
                            continue
                        self.assertEqual(
                            bool(logical.getpixel((x, y))[3]),
                            bool(template.getpixel((x, y))[3]),
                            f"{group['id']} {sample['id']} template shape {(x, y)}",
                        )
            self.assertEqual(len(set(candidate_alpha)), 1, group["id"])

    def test_editor_exposes_sample_tab_and_non_saving_import(self) -> None:
        html = (ROOT / "editor/static/index.html").read_text(encoding="utf-8")
        script = (ROOT / "editor/static/app.js").read_text(encoding="utf-8")
        styles = (ROOT / "editor/static/styles.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'data-tab="aiClasses">New 클래스</button>\n'
            '      <button class="tab" type="button" '
            'data-tab="sampleClasses">샘플 클래스</button>',
            html,
        )
        self.assertIn('id="sampleClassesPanel"', html)
        self.assertIn("async function loadClassSample(group, sample)", script)
        self.assertIn("state.pixels = imported", script)
        self.assertIn("저장 전까지 기존 디자인은 바뀌지 않습니다", script)
        self.assertIn('class="sampleLoadButton sampleCompactChoice"', script)
        self.assertIn("grid-template-columns: 170px minmax(0, 1fr)", styles)
        self.assertIn("grid-auto-flow: column", styles)
        self.assertIn("width: 48px", styles)
        loader = script.split(
            "async function loadClassSample(group, sample)", 1
        )[1].split("function collectClassEdits", 1)[0]
        self.assertNotIn('fetch("/api/ai-class-design"', loader)


if __name__ == "__main__":
    unittest.main()
