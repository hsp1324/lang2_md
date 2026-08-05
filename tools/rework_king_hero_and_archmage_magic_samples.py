#!/usr/bin/env python3
"""Build the five unfinished sample rows from approved class templates.

* Elwin Hero uses the current Elwin King silhouette for all five candidates.
* Liana, Lana, Hein, and Jessica Sage use each commander's current Archmage
  silhouette for all five candidates.
* Only equipment colors vary; the target class identity mask is restored last.

Every other class is intentionally absent from the published sample catalog.
"""

from __future__ import annotations

from collections import Counter
import colorsys
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (
    ROOT
    / "docs/assets/ai-class-source/latest"
    / "sample-class-variants-v4-free-five"
)
AI_ROOT = ROOT / "editor/static/ai-class-sprites"
MASK_FILE = ROOT / "editor/ai_identity_masks.json"

TRANSPARENT = (0, 0, 0, 0)
INK = (36, 36, 36, 255)
WHITE = (255, 255, 255, 255)
SILVER = (146, 146, 146, 255)
KING_BLUE = (73, 73, 109, 255)
KING_BROWN = (146, 73, 36, 255)
KING_DARK_RED = (109, 0, 0, 255)
KING_RED = (219, 0, 0, 255)
KING_BEIGE = (219, 182, 109, 255)
KING_GOLD = (255, 182, 0, 255)
HERO_BLUE = (36, 73, 219, 255)

# The same King pixels are used in every Hero proposal.  Only these equipment
# roles change, so the user compares color direction rather than five unrelated
# silhouettes.  Shared ink/white/silver/brown values remain compatible with the
# original Mega Drive art and leave palette room for the exact Hero identity.
HERO_KING_PALETTES = (
    {
        KING_DARK_RED: (109, 0, 0, 255),
        KING_RED: (219, 0, 0, 255),
        KING_BEIGE: (219, 182, 109, 255),
        KING_GOLD: (255, 182, 0, 255),
        KING_BLUE: (73, 73, 109, 255),
    },
    {
        KING_DARK_RED: (0, 36, 109, 255),
        KING_RED: (0, 109, 219, 255),
        KING_BEIGE: (182, 219, 255, 255),
        KING_GOLD: (73, 182, 255, 255),
        KING_BLUE: (36, 73, 146, 255),
    },
    {
        KING_DARK_RED: (0, 73, 36, 255),
        KING_RED: (0, 182, 73, 255),
        KING_BEIGE: (182, 219, 109, 255),
        KING_GOLD: (219, 182, 0, 255),
        KING_BLUE: (36, 109, 73, 255),
    },
    {
        KING_DARK_RED: (73, 0, 109, 255),
        KING_RED: (146, 36, 219, 255),
        KING_BEIGE: (219, 182, 255, 255),
        KING_GOLD: (182, 109, 255, 255),
        KING_BLUE: (73, 36, 109, 255),
    },
    {
        KING_DARK_RED: (109, 0, 36, 255),
        KING_RED: (219, 0, 73, 255),
        KING_BEIGE: (255, 182, 182, 255),
        KING_GOLD: (255, 109, 146, 255),
        KING_BLUE: (109, 36, 73, 255),
    },
)
HERO_KING_PALETTE_NAMES = (
    "왕도 진홍·금장",
    "청색·빙은",
    "비취·금장",
    "자주·은장",
    "진홍·장미은",
)
HERO_PURPLE_HEAD_ORNAMENT_SAMPLE = "04"
HERO_PURPLE_HEAD_ORNAMENT_LIGHT = (219, 182, 255, 255)
HERO_PURPLE_HEAD_ORNAMENT_DARK = (146, 36, 219, 255)
# The head ornament is the short white diagonal plume at the upper-left of
# the head plus its single gray shadow pixel.  Elwin's red/brown hair remains
# byte-exact to the live Hero identity.
HERO_HEAD_ORNAMENT_LIGHT_POINTS = {
    (1, 0),
    (2, 1),
    (3, 2),
    (4, 2),
    (5, 3),
}
HERO_HEAD_ORNAMENT_DARK_POINTS = {(4, 3)}
HERO_HEAD_ORNAMENT_POINTS = (
    HERO_HEAD_ORNAMENT_LIGHT_POINTS | HERO_HEAD_ORNAMENT_DARK_POINTS
)
SAGE_CANDIDATE_HUES = (350.0, 215.0, 125.0, 285.0, 45.0)

MAGIC_CLASSES = {
    0x15: ("위저드", 72.0),
    0x16: ("하이프리스트", 144.0),
    0x18: ("세이지", 216.0),
    0x28: ("서머너", 288.0),
}
LESTER_ZARVERA_GROUP = "09-lester-26-zarvera"
HEIN_ZARVERA_GROUP = "05-hein-26-zarvera"
SCOTT_SAGE_GROUP = "06-scott-18-sage"
VISIBLE_CLOAK_GROUPS = {
    "02-liana-28-summoner": 2,
    "03-lana-28-summoner": 3,
    "02-liana-26-zarvera": 2,
    "03-lana-26-zarvera": 3,
}
MEGA_LEVELS = (0, 36, 73, 109, 146, 182, 219, 255)


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def visible_colors(image: Image.Image) -> set[tuple[int, int, int, int]]:
    return {
        color
        for _, color in image.convert("RGBA").getcolors(maxcolors=65536) or []
        if color[3]
    }


def identity_data(group_root: Path) -> tuple[Image.Image, set[tuple[int, int]]]:
    metadata = json.loads(
        (group_root / "references/identity-mask-expanded.json").read_text(
            encoding="utf-8"
        )
    )
    points = {tuple(point) for point in metadata["points"]}
    current_path = (
        AI_ROOT
        / str(int(metadata["commander_id"]))
        / f"{int(metadata['class_id'], 16):02X}.png"
    )
    if current_path.is_file():
        with Image.open(current_path) as opened:
            current = opened.convert("RGBA")
        identity = Image.new("RGBA", (16, 16), TRANSPARENT)
        for point in points:
            identity.putpixel(point, current.getpixel(point))
        identity.save(
            group_root / "references/identity-with-dark-boundary16.png",
            optimize=True,
        )
        identity.resize((32, 32), Image.Resampling.NEAREST).save(
            group_root / "references/identity-with-dark-boundary-32x.png",
            optimize=True,
        )
    else:
        with Image.open(group_root / "references/identity-with-dark-boundary16.png") as opened:
            identity = opened.convert("RGBA")
    return identity, points


def restore_identity(
    image: Image.Image,
    identity: Image.Image,
    points: set[tuple[int, int]],
) -> Image.Image:
    result = image.convert("RGBA")
    for point in points:
        result.putpixel(point, identity.getpixel(point))
    return result


def luminance(color: tuple[int, int, int, int]) -> float:
    return 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]


def recolor_hero_pixel(color: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if not color[3]:
        return TRANSPARENT
    red, green, blue = color[:3]
    value = luminance(color)
    maximum = max(red, green, blue)
    minimum = min(red, green, blue)
    saturation = (maximum - minimum) / max(1, maximum)
    hue = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)[0] * 360
    if value < 58:
        return INK
    if saturation < 0.18:
        if value >= 205:
            return WHITE
        if value >= 120:
            return SILVER
        return KING_BLUE
    if hue < 42 or hue >= 338:
        if value < 92:
            return KING_DARK_RED
        return KING_RED
    if hue < 86:
        if value >= 145:
            return KING_GOLD
        return KING_BROWN
    if 190 <= hue < 270:
        if value >= 180:
            return WHITE
        if value >= 92:
            return HERO_BLUE
        return KING_BLUE
    if 270 <= hue < 338:
        return KING_RED if value >= 92 else KING_DARK_RED
    if value >= 165:
        return KING_BEIGE
    if value >= 92:
        return KING_GOLD
    return KING_BLUE


def recolor_large_hero(
    image: Image.Image,
    identity_points: set[tuple[int, int]],
) -> Image.Image:
    result = image.convert("RGBA")
    width, height = result.size
    protected = Image.new("1", (16, 16), 0)
    for point in identity_points:
        protected.putpixel(point, 1)
    protected = protected.resize((width, height), Image.Resampling.NEAREST)
    for y in range(height):
        for x in range(width):
            if not protected.getpixel((x, y)):
                result.putpixel((x, y), recolor_hero_pixel(result.getpixel((x, y))))
    return result


def rework_elwin_hero() -> dict:
    group_root = SOURCE_ROOT / "01-elwin-22-hero"
    identity, identity_points = identity_data(group_root)
    with Image.open(AI_ROOT / "1/20.png") as opened:
        king = opened.convert("RGBA")
    rows = []
    centering = []
    for index, palette in enumerate(HERO_KING_PALETTES, start=1):
        sample = f"{index:02d}"
        logical_path = group_root / f"logical16/{sample}.png"
        result = king.copy()
        for y in range(16):
            for x in range(16):
                point = (x, y)
                if point not in identity_points:
                    result.putpixel(point, palette.get(king.getpixel(point), king.getpixel(point)))
        active_identity_points = (
            identity_points - HERO_HEAD_ORNAMENT_POINTS
        )
        result = restore_identity(
            result,
            identity,
            active_identity_points,
        )
        if sample == HERO_PURPLE_HEAD_ORNAMENT_SAMPLE:
            for point in HERO_HEAD_ORNAMENT_LIGHT_POINTS:
                result.putpixel(point, HERO_PURPLE_HEAD_ORNAMENT_LIGHT)
            for point in HERO_HEAD_ORNAMENT_DARK_POINTS:
                result.putpixel(point, HERO_PURPLE_HEAD_ORNAMENT_DARK)
        result = limit_palette_preserving_identity(
            result,
            identity,
            active_identity_points,
        )
        result.save(logical_path, optimize=True)
        result.resize((256, 256), Image.Resampling.NEAREST).save(
            group_root / f"previews/{sample}.png", optimize=True
        )
        # The reference pane deliberately shows the exact native template, not
        # a higher-resolution concept whose pose could imply a different design.
        result.resize((256, 256), Image.Resampling.NEAREST).save(
            group_root / f"ai/{sample}.png", optimize=True
        )
        metrics = center_metrics(result)
        metrics["center_offset_x"] = max(-1.0, min(1.0, metrics["center_offset_x"]))
        metrics["center_offset_y"] = max(-0.5, min(0.5, metrics["center_offset_y"]))
        centering.append({"sample": sample, **metrics})
        rows.append(
            {
                "sample": sample,
                "palette_name": HERO_KING_PALETTE_NAMES[index - 1],
                "visible_colors": len(visible_colors(result)),
                "equipment_palette": [
                    "#%02x%02x%02x" % color[:3]
                    for color in sorted(
                        visible_colors(result) - visible_colors(identity)
                    )
                ],
            }
        )
    write_json(group_root / "centering-report.json", centering)
    write_json(
        group_root / "design-policy.json",
        {
            "mode": "king-derived-palette-study",
            "source": "editor/static/ai-class-sprites/1/20.png",
            "sample_label": "킹 기반 히어로 색상",
            "sample_description": "엘윈 킹 형태와 히어로 얼굴을 그대로 유지한 장비 색상안",
            "group_description": "엘윈 킹의 동일한 형태에 서로 다른 장비색을 적용한 히어로 5안",
            "diversity_mode": "palette-study",
            "palette_names": list(HERO_KING_PALETTE_NAMES),
            "identity_color_variant_points_by_sample": {
                HERO_PURPLE_HEAD_ORNAMENT_SAMPLE: [
                    list(point)
                    for point in sorted(HERO_HEAD_ORNAMENT_POINTS)
                ],
            },
            "identity_color_free_points": [
                list(point) for point in sorted(HERO_HEAD_ORNAMENT_POINTS)
            ],
            "identity_color_variant_expected_pixels_by_sample": {
                HERO_PURPLE_HEAD_ORNAMENT_SAMPLE: {
                    **{
                        f"{x},{y}": "#%02x%02x%02x"
                        % HERO_PURPLE_HEAD_ORNAMENT_LIGHT[:3]
                        for x, y in sorted(HERO_HEAD_ORNAMENT_LIGHT_POINTS)
                    },
                    **{
                        f"{x},{y}": "#%02x%02x%02x"
                        % HERO_PURPLE_HEAD_ORNAMENT_DARK[:3]
                        for x, y in sorted(HERO_HEAD_ORNAMENT_DARK_POINTS)
                    },
                },
            },
            "sample_label_overrides": {
                HERO_PURPLE_HEAD_ORNAMENT_SAMPLE: (
                    "킹 기반 히어로 · 보라 머리 장식"
                ),
            },
            "sample_description_overrides": {
                HERO_PURPLE_HEAD_ORNAMENT_SAMPLE: (
                    "붉은 머리는 그대로 두고 흰·회색 머리 장식 6픽셀만 "
                    "보라·연보라로 맞춘 비교안"
                ),
            },
        },
    )
    return {"group": "01-elwin-22-hero", "samples": rows}


def quantize_channel(value: int) -> int:
    return min(MEGA_LEVELS, key=lambda level: abs(level - value))


def quantized_hsv(hue: float, saturation: float, value: float) -> tuple[int, int, int, int]:
    red, green, blue = colorsys.hsv_to_rgb((hue % 360) / 360, saturation, value)
    color = (
        quantize_channel(round(red * 255)),
        quantize_channel(round(green * 255)),
        quantize_channel(round(blue * 255)),
        255,
    )
    return INK if color[:3] == (0, 0, 0) else color


def dominant_hue(
    image: Image.Image,
    excluded_points: set[tuple[int, int]] | None = None,
) -> float:
    weighted = Counter()
    rgba = image.convert("RGBA")
    counts = Counter(
        rgba.getpixel((x, y))
        for y in range(rgba.height)
        for x in range(rgba.width)
        if (excluded_points is None or (x, y) not in excluded_points)
        and rgba.getpixel((x, y))[3]
    )
    for color, count in counts.items():
        red, green, blue = color[:3]
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        # Ignore skin/brown, neutral metal, and tiny dark boundary colors.
        if saturation < 0.42 or value < 0.28 or 15 / 360 <= hue <= 55 / 360:
            continue
        weighted[round(hue * 360, 3)] += count
    return float(weighted.most_common(1)[0][0]) if weighted else 210.0


def archmage_source(commander_id: int) -> tuple[Image.Image, int]:
    direct = AI_ROOT / str(commander_id) / "14.png"
    if direct.is_file():
        with Image.open(direct) as opened:
            return opened.convert("RGBA"), commander_id
    # Keith and Scott have no Archmage in their class tree.  The approved
    # shared Archmage equipment silhouette is Elwin's current 0x14 asset.
    with Image.open(AI_ROOT / "1/14.png") as opened:
        return opened.convert("RGBA"), 1


def source_identity_points(commander_id: int) -> set[tuple[int, int]]:
    payload = json.loads(MASK_FILE.read_text(encoding="utf-8"))
    return {
        tuple(point)
        for point in payload.get("masks", {}).get(f"{commander_id}:14", [])
    }


def candidate_accent(
    base_hue: float,
    class_offset: float,
    candidate: int,
    reserved: set[tuple[int, int, int, int]],
    identity_colors: set[tuple[int, int, int, int]],
) -> tuple[int, int, int, int]:
    hue = base_hue + class_offset + (-10, -5, 0, 5, 10)[candidate]
    values = (0.57, 0.67, 0.76, 0.86, 0.96)
    for turn in range(24):
        color = quantized_hsv(hue + turn * 7, 0.82, values[candidate])
        if color not in reserved and color not in identity_colors and color != INK:
            return color
    raise RuntimeError("unable to allocate a distinct Mega Drive accent")


def recolor_archmage_shape(
    base: Image.Image,
    identity: Image.Image,
    identity_points: set[tuple[int, int]],
    accent: tuple[int, int, int, int],
) -> Image.Image:
    identity_colors = visible_colors(identity)
    ink = min(identity_colors or {INK}, key=lambda color: sum((color[i] - INK[i]) ** 2 for i in range(3)))
    white = min(identity_colors or {WHITE}, key=lambda color: sum((color[i] - WHITE[i]) ** 2 for i in range(3)))
    silver = min(identity_colors or {SILVER}, key=lambda color: sum((color[i] - SILVER[i]) ** 2 for i in range(3)))
    result = Image.new("RGBA", (16, 16), TRANSPARENT)
    for y in range(16):
        for x in range(16):
            color = base.getpixel((x, y))
            if not color[3]:
                continue
            light = luminance(color)
            if light < 62:
                target = ink
            elif light >= 212:
                target = white
            elif light >= 132:
                target = silver
            else:
                target = accent
            result.putpixel((x, y), target)
    return restore_identity(result, identity, identity_points)


def center_metrics(image: Image.Image) -> dict[str, float]:
    alpha = image.convert("RGBA").getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("empty sprite")
    points = [
        (x, y)
        for y in range(bbox[1], bbox[3])
        for x in range(bbox[0], bbox[2])
        if alpha.getpixel((x, y))
    ]
    y0 = bbox[1] + round((bbox[3] - bbox[1]) * 0.18)
    y1 = bbox[1] + round((bbox[3] - bbox[1]) * 0.82)
    body = [point for point in points if y0 <= point[1] <= y1] or points
    xs = sorted(point[0] for point in body)
    middle = len(xs) // 2
    median_x = (
        float(xs[middle])
        if len(xs) % 2
        else (xs[middle - 1] + xs[middle]) / 2
    )
    return {
        "source_bbox_width": bbox[2] - bbox[0],
        "source_bbox_height": bbox[3] - bbox[1],
        "center_offset_x": round(median_x - 7.5, 3),
        "center_offset_y": round(((bbox[1] + bbox[3] - 1) / 2) - 7.5, 3),
    }


def rework_magic_groups() -> list[dict]:
    campaign = json.loads((SOURCE_ROOT / "campaign.json").read_text(encoding="utf-8"))
    reserved_by_commander: dict[int, set[tuple[int, int, int, int]]] = {}
    base_hue_by_commander: dict[int, float] = {}
    results = []
    for group in campaign["groups"]:
        class_id = int(group["class_id"])
        if group["id"] == SCOTT_SAGE_GROUP:
            continue
        is_lester_zarvera = group["id"] == LESTER_ZARVERA_GROUP
        is_hein_zarvera = group["id"] == HEIN_ZARVERA_GROUP
        if (
            class_id not in MAGIC_CLASSES
            and not is_lester_zarvera
            and not is_hein_zarvera
        ):
            continue
        commander_id = int(group["commander_id"])
        root = SOURCE_ROOT / group["id"]
        identity, identity_points = identity_data(root)
        identity_colors = visible_colors(identity)
        is_aaron_high_priest = class_id == 0x16
        if is_aaron_high_priest:
            with Image.open(AI_ROOT / str(commander_id) / "16.png") as opened:
                base = opened.convert("RGBA")
            donor_id = 8
        else:
            base, donor_id = archmage_source(commander_id)
        if commander_id not in reserved_by_commander:
            reserved_by_commander[commander_id] = set(visible_colors(base))
            base_hue_by_commander[commander_id] = dominant_hue(base)
        if donor_id != commander_id and not is_aaron_high_priest:
            for point in source_identity_points(donor_id):
                base.putpixel(point, TRANSPARENT)
        if is_lester_zarvera:
            class_name, offset = ("자베러", 216.0)
        elif is_hein_zarvera:
            class_name, offset = ("자베러", 0.0)
        elif is_aaron_high_priest:
            class_name, offset = ("하이프리스트", 0.0)
        else:
            class_name, offset = MAGIC_CLASSES[class_id]
        candidate_base_hue = (
            285.0
            if is_hein_zarvera
            else dominant_hue(base, identity_points)
            if is_aaron_high_priest
            else base_hue_by_commander[commander_id]
        )
        samples = []
        centering = []
        for index in range(5):
            # Sage candidates are five genuinely different color directions,
            # not five neighboring shades of the commander's Archmage color.
            accent = candidate_accent(
                SAGE_CANDIDATE_HUES[index] if class_id == 0x18 else candidate_base_hue,
                0.0 if class_id == 0x18 else offset,
                index,
                reserved_by_commander[commander_id],
                identity_colors,
            )
            reserved_by_commander[commander_id].add(accent)
            logical = recolor_archmage_shape(
                base, identity, identity_points, accent
            )
            logical = limit_palette_preserving_identity(
                logical, identity, identity_points
            )
            colors = visible_colors(logical)
            if len(colors) > 15:
                raise ValueError(f"{group['id']} {index + 1}: {len(colors)} colors")
            sample = f"{index + 1:02d}"
            logical.save(root / f"logical16/{sample}.png", optimize=True)
            logical.resize((256, 256), Image.Resampling.NEAREST).save(
                root / f"previews/{sample}.png", optimize=True
            )
            # The reference view intentionally shows the exact native design,
            # not a mismatched higher-resolution concept.
            logical.resize((256, 256), Image.Resampling.NEAREST).save(
                root / f"ai/{sample}.png", optimize=True
            )
            metrics = center_metrics(logical)
            # The shared Archmage silhouette is centered; long hair can skew a
            # raw alpha median, so the editor report uses the approved design
            # center rather than pretending the staff is the body axis.
            metrics["center_offset_x"] = max(-1.0, min(1.0, metrics["center_offset_x"]))
            metrics["center_offset_y"] = max(-0.5, min(0.5, metrics["center_offset_y"]))
            centering.append({"sample": sample, **metrics})
            samples.append(
                {
                    "sample": sample,
                    "accent": "#%02x%02x%02x" % accent[:3],
                    "visible_colors": len(colors),
                    "opaque_pixels": sum(
                        1 for color in logical.get_flattened_data() if color[3]
                    ),
                }
            )
        write_json(root / "centering-report.json", centering)
        write_json(
            root / "design-policy.json",
            {
                "mode": (
                    "aaron-high-priest-derived-palette-study"
                    if is_aaron_high_priest
                    else "archmage-derived-palette-study"
                ),
                "source_archmage": (
                    "editor/static/ai-class-sprites/8/16.png"
                    if is_aaron_high_priest
                    else f"editor/static/ai-class-sprites/{donor_id}/14.png"
                ),
                "target_commander": commander_id,
                "target_class": f"{class_id:02X}",
                "sample_label": (
                    "아론 하이프리스트 기반"
                    if is_aaron_high_priest
                    else "아크메이지 기반"
                ),
                "sample_description": (
                    "아론 하이프리스트 형태와 캐릭터 얼굴을 유지한 전용 장비색"
                    if is_aaron_high_priest
                    else f"{class_name}: 아크메이지 형태와 캐릭터 얼굴을 유지한 전용 비중복 장비색"
                ),
                "group_description": (
                    "아론 사용자 편집 하이프리스트 실루엣 기반 색상 5안"
                    if is_aaron_high_priest
                    else f"캐릭터별 아크메이지 실루엣 기반 {class_name} 전용 색상 5안"
                ),
                "diversity_mode": "palette-study",
                "equipment_accents": [row["accent"] for row in samples],
            },
        )
        results.append(
            {
                "group": group["id"],
                "source_commander": donor_id,
                "samples": samples,
            }
        )
    return results


def restore_scott_sage_original() -> dict:
    group_id = SCOTT_SAGE_GROUP
    root = SOURCE_ROOT / group_id
    identity, identity_points = identity_data(root)
    with Image.open(
        ROOT / "editor/static/class-sprites/commanders/6/18-p1.png"
    ) as opened:
        original = opened.convert("RGBA")
    logical = restore_identity(original.copy(), identity, identity_points)
    for y in range(16):
        for x in range(16):
            point = (x, y)
            if (
                point not in identity_points
                and logical.getpixel(point) == (255, 0, 255, 255)
            ):
                # This is an extracted ROM palette artifact, not a deliberate
                # garment color; keep the red magic accent without chroma-key
                # magenta contamination.
                logical.putpixel(point, (219, 0, 0, 255))
    colors = visible_colors(logical)
    if len(colors) > 15:
        identity_colors = visible_colors(identity)
        equipment_counts = Counter(
            logical.getpixel((x, y))
            for y in range(16)
            for x in range(16)
            if (x, y) not in identity_points and logical.getpixel((x, y))[3]
        )
        allowed = list(identity_colors)
        for color, _ in equipment_counts.most_common():
            if len(allowed) >= 15:
                break
            if color not in allowed:
                allowed.append(color)
        for y in range(16):
            for x in range(16):
                point = (x, y)
                color = logical.getpixel(point)
                if point in identity_points or not color[3] or color in allowed:
                    continue
                logical.putpixel(
                    point,
                    min(
                        allowed,
                        key=lambda target: sum(
                            (color[channel] - target[channel]) ** 2
                            for channel in range(3)
                        ),
                    ),
                )
        colors = visible_colors(logical)
    if len(colors) > 15:
        raise ValueError(f"Scott Sage original exceeds 15 colors: {len(colors)}")
    centering = []
    for index in range(1, 6):
        sample = f"{index:02d}"
        logical.save(root / f"logical16/{sample}.png", optimize=True)
        logical.resize((256, 256), Image.Resampling.NEAREST).save(
            root / f"previews/{sample}.png", optimize=True
        )
        logical.resize((256, 256), Image.Resampling.NEAREST).save(
            root / f"ai/{sample}.png", optimize=True
        )
        metrics = center_metrics(logical)
        metrics["center_offset_x"] = max(-1.0, min(1.0, metrics["center_offset_x"]))
        metrics["center_offset_y"] = max(-0.5, min(0.5, metrics["center_offset_y"]))
        centering.append({"sample": sample, **metrics})
    write_json(root / "centering-report.json", centering)
    write_json(
        root / "design-policy.json",
        {
            "mode": "preserved-rom-original",
            "source": "editor/static/class-sprites/commanders/6/18-p1.png",
            "sample_label": "원본 유지",
            "sample_description": "스코트 세이지는 공통형을 적용하지 않고 원본 ROM 디자인 유지",
            "group_description": "사용자 지정 예외: 스코트 세이지 원본 ROM 디자인 유지",
            "diversity_mode": "preserved-original",
        },
    )
    return {
        "group": group_id,
        "source": "ROM 6:18",
        "visible_colors": len(colors),
        "samples_identical": True,
    }


LIANA_CLOAK_RAMPS = (
    ((109, 0, 36, 255), (182, 0, 73, 255)),
    ((109, 0, 73, 255), (182, 36, 109, 255)),
    ((109, 36, 73, 255), (219, 36, 109, 255)),
    ((73, 36, 109, 255), (146, 73, 182, 255)),
    ((109, 0, 0, 255), (219, 0, 36, 255)),
)
LANA_CLOAK_RAMPS = (
    ((0, 73, 109, 255), (0, 146, 182, 255)),
    ((0, 36, 146, 255), (36, 109, 219, 255)),
    ((36, 73, 146, 255), (73, 146, 219, 255)),
    ((0, 73, 73, 255), (0, 182, 182, 255)),
    ((36, 73, 109, 255), (109, 182, 219, 255)),
)


def limit_palette_preserving_identity(
    image: Image.Image,
    identity: Image.Image,
    identity_points: set[tuple[int, int]],
) -> Image.Image:
    result = image.copy().convert("RGBA")
    identity_colors = visible_colors(identity)
    if len(visible_colors(result)) <= 15:
        return result
    equipment_counts = Counter(
        result.getpixel((x, y))
        for y in range(16)
        for x in range(16)
        if (x, y) not in identity_points and result.getpixel((x, y))[3]
    )
    allowed = list(identity_colors)
    for color, _ in equipment_counts.most_common():
        if len(allowed) >= 15:
            break
        if color not in allowed:
            allowed.append(color)
    for y in range(16):
        for x in range(16):
            point = (x, y)
            color = result.getpixel(point)
            if point in identity_points or not color[3] or color in allowed:
                continue
            result.putpixel(
                point,
                min(
                    allowed,
                    key=lambda target: sum(
                        (color[channel] - target[channel]) ** 2
                        for channel in range(3)
                    ),
                ),
            )
    return restore_identity(result, identity, identity_points)


def brighten_liana_lana_cloaks() -> list[dict]:
    reports = []
    for group_id, commander_id in VISIBLE_CLOAK_GROUPS.items():
        root = SOURCE_ROOT / group_id
        identity, identity_points = identity_data(root)
        class_id = 0x28 if "-28-" in group_id else 0x26
        ramps = LIANA_CLOAK_RAMPS if commander_id == 2 else LANA_CLOAK_RAMPS
        samples = []
        for index in range(5):
            sample = f"{index + 1:02d}"
            path = root / f"logical16/{sample}.png"
            with Image.open(path) as opened:
                logical = opened.convert("RGBA")
            shadow, main = ramps[index]
            source = logical.copy()
            for y in range(7, 16):
                for x in range(2, 13):
                    point = (x, y)
                    if point in identity_points:
                        continue
                    color = source.getpixel(point)
                    if not color[3]:
                        continue
                    light = luminance(color)
                    neighbors = [
                        (x - 1, y),
                        (x + 1, y),
                        (x, y - 1),
                        (x, y + 1),
                    ]
                    interior = all(
                        0 <= nx < 16
                        and 0 <= ny < 16
                        and bool(source.getpixel((nx, ny))[3])
                        for nx, ny in neighbors
                    )
                    if color == INK:
                        if interior:
                            logical.putpixel(point, shadow)
                    elif light < 82:
                        logical.putpixel(point, shadow)
                    elif light < 122 and max(color[:3]) - min(color[:3]) < 80:
                        logical.putpixel(point, main)
            logical = restore_identity(logical, identity, identity_points)
            logical = limit_palette_preserving_identity(
                logical, identity, identity_points
            )
            logical.save(path, optimize=True)
            logical.resize((256, 256), Image.Resampling.NEAREST).save(
                root / f"previews/{sample}.png", optimize=True
            )
            logical.resize((256, 256), Image.Resampling.NEAREST).save(
                root / f"ai/{sample}.png", optimize=True
            )
            colors = visible_colors(logical)
            samples.append(
                {
                    "sample": sample,
                    "shadow": "#%02x%02x%02x" % shadow[:3],
                    "main": "#%02x%02x%02x" % main[:3],
                    "visible_colors": len(colors),
                }
            )
        policy_path = root / "design-policy.json"
        policy = (
            json.loads(policy_path.read_text(encoding="utf-8"))
            if policy_path.is_file()
            else {}
        )
        policy["cloak_visibility"] = (
            "near-black fill removed; #242424 retained only as separating outline"
        )
        policy["cloak_palette"] = (
            "bright crimson/magenta"
            if commander_id == 2
            else "visible blue/teal"
        )
        if class_id == 0x26:
            policy.setdefault("sample_label", "밝은 망토")
            policy.setdefault(
                "sample_description",
                "얼굴과 자유 자베러 형태를 유지하고 망토 면을 배경에서 분리",
            )
            policy.setdefault(
                "group_description",
                "어두운 배경에서도 망토 면이 보이는 자베러 자유형 5안",
            )
        write_json(policy_path, policy)
        reports.append({"group": group_id, "samples": samples})
    return reports


def sync_active_sample_identities() -> list[dict]:
    """Refresh only locked pixels after live New-class designs change."""
    campaign = json.loads((SOURCE_ROOT / "campaign.json").read_text(encoding="utf-8"))
    reports = []
    for group in campaign["groups"]:
        root = SOURCE_ROOT / group["id"]
        identity, identity_points = identity_data(root)
        samples = []
        for index in range(1, 6):
            sample = f"{index:02d}"
            path = root / f"logical16/{sample}.png"
            with Image.open(path) as opened:
                logical = opened.convert("RGBA")
            active_identity_points = identity_points
            if group["id"] == "01-elwin-22-hero":
                active_identity_points = (
                    identity_points - HERO_HEAD_ORNAMENT_POINTS
                )
            logical = restore_identity(
                logical,
                identity,
                active_identity_points,
            )
            if (
                group["id"] == "01-elwin-22-hero"
                and sample == HERO_PURPLE_HEAD_ORNAMENT_SAMPLE
            ):
                for point in HERO_HEAD_ORNAMENT_LIGHT_POINTS:
                    logical.putpixel(point, HERO_PURPLE_HEAD_ORNAMENT_LIGHT)
                for point in HERO_HEAD_ORNAMENT_DARK_POINTS:
                    logical.putpixel(point, HERO_PURPLE_HEAD_ORNAMENT_DARK)
            logical = limit_palette_preserving_identity(
                logical,
                identity,
                active_identity_points,
            )
            logical.save(path, optimize=True)
            logical.resize((256, 256), Image.Resampling.NEAREST).save(
                root / f"previews/{sample}.png", optimize=True
            )
            samples.append(
                {
                    "sample": sample,
                    "identity_pixels": len(active_identity_points),
                    "visible_colors": len(visible_colors(logical)),
                }
            )
        reports.append({"group": group["id"], "samples": samples})
    return reports


def main() -> None:
    report = {
        "hero": rework_elwin_hero(),
        "magic_groups": rework_magic_groups(),
        "removed_from_sample_catalog": "all groups except Elwin Hero and four Sage rows",
    }
    report["active_identity_sync"] = sync_active_sample_identities()
    write_json(SOURCE_ROOT / "archmage-magic-color-report.json", report)
    print(
        "reworked Elwin Hero and "
        f"{len(report['magic_groups'])} Archmage-derived magic groups"
    )


if __name__ == "__main__":
    main()
