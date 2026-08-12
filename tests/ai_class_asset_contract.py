"""Shared readers for current AI class-sprite regression contracts."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from tools import build_ai_class_sprite_assets as builder
from tools.pillow_compat import flattened_image_data


ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = ROOT / "editor/static/ai-class-sprites"
ROM_SPRITE_ROOT = ROOT / "editor/static/class-sprites/commanders"


def rgba(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        return opened.convert("RGBA")


def pixels(image: Image.Image) -> tuple[object, ...]:
    return tuple(flattened_image_data(image))


def visible_colors(image: Image.Image) -> set[tuple[int, int, int, int]]:
    return {
        color
        for color in flattened_image_data(image)
        if isinstance(color, tuple) and len(color) == 4 and color[3]
    }


def manifest() -> dict[str, object]:
    return json.loads(
        (LIVE_ROOT / "manifest.json").read_text(encoding="utf-8")
    )


def manifest_row(
    document: dict[str, object],
    commander_id: int,
    class_id: int,
) -> dict[str, object]:
    commanders = document["commanders"]
    assert isinstance(commanders, dict)
    commander = commanders[str(commander_id)]
    assert isinstance(commander, dict)
    classes = commander["classes"]
    assert isinstance(classes, dict)
    row = classes[str(class_id)]
    assert isinstance(row, dict)
    return row


def design_overrides() -> dict[tuple[int, int], dict[str, object]]:
    return builder.load_ai_design_overrides()


def override_image(
    key: tuple[int, int],
    overrides: dict[tuple[int, int], dict[str, object]] | None = None,
) -> Image.Image:
    values = design_overrides() if overrides is None else overrides
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    image.putdata(values[key]["pixels"])
    return image


def compose_untranslated_shared_source(
    key: tuple[int, int],
    *,
    document: dict[str, object] | None = None,
) -> Image.Image:
    """Recompose a retained shared source through the current v107 stages."""

    current_manifest = manifest() if document is None else document
    row = manifest_row(current_manifest, *key)
    if row["identity_translation"] is not None:
        raise ValueError(f"translated identity is not supported here: {key}")

    source_path, _ = builder.SHARED_CLASS_TEMPLATE_SOURCES[key]
    image = rgba(source_path)
    overrides = design_overrides()
    if row["design_override"]:
        image = override_image(key, overrides)

    if row["identity_lock_transparency_mode"] != "approved_full_sprite_template":
        original = rgba(
            ROM_SPRITE_ROOT
            / str(key[0])
            / f"{key[1]:02X}-p1.png"
        )
        lock_points = {
            tuple(point)
            for point in (
                list(row["identity_lock_points"])
                + list(row["mount_lock_points"])
            )
        }
        for point in lock_points:
            if original.getpixel(point)[3]:
                image.putpixel(point, original.getpixel(point))
    else:
        lock_points = set()

    mount_variant = builder.MOUNT_COLOR_VARIANTS.get(key)
    if mount_variant is not None:
        identity_points = {
            tuple(point) for point in row["identity_lock_points"]
        }
        for point in {
            tuple(point) for point in row["mount_lock_points"]
        } - identity_points:
            color = image.getpixel(point)
            if color in mount_variant:
                image.putpixel(point, mount_variant[color])

    for point, color in builder.FINAL_PIXEL_OVERRIDES.get(key, {}).items():
        image.putpixel(point, color)

    if key[0] != 1:
        for point in builder.SHARED_DARK_BOUNDARY_REFERENCE_POINTS.get(
            key[1], set()
        ):
            if point not in lock_points and not image.getpixel(point)[3]:
                image.putpixel(point, builder.ROM_INK)

    builder.close_internal_transparency(image)
    return image


def compose_rom_mount_variant(
    key: tuple[int, int],
    *,
    document: dict[str, object] | None = None,
) -> Image.Image:
    """Apply the v107 mount-mask palette transform to a stock ROM sprite."""

    current_manifest = manifest() if document is None else document
    row = manifest_row(current_manifest, *key)
    image = rgba(
        ROM_SPRITE_ROOT / str(key[0]) / f"{key[1]:02X}-p1.png"
    )
    identity_points = {
        tuple(point) for point in row["identity_lock_points"]
    }
    mount_points = {
        tuple(point) for point in row["mount_lock_points"]
    }
    color_variant = builder.MOUNT_COLOR_VARIANTS[key]
    for point in mount_points - identity_points:
        color = image.getpixel(point)
        if color in color_variant:
            image.putpixel(point, color_variant[color])
    builder.close_internal_transparency(image)
    return image
