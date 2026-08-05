from collections import Counter
from pathlib import Path
import json
import tempfile
import unittest

from PIL import Image

from editor.server import (
    normalize_ai_design_pixels,
    preserve_locked_ai_design_pixels,
)
from tools.build_class_sprite_assets import (
    DEFAULT_ROM,
    render_sprite,
)
from tools.build_test_class_sprite_assets import (
    protected_face_points,
)
from tools.build_shared_hein_martial_variants import (
    JESSICA_HIGH_LORD_CAPE_POINTS,
    LANA_HIGH_LORD_GRAY_FOOT_POINTS,
)
from tools.build_shared_hein_class_variants import (
    JESSICA_MAGE_RED_SHOULDER_DARK_POINTS,
    JESSICA_MAGE_RED_SHOULDER_MAIN_POINTS,
)
from tools.polish_jessica_swordmaster import POLISH_PIXELS
from tools.build_ai_class_sprite_assets import (
    ELWIN_SWORDMASTER_CAPE_POINTS,
    MEGA_DRIVE_CHANNEL_LEVELS,
    ROM_INK,
    SHARED_DARK_BOUNDARY_REFERENCE_POINTS,
    accent_hues,
    identity_locked_character_sprite,
    load_mount_mask_overrides,
    pixelize_cell,
    protected_eye_points,
    remove_magenta_background,
)
from tools.pixellab_elwin_inpaint import inpaint_mask as pixellab_inpaint_mask


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

    def assert_template_plus_dark_boundaries(
        self,
        actual: Image.Image,
        template: Image.Image,
        class_id: int,
    ) -> None:
        changed = {
            (x, y)
            for y in range(16)
            for x in range(16)
            if actual.getpixel((x, y)) != template.getpixel((x, y))
        }
        self.assertTrue(
            changed.issubset(
                SHARED_DARK_BOUNDARY_REFERENCE_POINTS[class_id]
            )
        )
        for point in changed:
            self.assertEqual(template.getpixel(point), (0, 0, 0, 0))
            self.assertEqual(actual.getpixel(point), ROM_INK)

    def test_test_change_assets_are_preview_only_and_complete(self):
        manifest = self.test_manifest
        self.assertEqual(manifest["commander_count"], 10)
        self.assertEqual(manifest["redesigned_count"], 111)
        self.assertIn("preview PNG assets only", manifest["rom_effect"])
        rows = [
            row
            for commander in manifest["commanders"].values()
            for row in commander["classes"].values()
        ]
        self.assertEqual(len(rows), 180)
        self.assertEqual(sum(row["redesigned"] for row in rows), 111)
        for row in rows:
            path = TEST_ASSET_DIR / row["file"]
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (16, 16))
                self.assertEqual(image.mode, "RGBA")

    def test_mount_mask_document_and_original_pixel_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mount-masks.json"
            path.write_text(
                json.dumps({
                    "version": 1,
                    "masks": {
                        "2:19": [[15, 15], [14, 15], [15, 15]],
                        "5:0B": [],
                    },
                }),
                encoding="utf-8",
            )
            masks = load_mount_mask_overrides(path)
        self.assertEqual(masks[(2, 0x19)], {(14, 15), (15, 15)})
        self.assertEqual(masks[(5, 0x0B)], set())

        row = self.ai_manifest["commanders"]["2"]["classes"]["25"]
        original = render_sprite(
            self.rom,
            row["face_source_sprite_id"],
            1,
        )
        generated = Image.new("RGBA", (16, 16), (182, 0, 0, 255))
        transparent_point = next(
            (x, y)
            for y in reversed(range(16))
            for x in reversed(range(16))
            if not original.getpixel((x, y))[3]
        )
        visible_point = next(
            (x, y)
            for y in reversed(range(16))
            for x in reversed(range(16))
            if original.getpixel((x, y))[3]
        )
        converted, _, _, _ = identity_locked_character_sprite(
            generated,
            original,
            [(182, 0, 0, 255)],
            set(),
            additional_locked_points={
                transparent_point,
                visible_point,
            },
            preserve_generated_palette=True,
        )
        self.assertEqual(
            converted.getpixel(transparent_point),
            original.getpixel(transparent_point),
        )
        self.assertEqual(
            converted.getpixel(visible_point),
            original.getpixel(visible_point),
        )

    def test_elwin_mounted_v2_uses_current_face_and_mount_masks(self):
        source_dir = (
            ROOT
            / "docs/assets/ai-class-source/latest/elwin-mounted-v2"
        )
        report = json.loads(
            (source_dir / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        mount_document = json.loads(
            (ROOT / "editor/ai_mount_masks.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(report["all_accepted"])
        reports = {
            int(row["class_id"], 16): row
            for row in report["classes"]
        }
        for class_id, filename in {
            0x0C: "0C-highlander.png",
            0x1D: "1D-silver-knight.png",
        }.items():
            row = self.ai_manifest["commanders"]["1"]["classes"][
                str(class_id)
            ]
            identity_points = {
                tuple(point)
                for point in row["identity_lock_points"]
            }
            mount_points = {
                tuple(point)
                for point in mount_document["masks"][
                    f"1:{class_id:02X}"
                ]
            }
            self.assertEqual(
                row["mount_lock_pixel_count"],
                len(mount_points),
            )
            self.assertEqual(row["mount_lock_mode"], "custom")
            self.assertFalse(row["mount_mask_pending_rebuild"])
            self.assertIn("원작 ROM 16×16", row["ai_source_kind"])
            self.assertIn("원작 ROM 기수·말", row["feature"])
            self.assertEqual(
                reports[class_id]["identity_matches"],
                len(identity_points),
            )
            self.assertEqual(
                reports[class_id]["mount_matches"],
                len(mount_points),
            )
            self.assertTrue(reports[class_id]["accepted"])

            original = render_sprite(
                self.rom,
                row["face_source_sprite_id"],
                1,
            )
            final = Image.open(
                AI_ASSET_DIR / "1" / f"{class_id:02X}.png"
            ).convert("RGBA")
            for point in identity_points - mount_points:
                self.assertEqual(
                    final.getpixel(point),
                    original.getpixel(point),
                )
            for point in mount_points:
                self.assertEqual(
                    bool(final.getpixel(point)[3]),
                    bool(original.getpixel(point)[3]),
                )
            self.assertTrue(
                all(
                    any(final.getpixel((x, y))[3] for x in range(16))
                    for y in range(16)
                )
            )
            self.assertTrue(
                all(
                    any(final.getpixel((x, y))[3] for y in range(16))
                    for x in range(16)
                )
            )
            visible_colors = {
                color
                for _, color in final.getcolors(maxcolors=256) or []
                if color[3]
            }
            self.assertLessEqual(len(visible_colors), 15)
            self.assertNotIn((0, 0, 0, 255), visible_colors)
            logical = remove_magenta_background(
                Image.open(
                    source_dir / "logical16" / filename
                ).convert("RGBA")
            )
            self.assertEqual(logical.size, (16, 16))

    def test_reserved_class_template_masters_are_not_overwritten(self):
        policy = json.loads(
            (ROOT / "editor/ai_class_template_policy.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            policy["protected_master_keys"],
            ["1:0B", "5:0B", "1:1A", "5:1A"],
        )
        protected_dir = (
            ROOT
            / "docs/assets/ai-class-source/"
            "class-template-masters/protected"
        )
        elwin_high_lord_master = (
            protected_dir / "01-0B-elwin-high-lord.png"
        )
        self.assertEqual(
            elwin_high_lord_master.read_bytes(),
            (
                ROOT
                / "docs/assets/ai-class-source/latest/"
                "shared-lord-elwin-high-lord-v1/master/"
                "elwin-0B-high-lord-user-approved.png"
            ).read_bytes(),
        )
        self.assertEqual(
            elwin_high_lord_master.read_bytes(),
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "elwin-lord-high-lord-before-swap-v1/"
                "01-0B-high-lord-v47.png"
            ).read_bytes(),
        )
        self.assertNotEqual(
            (AI_ASSET_DIR / "1/0B.png").read_bytes(),
            elwin_high_lord_master.read_bytes(),
        )
        hein_high_lord_master = (
            protected_dir / "05-0B-hein-high-lord.png"
        )
        self.assertEqual(
            hein_high_lord_master.read_bytes(),
            (
                ROOT
                / "docs/assets/ai-class-source/latest/"
                "shared-high-lord-hein-v1/master/"
                "hein-0B-high-lord-user-approved.png"
            ).read_bytes(),
        )
        self.assertEqual(
            hein_high_lord_master.read_bytes(),
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "hein-high-lord-before-green-cape-v1/"
                "05-0B-v47.png"
            ).read_bytes(),
        )
        self.assertNotEqual(
            (AI_ASSET_DIR / "5/0B.png").read_bytes(),
            hein_high_lord_master.read_bytes(),
        )
        self.assertNotEqual(
            (AI_ASSET_DIR / "1/1A.png").read_bytes(),
            (protected_dir / "01-1A-elwin-swordmaster.png").read_bytes(),
        )
        hein_swordmaster = Image.open(
            AI_ASSET_DIR / "5/1A.png"
        ).convert("RGBA")
        green_expected = Image.open(
            protected_dir / "05-1A-hein-swordmaster.png"
        ).convert("RGBA")
        green_ramp = {
            (73, 36, 36, 255): (36, 109, 0, 255),
            (146, 36, 36, 255): (36, 182, 36, 255),
        }
        for y in range(16):
            for x in range(16):
                point = (x, y)
                color = green_expected.getpixel(point)
                green_expected.putpixel(point, green_ramp.get(color, color))
        self.assert_template_plus_dark_boundaries(
            hein_swordmaster,
            green_expected,
            0x1A,
        )
        hein_swordmaster_colors = Counter(
            color
            for color in hein_swordmaster.get_flattened_data()
            if color[3]
        )
        self.assertGreaterEqual(
            hein_swordmaster_colors[(36, 182, 36, 255)],
            20,
        )
        self.assertNotIn((146, 36, 36, 255), hein_swordmaster_colors)

    def test_shared_classes_close_unlocked_transparent_boundaries(self):
        for commander_id, commander in self.ai_manifest[
            "commanders"
        ].items():
            if commander_id == "1":
                continue
            for class_id, points in (
                SHARED_DARK_BOUNDARY_REFERENCE_POINTS.items()
            ):
                row = commander["classes"].get(str(class_id))
                if not row or not row["redesigned"]:
                    continue
                locked = {
                    tuple(point)
                    for point in (
                        row["identity_lock_points"]
                        + row["mount_lock_points"]
                    )
                }
                image = Image.open(
                    AI_ASSET_DIR / row["file"]
                ).convert("RGBA")
                for point in points - locked:
                    self.assertTrue(
                        image.getpixel(point)[3],
                        f"{commander_id}:{class_id:02X} leaks at {point}",
                    )

    def test_hein_martial_templates_apply_to_selected_commanders(self):
        policy = json.loads(
            (ROOT / "editor/ai_class_template_policy.json").read_text(
                encoding="utf-8"
            )
        )
        active_by_class = {
            entry["class_id"]: entry
            for entry in policy["active_templates"]
        }
        expected_targets = {
            0x0B: (1, 2, 3, 4, 5, 6, 7, 8, 10),
            0x1A: (5, 7, 8, 10),
        }
        source_dirs = {
            0x0B: (
                ROOT
                / "docs/assets/ai-class-source/latest/"
                "shared-high-lord-hein-v1"
            ),
            0x1A: (
                ROOT
                / "docs/assets/ai-class-source/latest/"
                "shared-swordmaster-hein-v1"
            ),
        }
        for class_id, commander_ids in expected_targets.items():
            class_key = f"{class_id:02X}"
            entry = active_by_class[class_key]
            self.assertEqual(entry["master"], f"5:{class_key}")
            self.assertEqual(
                entry["targets"],
                [
                    f"{commander_id}:{class_key}"
                    for commander_id in commander_ids
                ],
            )
            if class_id == 0x1A:
                self.assertEqual(
                    entry["excluded_protected_masters"],
                    ["1:1A"],
                )
            else:
                self.assertEqual(
                    entry["preserved_reassigned_design"],
                    "1:0B -> 1:04",
                )
            report = json.loads(
                (
                    source_dirs[class_id]
                    / "validation-report.json"
                ).read_text(encoding="utf-8")
            )
            self.assertTrue(report["all_accepted"])
            self.assertEqual(
                {
                    row["commander_id"]
                    for row in report["classes"]
                },
                set(commander_ids),
            )
            for commander_id in commander_ids:
                row = self.ai_manifest["commanders"][
                    str(commander_id)
                ]["classes"][str(class_id)]
                self.assertIn(
                    "헤인 사용자 편집",
                    row["ai_source_kind"],
                )
                self.assertIn(
                    "공통 16×16 클래스 템플릿",
                    row["ai_source_kind"],
                )
                image = Image.open(
                    AI_ASSET_DIR
                    / str(commander_id)
                    / f"{class_id:02X}.png"
                ).convert("RGBA")
                self.assertEqual(
                    image.getchannel("A").getbbox(),
                    (0, 0, 16, 16),
                )
                visible_colors = {
                    color
                    for _, color in (
                        image.getcolors(maxcolors=256) or []
                    )
                    if color[3]
                }
                self.assertLessEqual(len(visible_colors), 15)
                self.assertNotIn((0, 0, 0, 255), visible_colors)
                original = render_sprite(
                    self.rom,
                    row["face_source_sprite_id"],
                    1,
                )
                dx, dy = row.get("identity_translation") or (0, 0)
                if row["identity_translation_applied_in_override"]:
                    continue
                for point in row["identity_lock_points"]:
                    target = tuple(point)
                    source_point = (target[0] - dx, target[1] - dy)
                    if not original.getpixel(source_point)[3]:
                        continue
                    self.assertEqual(
                        image.getpixel(target),
                        original.getpixel(source_point),
                    )
                self.assertEqual(
                    row["identity_lock_transparency_mode"],
                    "equipment_priority",
                )
                if commander_id in {2, 3}:
                    transparent_mask_points = {
                        tuple(point)
                        for point in row["identity_lock_points"]
                        if not original.getpixel(tuple(point))[3]
                    }
                    if (commander_id, class_id) == (2, 0x0B):
                        # Liana High Lord has a dedicated 72-point user mask.
                        # Its only transparent point is outside the approved
                        # cape, so the equipment-priority overlap check does
                        # not apply to this one saved design.
                        self.assertEqual(len(transparent_mask_points), 1)
                    else:
                        self.assertTrue(
                            any(
                                image.getpixel(point)[3]
                                for point in transparent_mask_points
                            ),
                            (
                                f"{commander_id}:{class_id:02X} erased all "
                                "equipment inside transparent hair-mask "
                                "pixels"
                            ),
                        )

            elwin_row = self.ai_manifest["commanders"]["1"][
                "classes"
            ][str(class_id)]
            if class_id == 0x0B:
                self.assertIn(
                    "헤인 사용자 편집 하이로드",
                    elwin_row["ai_source_kind"],
                )
                self.assertIn(
                    "공통 16×16 클래스 템플릿",
                    elwin_row["ai_source_kind"],
                )
                self.assertTrue(elwin_row["design_override"])
                self.assertGreater(
                    elwin_row["design_revision"],
                    elwin_row["superseded_design_revision"],
                )
                self.assertFalse(
                    elwin_row["design_override_superseded"]
                )
                self.assertEqual(
                    elwin_row["superseded_design_revision"], 0
                )
            else:
                self.assertNotIn(
                    "공통 16×16 클래스 템플릿",
                    elwin_row["ai_source_kind"],
                )

        hein_high_lord_row = self.ai_manifest["commanders"]["5"][
            "classes"
        ][str(0x0B)]
        self.assertFalse(hein_high_lord_row["design_override"])
        self.assertTrue(
            hein_high_lord_row["design_override_superseded"]
        )
        hein_high_lord = Image.open(
            AI_ASSET_DIR / "5/0B.png"
        ).convert("RGBA")
        colors = Counter(
            color for color in hein_high_lord.getdata() if color[3]
        )
        self.assertGreaterEqual(colors[(36, 182, 36, 255)], 20)
        self.assertNotIn((146, 36, 0, 255), colors)

    def test_jessica_high_lord_reuses_hein_design_with_purple_cape(self):
        row = self.ai_manifest["commanders"]["10"]["classes"][
            str(0x0B)
        ]
        self.assertEqual(row["identity_translation"], [1, 0])
        self.assertTrue(
            row["identity_translation_applied_in_override"]
        )
        self.assertGreater(row["identity_lock_pixel_count"], 0)
        self.assertTrue(row["design_override"])
        self.assertFalse(row["design_override_superseded"])
        self.assertIn("자주·보라·연보라", row["feature"])
        self.assertIn("오른쪽 1칸", row["feature"])

        source = Image.open(
            ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-high-lord-hein-v1/logical16/10-0B.png"
        ).convert("RGBA")
        final = Image.open(AI_ASSET_DIR / "10/0B.png").convert("RGBA")
        cape_colors = {
            source.getpixel(point)
            for point in JESSICA_HIGH_LORD_CAPE_POINTS
        }
        self.assertEqual(
            cape_colors,
            {
                (109, 219, 255, 255),
                (73, 146, 255, 255),
                (36, 73, 219, 255),
            },
        )
        final_cape_colors = {
            final.getpixel(point)
            for point in JESSICA_HIGH_LORD_CAPE_POINTS
        }
        self.assertTrue(
            {
                (73, 0, 109, 255),
                (182, 73, 219, 255),
                (219, 109, 255, 255),
            }.issubset(final_cape_colors)
        )
        self.assertFalse(final_cape_colors & cape_colors)

    def test_lana_high_lord_uses_original_cyan_armor_and_blue_cape(self):
        row = self.ai_manifest["commanders"]["3"]["classes"][
            str(0x0B)
        ]
        self.assertFalse(row["design_override"])
        self.assertTrue(row["design_override_superseded"])
        self.assertIn("캐릭터별 고유 주색·보조색", row["feature"])
        self.assertIn("짙은 경계", row["feature"])
        image = Image.open(AI_ASSET_DIR / "3/0B.png").convert("RGBA")
        colors = Counter(color for color in image.getdata() if color[3])
        self.assertGreaterEqual(colors[(109, 219, 255, 255)], 20)
        cape_colors = {
            image.getpixel(point)
            for point in JESSICA_HIGH_LORD_CAPE_POINTS
        }
        self.assertEqual(
            cape_colors,
            {
                (73, 109, 255, 255),
                (0, 0, 219, 255),
            },
        )
        self.assertTrue(
            all(
                image.getpixel(point) == (146, 146, 146, 255)
                for point in LANA_HIGH_LORD_GRAY_FOOT_POINTS
            )
        )

    def test_jessica_mage_uses_blue_robe_and_original_red_shoulders(self):
        row = self.ai_manifest["commanders"]["10"]["classes"][
            str(0x13)
        ]
        self.assertFalse(row["design_override"])
        self.assertTrue(row["design_override_superseded"])
        self.assertIn("자주색 망토", row["feature"])
        self.assertIn("은보라 로브", row["feature"])
        image = Image.open(AI_ASSET_DIR / "10/13.png").convert("RGBA")
        colors = {
            color for color in image.getdata() if color[3]
        }
        self.assertTrue({
            (219, 146, 255, 255),
            (146, 73, 182, 255),
            (73, 36, 109, 255),
        }.issubset(colors))
        self.assertIn((0, 0, 219, 255), colors)

    def test_jessica_swordmaster_keeps_bridges_with_purple_equipment(self):
        before = Image.open(
            ROOT
            / "docs/assets/ai-class-source/archive/"
            "jessica-swordmaster-before-polish-v1/"
            "10-1A-editor-v62.png"
        ).convert("RGBA")
        after = Image.open(AI_ASSET_DIR / "10/1A.png").convert("RGBA")
        changed = {
            (x, y)
            for y in range(16)
            for x in range(16)
            if before.getpixel((x, y)) != after.getpixel((x, y))
        }
        self.assertGreaterEqual(len(changed), len(POLISH_PIXELS))
        visible_colors = {
            color for color in after.getdata() if color[3]
        }
        self.assertTrue(
            {(73, 0, 109, 255), (182, 73, 219, 255)}.issubset(
                visible_colors
            )
        )
        self.assertGreaterEqual(
            sum(after.getpixel((x, 9))[3] != 0 for x in range(4, 13)),
            8,
        )
        row = self.ai_manifest["commanders"]["10"]["classes"][
            str(0x1A)
        ]
        self.assertTrue(row["design_override"])
        self.assertTrue(
            row["identity_translation_applied_in_override"]
        )
        self.assertIn("사용자 16×16 디자인 편집 적용", row["feature"])
        self.assertIn("짙은 경계", row["feature"])

    def test_hein_archmage_uses_lester_template_over_saved_override(self):
        row = self.ai_manifest["commanders"]["5"]["classes"][
            str(0x14)
        ]
        self.assertIn(
            "엘윈 사용자 리터칭 아크메이지",
            row["ai_source_kind"],
        )
        self.assertIn(
            "공통 16×16 클래스 템플릿",
            row["ai_source_kind"],
        )
        self.assertFalse(row["design_override"])
        self.assertTrue(row["design_override_superseded"])
        self.assertGreater(row["superseded_design_revision"], 0)
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "hein-archmage-before-lester-template-v1/"
                "05-14-v47.png"
            ).is_file()
        )
        expected = Image.open(
            ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-elwin-magic-v1/logical16/05-14.png"
        ).convert("RGBA")
        actual = Image.open(
            AI_ASSET_DIR / "5/14.png"
        ).convert("RGBA")
        self.assert_template_plus_dark_boundaries(actual, expected, 0x14)

    def test_aaron_lord_separates_ochre_cape_from_blue_shield(self):
        image = Image.open(
            AI_ASSET_DIR / "8/04.png"
        ).convert("RGBA")
        cape_points = {
            (4, 12),
            (2, 13),
            (3, 13),
            (4, 13),
            (1, 14),
            (2, 14),
            (3, 14),
            (1, 15),
            (2, 15),
            (3, 15),
        }
        cape_colors = {
            image.getpixel(point)
            for point in cape_points
        }
        shield_colors = {
            image.getpixel((x, y))
            for y in range(9, 16)
            for x in range(11, 16)
            if image.getpixel((x, y))[3]
        }
        self.assertEqual(cape_colors, {(219, 146, 36, 255)})
        self.assertIn((73, 109, 255, 255), shield_colors)
        self.assertIn((109, 219, 255, 255), shield_colors)
        self.assertNotIn((219, 146, 36, 255), shield_colors)
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "aaron-before-ochre-capes-v1/08-04-v51.png"
            ).is_file()
        )
        expected = Image.open(
            ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-lord-elwin-high-lord-v1/logical16/08-04.png"
        ).convert("RGBA")
        self.assertEqual(image.getchannel("A").getbbox(), (0, 0, 16, 16))

    def test_elwin_lord_uses_high_lord_style_shield(self):
        image = Image.open(
            AI_ASSET_DIR / "1/04.png"
        ).convert("RGBA")
        shield_colors = {
            image.getpixel((x, y))
            for y in range(9, 15)
            for x in range(11, 16)
            if image.getpixel((x, y))[3]
        }
        self.assertIn((36, 73, 219, 255), shield_colors)
        self.assertIn((255, 182, 0, 255), shield_colors)
        self.assertIn((219, 182, 109, 255), shield_colors)
        self.assertTrue(
            all(
                image.getpixel(point) == ROM_INK
                for point in SHARED_DARK_BOUNDARY_REFERENCE_POINTS[0x04]
            )
        )
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "elwin-lord-before-high-lord-shield-v1/"
                "01-04-v54.png"
            ).is_file()
        )

    def test_aaron_mage_uses_white_and_ochre_cape(self):
        image = Image.open(
            AI_ASSET_DIR / "8/13.png"
        ).convert("RGBA")
        cape_colors = {
            image.getpixel((x, y))
            for y in range(7, 16)
            for x in range(0, 8)
            if image.getpixel((x, y))[3]
        }
        all_colors = {
            color
            for _, color in (image.getcolors(maxcolors=256) or [])
            if color[3]
        }
        self.assertIn((219, 146, 36, 255), cape_colors)
        self.assertIn((255, 255, 255, 255), cape_colors)
        self.assertIn((73, 109, 255, 255), all_colors)
        self.assertIn((109, 219, 255, 255), all_colors)
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "aaron-magic-before-deeper-blue-v1/08-13-v49.png"
            ).is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "aaron-before-sky-blue-v1/08-13-v50.png"
            ).is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "aaron-before-ochre-capes-v1/08-13-v51.png"
            ).is_file()
        )

    def test_aaron_archmage_uses_white_and_ochre_cape(self):
        row = self.ai_manifest["commanders"]["8"]["classes"][
            str(0x14)
        ]
        self.assertEqual(
            row["identity_lock_transparency_mode"],
            "equipment_priority",
        )
        image = Image.open(
            AI_ASSET_DIR / "8/14.png"
        ).convert("RGBA")
        all_colors = {
            color
            for _, color in (image.getcolors(maxcolors=256) or [])
            if color[3]
        }
        self.assertIn((219, 146, 36, 255), all_colors)
        self.assertIn((255, 255, 255, 255), all_colors)
        self.assertGreater(
            list(image.getdata()).count((255, 255, 255, 255)),
            list(image.getdata()).count((219, 146, 36, 255)),
        )
        self.assertIn((73, 109, 255, 255), all_colors)
        self.assertIn((109, 219, 255, 255), all_colors)
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "aaron-magic-before-deeper-blue-v1/08-14-v49.png"
            ).is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "aaron-before-sky-blue-v1/08-14-v50.png"
            ).is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "aaron-before-ochre-capes-v1/08-14-v51.png"
            ).is_file()
        )
        expected = Image.open(
            ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-archmage-lester-v1/logical16/08-14.png"
        ).convert("RGBA")
        self.assertEqual(image.getchannel("A").getbbox(), (0, 0, 16, 16))

    def test_aaron_high_lord_uses_knight_shield_blue(self):
        image = Image.open(
            AI_ASSET_DIR / "8/0B.png"
        ).convert("RGBA")
        shield_colors = {
            image.getpixel((x, y))
            for y in range(8, 14)
            for x in range(0, 4)
        }
        self.assertIn((73, 109, 255, 255), shield_colors)
        self.assertIn((109, 219, 255, 255), shield_colors)
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "aaron-before-sky-blue-v1/08-0B-v50.png"
            ).is_file()
        )

    def test_aaron_swordmaster_uses_latest_saved_face_mask(self):
        mask_document = json.loads(
            (ROOT / "editor/ai_identity_masks.json").read_text(
                encoding="utf-8"
            )
        )
        row = self.ai_manifest["commanders"]["8"]["classes"][
            str(0x1A)
        ]
        self.assertEqual(
            {tuple(point) for point in row["identity_lock_points"]},
            {
                tuple(point)
                for point in mask_document["masks"]["8:1A"]
            },
        )
        original = render_sprite(
            self.rom,
            row["face_source_sprite_id"],
            1,
        )
        actual = Image.open(
            AI_ASSET_DIR / "8/1A.png"
        ).convert("RGBA")
        for point in row["identity_lock_points"]:
            point = tuple(point)
            self.assertEqual(
                actual.getpixel(point),
                original.getpixel(point),
            )
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "aaron-swordmaster-before-face-mask-refresh-v1/"
                "08-1A-v48.png"
            ).is_file()
        )

    def test_elwin_high_lord_template_applies_only_to_fighter_lords(self):
        source_dir = (
            ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-lord-elwin-high-lord-v1"
        )
        report = json.loads(
            (source_dir / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(report["all_accepted"])
        self.assertEqual(
            {
                row["commander_id"]
                for row in report["classes"]
            },
            {1, 4, 6, 7, 8},
        )
        self.assertEqual(
            {
                row["commander_id"]
                for row in report["excluded_rom_base_lords"]
            },
            {2, 3, 5, 10},
        )
        self.assertEqual(
            report["missing_lord_class"],
            [{"commander_id": 9, "name": "레스터"}],
        )
        for commander_id in (1, 4, 6, 7, 8):
            row = self.ai_manifest["commanders"][
                str(commander_id)
            ]["classes"][str(0x04)]
            self.assertGreater(row["group_rank"], 0)
            self.assertIn(
                "엘윈 사용자 편집 하이로드 기반 로드",
                row["ai_source_kind"],
            )
            self.assertEqual(
                row["identity_lock_transparency_mode"],
                "equipment_priority",
            )
            image = Image.open(
                AI_ASSET_DIR / str(commander_id) / "04.png"
            ).convert("RGBA")
            self.assertEqual(
                image.getchannel("A").getbbox(),
                (0, 0, 16, 16),
            )
            self.assertNotIn(
                (0, 0, 0, 255),
                {
                    color
                    for _, color in (
                        image.getcolors(maxcolors=256) or []
                    )
                    if color[3]
                },
            )
            if commander_id == 1:
                archive = (
                    ROOT
                    / "docs/assets/ai-class-source/archive/"
                    "elwin-lord-high-lord-before-swap-v1/"
                    "01-04-lord-v47.png"
                )
            else:
                archive = (
                    ROOT
                    / "docs/assets/ai-class-source/archive/"
                    "lord-before-elwin-high-lord-v1/"
                    f"{commander_id:02d}-04-v45.png"
                )
            self.assertTrue(archive.is_file())

        for commander_id in (2, 3, 5):
            row = self.ai_manifest["commanders"][
                str(commander_id)
            ]["classes"][str(0x04)]
            self.assertEqual(row["group_rank"], 0)
            self.assertFalse(row["redesigned"])
            original = Image.open(
                ROOT
                / "editor/static/class-sprites/commanders"
                / str(commander_id)
                / "04-p1.png"
            ).convert("RGBA")
            actual = Image.open(
                AI_ASSET_DIR / str(commander_id) / "04.png"
            ).convert("RGBA")
            self.assertEqual(actual.tobytes(), original.tobytes())

        jessica_lord = self.ai_manifest["commanders"]["10"]["classes"][
            str(0x04)
        ]
        self.assertTrue(jessica_lord["redesigned"])
        self.assertIn("자주·보라·연보라", jessica_lord["feature"])

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

    def test_elwin_lord_and_high_lord_use_original_bright_red_capes(self):
        for class_id, minimum_bright_red in (
            (0x04, 14),
            (0x0B, 20),
        ):
            image = Image.open(
                AI_ASSET_DIR / "1" / f"{class_id:02X}.png"
            ).convert("RGBA")
            colors = Counter(
                color for color in image.getdata() if color[3]
            )
            self.assertGreaterEqual(
                colors[(219, 0, 0, 255)],
                minimum_bright_red,
            )
        archive_dir = (
            ROOT
            / "docs/assets/ai-class-source/archive/"
            "elwin-capes-before-original-red-v1"
        )
        self.assertTrue((archive_dir / "01-04-v48.png").is_file())
        self.assertTrue((archive_dir / "01-0B-v48.png").is_file())

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

    def test_ai_assets_keep_coherent_source_cells_at_full_16_extent(self):
        manifest = self.ai_manifest
        self.assertEqual(len(manifest["ai_source_sheets"]), 9)
        self.assertTrue(
            all(
                path.startswith(
                    "docs/assets/ai-class-source/"
                    "logical16-v3/"
                )
                for path in manifest["ai_source_sheets"]
            )
        )
        self.assertEqual(manifest["commander_count"], 10)
        self.assertEqual(manifest["asset_count"], 180)
        self.assertEqual(manifest["redesigned_count"], 131)
        self.assertEqual(manifest["pending_redesign_count"], 0)
        self.assertIn("preview PNG assets only", manifest["rom_effect"])
        source_cells = set()
        rows = [
            row
            for commander in manifest["commanders"].values()
            for row in commander["classes"].values()
        ]
        for row in rows:
            path = AI_ASSET_DIR / row["file"]
            self.assertTrue(path.is_file(), path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (16, 16))
                source = render_sprite(
                    self.rom,
                    row["face_source_sprite_id"],
                    1,
                )
                eye_points = protected_eye_points(source)
                dx, dy = row.get("identity_translation") or (0, 0)
                manifest_eye_points = {
                    (x + dx, y + dy) for x, y in eye_points
                }
                generated_identity = (
                    row["identity_lock_mode"] == "generated"
                )
                if generated_identity:
                    self.assertEqual(row["eye_lock_pixel_count"], 0)
                    self.assertEqual(row["eye_lock_points"], [])
                else:
                    self.assertEqual(
                        row["eye_lock_pixel_count"],
                        len(eye_points),
                    )
                    self.assertEqual(
                        row["eye_lock_points"],
                        [
                            list(point)
                            for point in sorted(manifest_eye_points)
                        ],
                    )
                if not row["redesigned"]:
                    self.assertIsNone(row["ai_source_cell_file"])
                    self.assertEqual(image.tobytes(), source.tobytes())
                    self.assertEqual(row["face_pixel_count"], 0)
                    self.assertEqual(row["identity_lock_points"], [])
                    self.assertEqual(row["identity_lock_mode"], "none")
                    self.assertEqual(
                        row["identity_lock_transparency_mode"],
                        "none",
                    )
                    continue
                self.assertIn(len(eye_points), {2, 4})
                lock_points = {
                    tuple(point)
                    for point in row["identity_lock_points"]
                }
                self.assertEqual(
                    len(lock_points),
                    row["identity_lock_pixel_count"],
                )
                if (
                    not generated_identity
                    and lock_points
                    and not row.get(
                        "identity_translation_applied_in_override",
                        False,
                    )
                    and row["file"] != "1/1A.png"
                ):
                    self.assertTrue(
                        manifest_eye_points.issubset(lock_points)
                    )
                if (
                    not row.get("identity_mask_pending_rebuild")
                    and not row.get(
                        "identity_translation_applied_in_override",
                        False,
                    )
                ):
                    for target in lock_points:
                        source_point = (
                            target[0] - dx,
                            target[1] - dy,
                        )
                        if (
                            row["identity_lock_transparency_mode"]
                            == "equipment_priority"
                            and not source.getpixel(source_point)[3]
                        ):
                            continue
                        self.assertEqual(
                            image.getpixel(target),
                            source.getpixel(source_point),
                        )
                self.assertIn(
                    row["identity_lock_mode"],
                    {"automatic", "custom", "generated"},
                )
                self.assertIn(
                    row["identity_lock_transparency_mode"],
                    {"exact", "equipment_priority", "generated"},
                )
                if generated_identity:
                    self.assertEqual(lock_points, set())
                    self.assertTrue(row["identity_mask_superseded"])
                    self.assertIsNone(row["identity_lock_box"])
                    self.assertIn(
                        "원본 얼굴 덮어쓰기 없음",
                        row["feature"],
                    )
                if (
                    row["identity_lock_transparency_mode"]
                    == "equipment_priority"
                ):
                    self.assertTrue(
                        "공통 16×16 클래스 템플릿"
                        in row["ai_source_kind"]
                        or "원작 ROM 16×16" in row["ai_source_kind"]
                        or "전용 네이티브 논리16 원화"
                        in row["ai_source_kind"]
                    )
                source_cells.add(row["ai_source_cell_file"])
                self.assertEqual(row["face_pixel_count"], 0)
                if row.get("supplemental_hidden_baseline"):
                    if row["changed_pixel_count"]:
                        self.assertNotEqual(image.tobytes(), source.tobytes())
                    else:
                        self.assertEqual(image.tobytes(), source.tobytes())
                elif (
                    row.get("ai_generated") is False
                    and row["class_name"] in {"호크나이트", "크로코나이트"}
                ):
                    self.assertEqual(image.tobytes(), source.tobytes())
                else:
                    self.assertNotEqual(
                        image.tobytes(),
                        source.tobytes(),
                    )
                self.assertEqual(
                    image.getchannel("A").getbbox()[3],
                    16,
                    "converted sprite must be aligned to the bottom row",
                )
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
        self.assertEqual(len(source_cells), 131)
        for filename in source_cells:
            self.assertTrue((AI_ASSET_DIR / filename).is_file(), filename)

    def test_hein_sorcerer_and_cleric_source_originals_are_explicit(self):
        rows = self.ai_manifest["commanders"]["5"]["classes"]
        expected_sources = {
            0x11: (
                ROOT
                / "docs/assets/ai-class-source/latest/"
                "shared-hein-classes-v1/master/"
                "hein-11-priest-user-approved.png"
            ),
            0x16: (
                ROOT
                / "docs/assets/ai-class-source/latest/"
                "shared-hein-classes-v1/master/"
                "hein-16-high-priest-user-approved.png"
            ),
        }
        for class_id, expected_source in expected_sources.items():
            row = rows[str(class_id)]
            original_path = (
                AI_ASSET_DIR / row["ai_source_original_file"]
            )
            self.assertTrue(original_path.is_file())
            self.assertEqual(
                original_path.read_bytes(),
                expected_source.read_bytes(),
            )

        sorcerer_row = rows[str(0x09)]
        self.assertEqual(sorcerer_row["identity_lock_mode"], "custom")
        self.assertGreater(sorcerer_row["identity_lock_pixel_count"], 0)
        self.assertIsNone(sorcerer_row["ai_source_original_file"])
        self.assertIn("비-AI 워록 원본", sorcerer_row["ai_source_kind"])
        with Image.open(AI_ASSET_DIR / "5/09.png") as sorcerer:
            self.assertEqual(sorcerer.size, (16, 16))
            self.assertEqual(
                sorcerer.getchannel("A").getbbox(),
                (0, 0, 16, 16),
            )
            visible = {
                color for color in sorcerer.convert("RGBA").getdata()
                if color[3]
            }
            self.assertLessEqual(len(visible), 15)
            self.assertTrue(
                all(
                    channel in MEGA_DRIVE_CHANNEL_LEVELS
                    for color in visible
                    for channel in color[:3]
                )
            )

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
        for commander_id, commander in self.ai_manifest[
            "commanders"
        ].items():
            if commander_id == "1":
                continue
            for row in commander["classes"].values():
                if not row["redesigned"]:
                    continue
                with Image.open(
                    AI_ASSET_DIR / row["ai_source_cell_file"]
                ) as source:
                    # High-resolution generated sheets contain many tiny edge
                    # shades. Require roughly one destination-pixel worth of
                    # coverage before treating a hue as a required accent.
                    wanted = accent_hues(
                        source.convert("RGBA"),
                        minimum=max(
                            8,
                            round(source.width * source.height * 0.005),
                        ),
                    )
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

    def test_logical16_outputs_keep_equipment_hues_and_one_silhouette(self):
        levels = set(MEGA_DRIVE_CHANNEL_LEVELS)
        for commander_id in range(2, 11):
            rows = self.ai_manifest["commanders"][str(commander_id)][
                "classes"
            ]
            for class_id_text, row in rows.items():
                if not row["redesigned"]:
                    continue
                image = Image.open(
                    AI_ASSET_DIR
                    / str(commander_id)
                    / f"{int(class_id_text):02X}.png"
                ).convert("RGBA")
                for _, color in image.getcolors(maxcolors=256) or []:
                    if color[3]:
                        self.assertTrue(set(color[:3]).issubset(levels))

                remaining = {
                    (x, y)
                    for y in range(16)
                    for x in range(16)
                    if image.getpixel((x, y))[3]
                }
                component_sizes = []
                while remaining:
                    pending = [remaining.pop()]
                    size = 0
                    while pending:
                        x, y = pending.pop()
                        size += 1
                        for next_y in range(
                            max(0, y - 1),
                            min(16, y + 2),
                        ):
                            for next_x in range(
                                max(0, x - 1),
                                min(16, x + 2),
                            ):
                                point = (next_x, next_y)
                                if point in remaining:
                                    remaining.remove(point)
                                    pending.append(point)
                    component_sizes.append(size)
                substantive_components = sorted(
                    (
                        size
                        for size in component_sizes
                        if size >= 3
                    ),
                    reverse=True,
                )
                # The new shared Sage face mask intentionally owns x=13,
                # y=2..4. In Liana/Lana Priest that transparent original
                # face edge leaves the valid seven-pixel outer staff one
                # logical pixel away from the robe. Preserve the user's
                # face boundary instead of repainting equipment inside it.
                priest_outer_staff = (
                    commander_id in {2, 3}
                    and int(class_id_text) == 0x11
                    and substantive_components == [163, 7]
                )
                self.assertTrue(
                    len(substantive_components) == 1
                    or priest_outer_staff,
                    f"{commander_id}:{class_id_text} has a clipped "
                    "neighbor fragment or detached equipment",
                )

        liana_wizard = Image.open(
            AI_ASSET_DIR / "2/15.png"
        ).convert("RGBA")
        self.assertTrue(
            any(
                red >= blue + 36
                and red >= green
                for _, (red, green, blue, alpha) in (
                    liana_wizard.getcolors(maxcolors=256) or []
                )
                if alpha
            ),
            "Liana Wizard's generated red cape was lost",
        )

    def test_v87_hero_anatomy_and_jessica_fresh_sources_are_validated(self):
        hero_root = (
            ROOT
            / "docs/assets/ai-class-source/latest/elwin-hero-ai-v7-anatomy"
        )
        hero_report = json.loads(
            (hero_root / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(hero_report["accepted"])
        self.assertEqual(hero_report["identity_match"], 73)
        self.assertEqual(hero_report["identity_pixel_count"], 73)
        self.assertEqual(len(hero_report["connected_components"]), 1)
        self.assertFalse(hero_report["empty_rows"])
        self.assertFalse(hero_report["empty_columns"])
        self.assertFalse(hero_report["center_holes"])
        self.assertTrue(all(hero_report["semantic_checks"].values()))
        self.assertEqual(
            list(Image.open(hero_root / "22-hero.png").convert("RGBA").getdata()),
            list(Image.open(AI_ASSET_DIR / "1/22.png").convert("RGBA").getdata()),
        )
        final_hero = Image.open(AI_ASSET_DIR / "1/22.png").convert("RGBA")
        self.assertEqual(final_hero.getpixel((7, 15)), (36, 36, 36, 255))
        self.assertEqual(final_hero.getpixel((8, 15)), (0, 0, 0, 0))
        self.assertEqual(final_hero.getpixel((9, 15)), (36, 36, 36, 255))
        hero_manifest = self.ai_manifest["commanders"]["1"]["classes"][
            str(0x22)
        ]
        self.assertIn("elwin-hero-ai-v7-anatomy", hero_manifest["ai_source_position"])
        self.assertIn("검날→금색 가드→피부색 손→은색 팔", hero_manifest["feature"])
        self.assertIn("견갑→팔→손", hero_manifest["feature"])
        selected_hero = hero_root / "selected-sources/22-hero-ai.png"
        copied_hero = AI_ASSET_DIR / str(hero_manifest["ai_source_original_file"])
        self.assertEqual(
            list(Image.open(selected_hero).convert("RGBA").getdata()),
            list(Image.open(copied_hero).convert("RGBA").getdata()),
        )

        refined_root = (
            ROOT
            / "docs/assets/ai-class-source/latest/"
            "shared-new-classes-v2-refined"
        )
        report = json.loads(
            (refined_root / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(report["all_accepted"])
        self.assertEqual(len(report["classes"]), 33)
        refined_classes = {"15", "16", "18", "28", "25", "26"}
        self.assertEqual(
            sum(row["class_id"] in refined_classes for row in report["classes"]),
            29,
        )
        for row in report["classes"]:
            commander_id = int(row["commander_id"])
            class_id = str(row["class_id"])
            source = Image.open(refined_root / str(row["file"])).convert("RGBA")
            editor = Image.open(
                AI_ASSET_DIR / f"{commander_id}/{class_id}.png"
            ).convert("RGBA")
            if (commander_id, class_id) not in {(10, "26"), (10, "28")}:
                self.assertEqual(list(source.getdata()), list(editor.getdata()))
            if class_id in {"15", "18", "28", "25", "26"}:
                self.assertFalse(row["center_holes"])

        fresh_root = (
            ROOT
            / "docs/assets/ai-class-source/latest/"
            "jessica-zarvera-summoner-ai-v1-fresh"
        )
        fresh_report = json.loads(
            (fresh_root / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(fresh_report["all_accepted"])
        self.assertEqual(len(fresh_report["classes"]), 2)
        self.assertEqual(
            {row["class_id"] for row in fresh_report["classes"]},
            {"26", "28"},
        )
        for row in fresh_report["classes"]:
            class_id = str(row["class_id"])
            self.assertEqual(row["identity_pixel_count"], 73)
            self.assertEqual(row["identity_match"], 73)
            self.assertLessEqual(row["visible_color_count"], 15)
            self.assertEqual(len(row["connected_components"]), 1)
            self.assertFalse(row["empty_rows"])
            self.assertFalse(row["empty_columns"])
            self.assertFalse(row["center_holes"])
            self.assertFalse(row["pure_black"])
            self.assertFalse(row["magenta_contamination"])
            self.assertIn(
                "no earlier AI or shared class template",
                row["input_policy"],
            )

            manifest_row = self.ai_manifest["commanders"]["10"][
                "classes"
            ][str(int(class_id, 16))]
            self.assertIn("OpenAI 신규 제시카", manifest_row["ai_source_kind"])
            self.assertIn(
                "latest/jessica-zarvera-summoner-ai-v1-fresh/",
                manifest_row["ai_source_position"],
            )
            selected = ROOT / str(row["generative_source"])
            copied = (
                AI_ASSET_DIR / str(manifest_row["ai_source_original_file"])
            )
            self.assertEqual(
                list(Image.open(selected).convert("RGBA").getdata()),
                list(Image.open(copied).convert("RGBA").getdata()),
            )

            # The dedicated native source stores the ROM head at x1..11;
            # aggregate composition moves exactly those 73 colors to x2..12.
            original = Image.open(
                ROOT
                / "editor/static/class-sprites/commanders/10/"
                f"{class_id}-p1.png"
            ).convert("RGBA")
            final = Image.open(
                AI_ASSET_DIR / f"10/{class_id}.png"
            ).convert("RGBA")
            translated_identity = {
                tuple(point) for point in manifest_row["identity_lock_points"]
            }
            self.assertEqual(len(translated_identity), 73)
            for x, y in translated_identity:
                self.assertEqual(
                    final.getpixel((x, y)),
                    original.getpixel((x - 1, y)),
                )
            self.assertEqual(final.getpixel((6, 8)), (36, 36, 36, 255))
            self.assertIn(
                "목 경계 투명 1픽셀 폐쇄",
                manifest_row["feature"],
            )

        # Jessica's face is intentionally placed one cell to the right of each
        # dedicated fresh body. Both classes expose that destination mask.
        for class_id in (0x26, 0x28):
            manifest_row = self.ai_manifest["commanders"]["10"]["classes"][
                str(class_id)
            ]
            self.assertEqual(
                min(x for x, _ in manifest_row["identity_lock_points"]),
                2,
            )
            self.assertEqual(
                max(x for x, _ in manifest_row["identity_lock_points"]),
                12,
            )
            self.assertIn("오른쪽 1칸 이동", manifest_row["feature"])

        # The user explicitly kept Healer unchanged.
        for commander_id in (2, 3, 7, 10):
            old = Image.open(
                ROOT
                / "docs/assets/ai-class-source/latest/"
                "shared-new-classes-v1/logical16"
                / f"{commander_id:02d}-08.png"
            ).convert("RGBA")
            new = Image.open(
                refined_root / f"logical16/{commander_id:02d}-08.png"
            ).convert("RGBA")
            self.assertEqual(list(old.getdata()), list(new.getdata()))

    def test_elwin_and_logical16_commanders_change_only_upper_classes(self):
        self.assertEqual(
            self.ai_manifest["asset_version"],
            "elwin-hero-anatomy-v87",
        )
        source_paths = self.ai_manifest["ai_source_images"]
        self.assertEqual(len(source_paths), 148)
        self.assertEqual(
            sum(
                path.startswith(
                    "docs/assets/ai-class-source/elwin-native16-v16/"
                )
                for path in source_paths
            ),
            6,
        )
        self.assertEqual(
            sum(
                path.startswith(
                    "docs/assets/ai-class-source/latest/hein/raw/"
                )
                for path in source_paths
            ),
            10,
        )
        self.assertEqual(
            sum(
                "latest/shared-new-classes-v2-refined/logical16/" in path
                for path in source_paths
            ),
            31,
        )
        self.assertEqual(
            sum(
                "latest/jessica-zarvera-summoner-ai-v1-fresh/" in path
                for path in source_paths
            ),
            4,
        )
        self.assertEqual(
            sum(
                "latest/elwin-hero-ai-v7-anatomy/" in path
                for path in source_paths
            ),
            2,
        )
        self.assertEqual(
            sum(
                "latest/elwin-hero-ai-v6-fresh/" in path
                for path in source_paths
            ),
            0,
        )
        self.assertEqual(
            sum(
                "latest/keith-lester-tier1-mounted-v1/logical16/" in path
                for path in source_paths
            ),
            4,
        )
        self.assertEqual(
            sum("latest/hein-sorcerer-v2/" in path for path in source_paths),
            0,
        )
        self.assertEqual(
            sum(
                "latest/shared-hein-classes-v1/master/" in path
                for path in source_paths
            ),
            2,
        )
        self.assertEqual(
            sum(
                path.startswith(
                    "docs/assets/ai-class-source/latest/"
                    "liana-lana-strict16-v1/native16-"
                )
                for path in source_paths
            ),
            22,
        )
        self.assertEqual(
            sum(
                path.startswith(
                    "docs/assets/ai-class-source/latest/sherry-v2/"
                )
                for path in source_paths
            ),
            11,
        )
        self.assertEqual(
            sum(
                path.startswith(
                    "docs/assets/ai-class-source/latest/"
                    "shared-archmage-lester-v1/logical16/"
                )
                for path in source_paths
            ),
            0,
        )
        self.assertEqual(
            sum(
                path.startswith(
                    "docs/assets/ai-class-source/latest/"
                    "shared-hein-classes-v1/logical16/"
                )
                for path in source_paths
            ),
            5,
        )
        self.assertEqual(
            sum(
                path.startswith(
                    "docs/assets/ai-class-source/latest/"
                    "shared-high-lord-hein-v1/logical16/"
                )
                for path in source_paths
            ),
            9,
        )
        self.assertEqual(
            sum(
                path.startswith(
                    "docs/assets/ai-class-source/latest/"
                    "shared-swordmaster-hein-v1/logical16/"
                )
                for path in source_paths
            ),
            4,
        )
        self.assertEqual(
            sum(
                path.startswith(
                    "docs/assets/ai-class-source/latest/"
                    "shared-lord-elwin-high-lord-v1/logical16/"
                )
                for path in source_paths
            ),
            5,
        )
        for source_path in source_paths:
            with Image.open(ROOT / source_path) as source:
                if source.size == (16, 16):
                    self.assertEqual(source.size, (16, 16))
                else:
                    self.assertGreaterEqual(source.width, 1000)
                    self.assertGreaterEqual(source.height, 1000)

        elwin_direct_stages = {}
        elwin_character_ai = set()
        for commander_id, expected_class_count in (
            ("1", 18),
            ("4", 19),
            ("5", 18),
        ):
            rows = self.ai_manifest["commanders"][commander_id]["classes"]
            self.assertEqual(len(rows), expected_class_count)
            for class_id_text, row in rows.items():
                class_id = int(class_id_text)
                direct_stage = (
                    elwin_direct_stages.get(class_id)
                    if commander_id == "1"
                    else None
                )
                original = render_sprite(
                    self.rom,
                    row["face_source_sprite_id"],
                    1,
                )
                actual = Image.open(
                    AI_ASSET_DIR
                    / commander_id
                    / f"{class_id:02X}.png"
                ).convert("RGBA")
                should_redesign = (
                    row["group_rank"] > 0
                    or (
                        commander_id == "5"
                        and class_id == 0x11
                    )
                    or "원작 ROM 16×16" in row["ai_source_kind"]
                    or "공통 16×16 클래스 템플릿"
                    in row["ai_source_kind"]
                    or row.get("supplemental_hidden_baseline", False)
                )
                self.assertEqual(row["redesigned"], should_redesign)
                self.assertFalse(row["pending_redesign"])
                if not should_redesign:
                    self.assertEqual(
                        actual.tobytes(),
                        original.tobytes(),
                    )
                    self.assertIsNone(row["ai_source_cell_file"])
                    self.assertIsNone(row["identity_lock_box"])
                    self.assertEqual(row["changed_pixel_count"], 0)
                    continue
                if direct_stage is not None:
                    self.assertIn(
                        "direct_16x16",
                        row["ai_source_kind"],
                    )
                    self.assertIn(
                        f"{direct_stage}단계",
                        row["ai_source_position"],
                    )
                    self.assertIn(
                        "실루엣 유지",
                        row["feature"],
                    )
                elif (
                    commander_id == "1"
                    and class_id in elwin_character_ai
                ):
                    self.assertIn(
                        "character-ai-v3",
                        row["ai_source_kind"],
                    )
                else:
                    if row.get("supplemental_hidden_baseline"):
                        expected_source = (
                            "원작 ROM 16×16"
                            if row["changed_pixel_count"]
                            else "히든 클래스"
                        )
                    elif "공통 16×16 클래스 템플릿" in row[
                        "ai_source_kind"
                    ]:
                        expected_source = "공통 16×16 클래스 템플릿"
                    elif "원작 ROM 16×16" in row["ai_source_kind"]:
                        expected_source = "원작 ROM 16×16"
                    elif "네이티브 16×16" in row["ai_source_kind"]:
                        expected_source = "네이티브 16×16"
                    elif (
                        commander_id == "1"
                        and class_id in {0x04, 0x0C, 0x1D, 0x22}
                    ):
                        expected_source = "OpenAI 신규 엘윈"
                    elif commander_id == "1":
                        expected_source = "메가드라이브 16×16"
                    elif commander_id == "4":
                        expected_source = "신규 쉐리"
                    elif (
                        commander_id == "5"
                        and class_id == 0x09
                    ):
                        expected_source = "신규 헤인 소서러"
                    elif commander_id == "5":
                        expected_source = "신규 전폭 논리16"
                    else:
                        expected_source = "logical16-v3"
                    self.assertIn(expected_source, row["ai_source_kind"])
                self.assertIsNotNone(row["ai_source_cell_file"])
                if row.get("supplemental_hidden_baseline"):
                    if row["changed_pixel_count"]:
                        self.assertIn(
                            "원작 ROM 16×16",
                            row["ai_source_kind"],
                        )
                    else:
                        self.assertIn(
                            "히든 클래스",
                            row["ai_source_kind"],
                        )
                else:
                    self.assertGreaterEqual(
                        row["changed_pixel_count"],
                        20,
                    )
                self.assertEqual(
                    sum(
                        actual.getpixel((x, y))
                        != original.getpixel((x, y))
                        for y in range(16)
                        for x in range(16)
                    ),
                    row["changed_pixel_count"],
                )
                if not row.get("identity_mask_pending_rebuild"):
                    for point in row["identity_lock_points"]:
                        point = tuple(point)
                        if (
                            row["identity_lock_transparency_mode"]
                            == "equipment_priority"
                            and not original.getpixel(point)[3]
                        ):
                            continue
                        self.assertEqual(
                            actual.getpixel(point),
                            original.getpixel(point),
                        )

    def test_elwin_v16_ai_sources_fill_the_native_sprite_area(self):
        filenames = {
            0x04: "04-lord.png",
            0x0B: "0B-high-lord.png",
            0x0C: "0C-highlander.png",
            0x12: "12-bishop.png",
            0x13: "13-mage.png",
            0x14: "14-archmage.png",
            0x1A: "1A-swordmaster.png",
            0x1B: "1B-knight-master.png",
            0x1D: "1D-silver-knight.png",
            0x22: "22-hero.png",
        }
        source_dir = (
            ROOT / "docs/assets/ai-class-source/elwin-native16-v16"
        )
        for class_id, filename in filenames.items():
            with Image.open(
                source_dir / "logical16" / filename
            ) as logical_source:
                self.assertEqual(logical_source.size, (16, 16))
            source = remove_magenta_background(
                Image.open(source_dir / filename).convert("RGBA")
            )
            bbox = source.getchannel("A").getbbox()
            self.assertIsNotNone(bbox)
            left, top, right, bottom = bbox
            self.assertGreaterEqual(
                (right - left) / source.width,
                0.60,
                f"Elwin class {class_id:02X} design is too narrow",
            )
            self.assertGreaterEqual(
                (bottom - top) / source.height,
                0.80,
                f"Elwin class {class_id:02X} design is too short",
            )

    def test_sherry_v2_sources_keep_native_scale_and_short_bob_mask(self):
        filenames = {
            0x04: "04-lord.png",
            0x0B: "0B-high-lord.png",
            0x13: "13-mage.png",
            0x14: "14-archmage.png",
            0x15: "15-wizard.png",
            0x17: "17-saint.png",
            0x19: "19-paladin.png",
            0x1D: "1D-silver-knight.png",
            0x1E: "1E-dragon-lord.png",
            0x21: "21-ranger.png",
            0x23: "23-high-master.png",
        }
        source_dir = (
            ROOT / "docs/assets/ai-class-source/latest/sherry-v2"
        )
        report = json.loads(
            (source_dir / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(report["all_accepted"])
        for row in report["classes"]:
            self.assertGreaterEqual(
                row["prelock_identity_ratio"],
                1.0,
            )
            self.assertEqual(row["foreground_width"], 16)
            self.assertEqual(row["foreground_height"], 16)
        for class_id, filename in filenames.items():
            with Image.open(
                source_dir / "logical16" / filename
            ) as logical_source:
                self.assertEqual(logical_source.size, (16, 16))
            source = remove_magenta_background(
                Image.open(source_dir / filename).convert("RGBA")
            )
            bbox = source.getchannel("A").getbbox()
            self.assertIsNotNone(bbox)
            left, top, right, bottom = bbox
            self.assertGreaterEqual(
                right - left,
                12 if class_id in {0x1D, 0x1E} else 7,
            )
            self.assertGreaterEqual(bottom - top, 14)
            final = Image.open(
                AI_ASSET_DIR / "4" / f"{class_id:02X}.png"
            ).convert("RGBA")
            identity_points = {
                tuple(point)
                for point in self.ai_manifest["commanders"]["4"][
                    "classes"
                ][str(class_id)]["identity_lock_points"]
            }
            self.assertFalse(
                any(
                    final.getpixel((x, y)) == (0, 0, 0, 255)
                    for y in range(16)
                    for x in range(16)
                    if (x, y) not in identity_points
                ),
                f"Sherry class {class_id:02X} retained generated black",
            )
            self.assertTrue(
                all(
                    any(
                        final.getpixel((x, y))[3]
                        for x in range(16)
                    )
                    for y in range(16)
                )
            )
            self.assertTrue(
                all(
                    any(
                        final.getpixel((x, y))[3]
                        for y in range(16)
                    )
                    for x in range(16)
                )
            )

    def test_hein_v2_reconstructs_existing_ai_with_current_masks(self):
        filenames = {
            0x09: "09-sorcerer.png",
            0x0A: "0A-shaman.png",
            0x0B: "0B-high-lord.png",
            0x13: "13-mage.png",
            0x14: "14-archmage.png",
            0x15: "15-wizard.png",
            0x16: "16-high-priest.png",
            0x18: "18-sage.png",
            0x19: "19-paladin.png",
            0x1A: "1A-swordmaster.png",
            0x28: "28-summoner.png",
        }
        source_dir = (
            ROOT
            / "docs/assets/ai-class-source/archive/hein/hein-native16-v2"
        )
        report = json.loads(
            (source_dir / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(report["all_accepted"])
        self.assertIn("reconstruct", report["mode"])
        for class_id, filename in filenames.items():
            with Image.open(
                source_dir / "logical16" / filename
            ) as logical_source:
                self.assertEqual(logical_source.size, (16, 16))
            source = remove_magenta_background(
                Image.open(source_dir / filename).convert("RGBA")
            )
            bbox = source.getchannel("A").getbbox()
            self.assertIsNotNone(bbox)
            left, top, right, bottom = bbox
            self.assertGreaterEqual(right - left, 7)
            self.assertGreaterEqual(bottom - top, 14)

    def test_latest_hein_uses_every_row_and_column_without_ai_fringe(self):
        source_dir = ROOT / "docs/assets/ai-class-source/latest/hein"
        filenames = {
            0x09: "09-sorcerer",
            0x0A: "0A-shaman",
            0x0B: "0B-high-lord",
            0x11: "11-priest",
            0x13: "13-mage",
            0x14: "14-archmage",
            0x15: "15-wizard",
            0x16: "16-high-priest",
            0x18: "18-sage",
            0x19: "19-paladin",
            0x1A: "1A-swordmaster",
            0x28: "28-summoner",
        }
        for class_id, stem in filenames.items():
            raw_path = source_dir / "raw" / f"{stem}.png"
            logical_path = source_dir / "logical16" / f"{stem}.png"
            if class_id == 0x09:
                raw_path = (
                    ROOT
                    / "docs/assets/ai-class-source/latest/"
                    "hein-sorcerer-v2/clean/"
                    "hein-09-sorcerer-ai.png"
                )
                logical_path = (
                    ROOT
                    / "docs/assets/ai-class-source/latest/"
                    "hein-sorcerer-v2/logical16/"
                    "hein-09-sorcerer-ai.png"
                )
            with Image.open(raw_path) as raw:
                self.assertEqual(raw.size, (1254, 1254))
            with Image.open(logical_path) as logical:
                self.assertEqual(logical.size, (16, 16))
            row = self.ai_manifest["commanders"]["5"]["classes"][
                str(class_id)
            ]
            if class_id == 0x09:
                self.assertIn(
                    "비-AI 워록 원본 기반 소서러",
                    row["ai_source_kind"],
                )
                self.assertEqual(
                    row["identity_lock_mode"],
                    "custom",
                )
                self.assertGreater(
                    row["identity_lock_pixel_count"],
                    0,
                )
                self.assertFalse(row["identity_mask_superseded"])
                self.assertIn(
                    "현재 원작 머리·얼굴·눈",
                    row["feature"],
                )
            elif class_id in {
                0x0B,
                0x11,
                0x13,
                0x14,
                0x15,
                0x16,
                0x18,
                0x1A,
                0x26,
                0x28,
            }:
                self.assertIn(
                    "공통 16×16 클래스 템플릿",
                    row["ai_source_kind"],
                )
            else:
                self.assertTrue(
                    "신규 전폭 논리16" in row["ai_source_kind"]
                    or "원작 ROM 16×16" in row["ai_source_kind"]
                )
            image = Image.open(
                AI_ASSET_DIR / "5" / f"{class_id:02X}.png"
            ).convert("RGBA")
            self.assertEqual(
                image.getchannel("A").getbbox(),
                (0, 0, 16, 16)
                if class_id == 0x09
                else (0, 0, 16, 16),
            )
            for y in range(16):
                self.assertTrue(
                    any(image.getpixel((x, y))[3] for x in range(16)),
                    f"class {class_id:02X} leaves row {y} empty",
                )
            if class_id != 0x09:
                for x in range(16):
                    self.assertTrue(
                        any(
                            image.getpixel((x, y))[3]
                            for y in range(16)
                        ),
                        f"class {class_id:02X} leaves column {x} empty",
                    )
            colors = {
                color
                for _, color in (image.getcolors(maxcolors=256) or [])
                if color[3]
            }
            self.assertLessEqual(len(colors), 15)
            self.assertNotIn((0, 0, 0, 255), colors)
            locked = {
                tuple(point)
                for point in row["identity_lock_points"]
            }
            ai_pixels = (
                image.getpixel((x, y))
                for y in range(16)
                for x in range(16)
                if (x, y) not in locked
            )
            if class_id != 0x14:
                self.assertFalse(
                    any(
                        red >= 36
                        and blue >= 36
                        and green * 2 < min(red, blue)
                        for red, green, blue, alpha in ai_pixels
                        if alpha
                    ),
                    f"class {class_id:02X} retains a purple AI fringe",
                )

    def test_pixellab_lord_trial_is_native_16_and_locks_head_pixels(self):
        trial_dir = (
            ROOT / "docs/assets/ai-class-source/pixellab-elwin-trial"
        )
        source = Image.open(trial_dir / "04-source-16.png").convert("RGBA")
        mask = Image.open(trial_dir / "04-mask-16.png").convert("L")
        generated_mask, box = pixellab_inpaint_mask(source)
        self.assertEqual(source.size, (16, 16))
        self.assertEqual(mask.size, (16, 16))
        self.assertEqual(mask.tobytes(), generated_mask.tobytes())
        self.assertEqual(box, (4, 0, 14, 5))
        values = {color for _, color in mask.getcolors(maxcolors=256)}
        self.assertEqual(values, {0, 255})
        self.assertGreater(sum(value == 0 for value in mask.getdata()), 0)
        self.assertGreater(sum(value == 255 for value in mask.getdata()), 0)

    def test_preview_generators_are_not_imported_by_rom_builder(self):
        production_sources = (
            ROOT / "scripts/build_korean_jp_probe.py",
        )
        for path in production_sources:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("build_test_class_sprite_assets", source)
            self.assertNotIn("build_ai_class_sprite_assets", source)

    def test_each_commander_has_ai_and_16x16_comparison_png(self):
        paths = self.ai_manifest["character_comparison_images"]
        self.assertEqual(len(paths), 10)
        for path_text in paths:
            path = ROOT / path_text
            self.assertTrue(path.is_file(), path)
            self.assertIn(
                "docs/assets/ai-class-source/character-ai-v3/",
                path_text,
            )
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 1000)
                self.assertGreaterEqual(image.height, 900)

    def test_saved_identity_mask_document_is_well_formed(self):
        document = json.loads(
            (ROOT / "editor/ai_identity_masks.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(document["version"], 1)
        for key, points in document["masks"].items():
            commander_id, class_id = key.split(":", 1)
            self.assertIn(int(commander_id), range(1, 11))
            self.assertIn(int(class_id, 16), range(0x100))
            normalized = {tuple(point) for point in points}
            self.assertEqual(len(normalized), len(points))
            self.assertTrue(
                all(
                    0 <= x < 16 and 0 <= y < 16
                    for x, y in normalized
                )
            )

    def test_ai_design_editor_document_and_palette_normalizer(self):
        document = json.loads(
            (ROOT / "editor/ai_class_design_overrides.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(document["version"], 1)
        self.assertIsInstance(document["designs"], dict)
        levels = set(MEGA_DRIVE_CHANNEL_LEVELS)
        for key, entry in document["designs"].items():
            commander_id, class_id = key.split(":", 1)
            self.assertIn(int(commander_id), range(1, 11))
            self.assertIn(int(class_id, 16), range(0x100))
            self.assertEqual(len(entry["pixels"]), 256)
            visible = {
                tuple(pixel)
                for pixel in entry["pixels"]
                if pixel[3]
            }
            self.assertLessEqual(len(visible), 15)
            self.assertTrue(
                all(
                    set(pixel[:3]).issubset(levels)
                    and pixel[3] in {0, 255}
                    for pixel in entry["pixels"]
                )
            )

        normalized = normalize_ai_design_pixels(
            [[80, 30, 120, 255], [9, 9, 9, 0]]
            + [[0, 0, 0, 0]] * 254
        )
        self.assertEqual(normalized[0], [73, 36, 109, 255])
        self.assertEqual(normalized[1], [0, 0, 0, 0])

        current = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        current.putpixel((7, 6), (219, 182, 109, 255))
        requested = [[0, 0, 0, 0] for _ in range(256)]
        requested[6 * 16 + 7] = [73, 109, 255, 255]
        preserve_locked_ai_design_pixels(
            requested,
            current,
            [[7, 6]],
        )
        self.assertEqual(
            requested[6 * 16 + 7],
            [219, 182, 109, 255],
        )
        for commander in self.ai_manifest["commanders"].values():
            for row in commander["classes"].values():
                self.assertIsInstance(row["design_override"], bool)
                self.assertIsInstance(row["design_revision"], int)

    def test_liana_high_lord_keeps_identity_and_uses_red_cape(self):
        row = self.ai_manifest["commanders"]["2"]["classes"]["11"]
        self.assertTrue(row["design_override"])
        with Image.open(AI_ASSET_DIR / row["file"]) as image:
            pixels = list(image.getdata())
            self.assertEqual(
                pixels.count((219, 0, 0, 255)),
                45,
            )
            self.assertEqual(
                pixels.count((109, 0, 0, 255)),
                5,
            )
            self.assertEqual(
                image.getpixel((7, 0)),
                (146, 73, 36, 255),
            )
            self.assertEqual(
                image.getpixel((12, 10)),
                (109, 0, 0, 255),
            )

    def test_shared_identity_masks_and_elwin_swordmaster_mask_are_saved(self):
        document = json.loads(
            (ROOT / "editor/ai_identity_masks.json").read_text(
                encoding="utf-8"
            )
        )
        masks = document["masks"]
        shared_liana_classes = (
            0x08,
            0x0B,
            0x11,
            0x13,
            0x14,
            0x15,
            0x16,
            0x18,
            0x19,
            0x1D,
            0x28,
        )
        sage_reference = masks["2:18"]
        self.assertEqual(len(sage_reference), 91)
        for class_id in shared_liana_classes:
            if class_id == 0x18:
                self.assertEqual(masks["3:18"], sage_reference)
            elif class_id == 0x0B:
                self.assertEqual(len(masks["3:0B"]), 75)
                self.assertNotEqual(masks["3:0B"], sage_reference)
            else:
                self.assertEqual(len(masks[f"3:{class_id:02X}"]), 82)
                self.assertEqual(len(masks[f"2:{class_id:02X}"]), 82)
        self.assertEqual(len(masks["2:0B"]), 72)
        self.assertNotEqual(masks["2:0B"], sage_reference)

        jessica_sorcerer = masks["10:09"]
        for class_id in (
            0x11,
            0x15,
            0x16,
            0x18,
            0x26,
        ):
            self.assertEqual(
                masks[f"10:{class_id:02X}"],
                jessica_sorcerer,
            )
        for class_id, expected_count in (
            (0x13, 69),
            (0x14, 69),
            (0x19, 76),
        ):
            self.assertEqual(
                len(masks[f"10:{class_id:02X}"]),
                expected_count,
            )
            self.assertNotEqual(
                masks[f"10:{class_id:02X}"],
                jessica_sorcerer,
            )
        # High Lord now has an explicit shifted mask. Swordmaster keeps its
        # finalized face directly in the saved override.
        self.assertEqual(len(masks["10:0B"]), 69)
        self.assertEqual(masks["10:1A"], [])
        self.assertTrue(
            all(
                0 <= x < 16 and 0 <= y < 16
                for x, y in masks["10:0B"]
            )
        )
        self.assertEqual(
            self.ai_manifest["commanders"]["10"]["classes"]["11"][
                "identity_translation"
            ],
            [1, 0],
        )
        self.assertTrue(
            self.ai_manifest["commanders"]["10"]["classes"]["11"][
                "identity_translation_applied_in_override"
            ]
        )
        self.assertEqual(
            self.ai_manifest["commanders"]["10"]["classes"]["26"][
                "identity_translation"
            ],
            [1, 0],
        )

        elwin_swordmaster = {
            tuple(point) for point in masks["1:1A"]
        }
        # This is a user-edited mask, so its exact pixel count may change
        # whenever the editor is used. Keep only the broad silhouette guard.
        self.assertGreaterEqual(len(elwin_swordmaster), 70)
        self.assertTrue(
            {(0, 10), (0, 11)}.issubset(elwin_swordmaster)
        )

    def test_elwin_red_capes_and_shared_hein_mage_layout_are_saved(self):
        swordmaster = Image.open(
            AI_ASSET_DIR / "1/1A.png"
        ).convert("RGBA")
        for point in ELWIN_SWORDMASTER_CAPE_POINTS:
            self.assertEqual(
                swordmaster.getpixel(point),
                (219, 0, 0, 255),
            )

        mage_path = AI_ASSET_DIR / "1/13.png"
        row = self.ai_manifest["commanders"]["1"]["classes"]["19"]
        self.assertIn("공통 16×16 클래스 템플릿", row["ai_source_kind"])
        self.assertTrue(row["design_override"])
        self.assertFalse(row["design_override_superseded"])
        self.assertEqual(row["superseded_design_revision"], 0)
        with Image.open(mage_path) as mage:
            colors = Counter(mage.getdata())
            self.assertGreaterEqual(colors[(109, 0, 0, 255)], 10)
            self.assertGreaterEqual(colors[(146, 0, 0, 255)], 10)
            self.assertGreaterEqual(colors[(0, 73, 219, 255)], 10)
            self.assertTrue(
                all(
                    mage.getpixel(point)[3]
                    for point in (
                        SHARED_DARK_BOUNDARY_REFERENCE_POINTS[0x13]
                    )
                )
            )

    def test_all_stock_multi_hidden_classes_are_editable_in_ai_manifest(self):
        expected = {
            1: {0x22, 0x29},
            2: {0x25, 0x26, 0x28},
            3: {0x25, 0x26, 0x28},
            4: {0x23, 0x24, 0x27},
            5: {0x26, 0x28},
            6: {0x29},
            7: {0x24},
            8: {0x23},
            9: {0x26, 0x2A},
            10: {0x26, 0x28},
        }
        supplemental_count = 0
        for commander_id, class_ids in expected.items():
            rows = self.ai_manifest["commanders"][
                str(commander_id)
            ]["classes"]
            actual = {
                int(class_id)
                for class_id, row in rows.items()
                if row.get("hidden_class")
            }
            self.assertEqual(actual, class_ids)
            for class_id in class_ids:
                row = rows[str(class_id)]
                self.assertEqual(row["tier"], 5)
                self.assertTrue(row["redesigned"])
                self.assertTrue(
                    (AI_ASSET_DIR / row["file"]).is_file()
                )
                if row.get("supplemental_hidden_baseline"):
                    supplemental_count += 1
                    if row["changed_pixel_count"]:
                        self.assertIn("원작 ROM 16×16", row["ai_source_kind"])
                    else:
                        self.assertIn("히든 클래스", row["ai_source_kind"])
        self.assertEqual(supplemental_count, 3)

    def test_liana_lana_share_one_full_canvas_design_with_blue_red_contrast(
        self,
    ):
        source_dir = (
            ROOT
            / "docs/assets/ai-class-source/latest/liana-lana-strict16-v1"
        )
        class_ids = (
            0x08,
            0x0B,
            0x11,
            0x13,
            0x14,
            0x15,
            0x16,
            0x18,
            0x19,
            0x1D,
            0x28,
        )
        validation = json.loads(
            (source_dir / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        face_refresh = json.loads(
            (source_dir / "sage-face-refresh-report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(face_refresh["identity_pixel_count"], 82)
        self.assertTrue(face_refresh["all_face_exact"])
        self.assertTrue(face_refresh["all_equipment_unchanged"])
        self.assertTrue(face_refresh["all_4bpp"])
        self.assertTrue(face_refresh["all_pair_alpha_equal"])
        self.assertTrue(validation["all_head_exact"])
        self.assertTrue(validation["all_pair_alpha_equal"])
        self.assertTrue(validation["all_4bpp"])
        self.assertTrue(validation["all_full_canvas"])
        self.assertTrue(
            all(
                row["selected_source_identity_exact_pixels"] == 82
                for row in validation["classes"]
            )
        )
        liana_high_lord = Image.open(
            AI_ASSET_DIR / "2/0B.png"
        ).convert("RGBA")
        lana_high_lord = Image.open(
            AI_ASSET_DIR / "3/0B.png"
        ).convert("RGBA")
        liana_colors = {
            color for color in liana_high_lord.getdata() if color[3]
        }
        lana_colors = {
            color for color in lana_high_lord.getdata() if color[3]
        }
        self.assertIn((219, 0, 0, 255), liana_colors)
        self.assertIn((109, 0, 0, 255), liana_colors)
        self.assertNotIn((0, 73, 219, 255), liana_colors)
        self.assertIn((0, 0, 219, 255), lana_colors)
        self.assertNotIn((219, 0, 0, 255), lana_colors)
        self.assertTrue(
            self.ai_manifest["commanders"]["2"]["classes"][
                str(0x0B)
            ]["design_override"]
        )
        self.assertTrue(
            (
                ROOT
                / "docs/assets/ai-class-source/archive/"
                "liana-high-lord-before-red-cape-v1/"
                "02-0B-blue-v1.png"
            ).is_file()
        )
        for class_id in class_ids:
            with Image.open(
                source_dir / "selected-sources" / f"{class_id:02X}.png"
            ) as evidence:
                self.assertEqual(evidence.size, (1254, 1254))
            native_filename = f"{class_id:02X}.png"
            with Image.open(
                source_dir / "native16-blue" / native_filename
            ) as native_source:
                blue_native = native_source.convert("RGBA")
            with Image.open(
                source_dir / "native16-red" / native_filename
            ) as native_source:
                red_native = native_source.convert("RGBA")
            self.assertEqual(blue_native.size, (16, 16))
            self.assertEqual(red_native.size, (16, 16))

            liana_red = Image.open(
                AI_ASSET_DIR / "2" / f"{class_id:02X}.png"
            ).convert("RGBA")
            lana_blue = Image.open(
                AI_ASSET_DIR / "3" / f"{class_id:02X}.png"
            ).convert("RGBA")
            liana_row = self.ai_manifest["commanders"]["2"][
                "classes"
            ][str(class_id)]
            if "공통 16×16 클래스 템플릿" in liana_row[
                "ai_source_kind"
            ]:
                for commander_id, image in (
                    (2, liana_red),
                    (3, lana_blue),
                ):
                    row = self.ai_manifest["commanders"][
                        str(commander_id)
                    ]["classes"][str(class_id)]
                    self.assertIn(
                        "공통 16×16 클래스 템플릿",
                        row["ai_source_kind"],
                    )
                    self.assertEqual(
                        image.getchannel("A").getbbox(),
                        (0, 0, 16, 16),
                    )
                continue
            if "원작 ROM 16×16" in liana_row["ai_source_kind"]:
                for image in (liana_red, lana_blue):
                    self.assertEqual(
                        image.getchannel("A").getbbox(),
                        (0, 0, 16, 16),
                    )
                    self.assertLessEqual(
                        len(image.getcolors(maxcolors=256) or []),
                        16,
                    )
                continue
            self.assertEqual(
                liana_red.tobytes(),
                red_native.tobytes(),
            )
            self.assertEqual(
                lana_blue.tobytes(),
                blue_native.tobytes(),
            )
            self.assertEqual(
                liana_red.getchannel("A").tobytes(),
                lana_blue.getchannel("A").tobytes(),
                f"class {class_id:02X} blue/red silhouettes differ",
            )
            self.assertEqual(
                liana_red.getchannel("A").getbbox(),
                (0, 0, 16, 16),
            )
            for logical_index in range(16):
                self.assertTrue(
                    any(
                        liana_red.getpixel((x, logical_index))[3]
                        for x in range(16)
                    ),
                    f"class {class_id:02X} leaves a row empty",
                )
                self.assertTrue(
                    any(
                        liana_red.getpixel((logical_index, y))[3]
                        for y in range(16)
                    ),
                    f"class {class_id:02X} leaves a column empty",
                )
            self.assertGreaterEqual(
                sum(
                    bool(liana_red.getpixel((x, y))[3])
                    for x in range(13, 16)
                    for y in range(16)
                ),
                10,
                f"class {class_id:02X} does not use the viewer-right "
                "weapon space",
            )

            blue_colors = lana_blue.getcolors(maxcolors=256) or []
            red_colors = liana_red.getcolors(maxcolors=256) or []
            self.assertGreaterEqual(
                sum(
                    count
                    for count, (red_value, green, blue_value, alpha)
                    in blue_colors
                    if (
                        alpha
                        and blue_value >= red_value + 36
                        and blue_value >= green
                    )
                ),
                20,
            )
            self.assertGreaterEqual(
                sum(
                    count
                    for count, (red_value, green, blue_value, alpha)
                    in red_colors
                    if (
                        alpha
                        and red_value >= blue_value + 36
                        and red_value >= green
                    )
                ),
                20,
            )

            for commander_id, image in (
                (2, liana_red),
                (3, lana_blue),
            ):
                row = self.ai_manifest["commanders"][
                    str(commander_id)
                ]["classes"][str(class_id)]
                self.assertIn(
                    "네이티브 16×16",
                    row["ai_source_kind"],
                )
                self.assertIn(
                    "오른쪽 끝",
                    row["feature"],
                )
                self.assertIn(
                    "강제 확대 없이",
                    row["feature"],
                )
                source_cell = Image.open(
                    AI_ASSET_DIR / row["ai_source_cell_file"]
                ).convert("RGBA")
                self.assertEqual(source_cell.size, (16, 16))
                locked = {
                    tuple(point)
                    for point in row["identity_lock_points"]
                }
                for y in range(16):
                    for x in range(16):
                        if (x, y) in locked:
                            continue
                        red_value, green, blue_value, alpha = (
                            image.getpixel((x, y))
                        )
                        if not alpha:
                            continue
                        self.assertNotEqual(
                            (red_value, green, blue_value),
                            (0, 0, 0),
                        )
                        self.assertFalse(
                            red_value >= 36
                            and blue_value >= 36
                            and green * 2
                            < min(red_value, blue_value)
                            and abs(red_value - blue_value) <= 73
                        )

    def test_direct_five_stage_sources_are_reference_only(self):
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
        for path in direct_sources:
            self.assertNotIn(path.name, manifest_text)


if __name__ == "__main__":
    unittest.main()
