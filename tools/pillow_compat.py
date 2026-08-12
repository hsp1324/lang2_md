"""Small Pillow-version compatibility helpers used by image tooling.

Pillow 11 introduced ``Image.get_flattened_data`` as the replacement for
``Image.getdata``.  The project still supports Pillow 9 and 10, so callers use
these helpers instead of depending on import-order monkey patches or on a
particular default-font implementation.
"""

from __future__ import annotations

from PIL import Image, ImageDraw


def flattened_image_data(image: Image.Image):
    """Return Pillow's flat pixel iterator on both old and new releases."""

    modern_getter = getattr(image, "get_flattened_data", None)
    if modern_getter is not None:
        return modern_getter()
    return image.getdata()


def text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
) -> tuple[int, int, int, int]:
    """Measure default-font text across supported Pillow releases.

    Some distro builds of Pillow 9 expose ``textbbox`` but reject Pillow's
    bitmap default font.  Their legacy ``textsize`` path supports that font;
    newer Pillow releases support it through ``textbbox`` and have removed
    ``textsize``.
    """

    modern_getter = getattr(draw, "textbbox", None)
    if modern_getter is not None:
        try:
            return modern_getter(xy, text)
        except ValueError as exc:
            if "Only supported for TrueType fonts" not in str(exc):
                raise

    legacy_getter = getattr(draw, "textsize", None)
    if legacy_getter is None:
        raise AttributeError("Pillow has neither usable textbbox nor textsize")
    width, height = legacy_getter(text)
    x, y = xy
    return x, y, x + width, y + height
