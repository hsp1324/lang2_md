#!/usr/bin/env python3
"""Prepare and run native 16x16 masked PixelLab trials for Elwin.

This pipeline never generates a large image and never pastes the ROM head back
after generation.  The original 16x16 class sprite is the inpainting input.
The face and hair rectangle is black in the mask, so the service must preserve
those pixels while it redraws the body and class equipment around them.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "editor/static/class-sprites/commanders/1"
DEFAULT_OUTPUT = (
    ROOT / "docs/assets/ai-class-source/pixellab-elwin-trial"
)
DEFAULT_TOKEN_FILE = Path.home() / ".config/pixellab/token"
API_URL = "https://api.pixellab.ai/v2/inpaint"
SKIN = (219, 182, 109, 255)
RESAMPLING = getattr(Image, "Resampling", Image)

CLASS_PROMPTS = {
    0x04: (
        "LORD",
        "silver cuirass and shoulder armor, a short crimson cape behind the "
        "left shoulder, a small red-and-gold heater shield on the right "
        "forearm, and a straight sword held diagonally away from the body",
    ),
    0x0B: (
        "HIGH LORD",
        "heavier silver plate armor, long crimson commander's cape, ornate "
        "straight sword, gold-trimmed shield",
    ),
    0x0C: (
        "HIGHLANDER",
        "light silver cavalry armor, crimson sash, long lance, compact horse",
    ),
    0x12: (
        "BISHOP",
        "white bishop vestments over light armor, red stole, small golden "
        "holy staff",
    ),
    0x13: (
        "MAGE",
        "crimson battle robe, short mantle, compact gold staff with a red orb",
    ),
    0x14: (
        "ARCHMAGE",
        "white-and-gold archmage robe, crimson lining, ornate compact staff "
        "with a red crystal",
    ),
    0x1A: (
        "SWORDMASTER",
        "light silver duelist armor, crimson waist sash, readable two-handed "
        "greatsword",
    ),
    0x1B: (
        "KNIGHT MASTER",
        "crimson-and-gold cavalry armor, armored brown horse, knight sword",
    ),
    0x1D: (
        "SILVER KNIGHT",
        "blue-and-silver cavalry armor, pale armored horse, long silver lance",
    ),
    0x22: (
        "HERO",
        "white silver heroic plate, royal blue and crimson accents, ornate "
        "sword and small gold-trimmed shield",
    ),
}

NEGATIVE_PROMPT = (
    "portrait, bust, floating head, oversized head, tiny body, disconnected "
    "neck, different face, different hair, helmet covering hair, symmetrical "
    "front view, cropped feet, horse, wings, magic, extra weapons, oversized "
    "shield, shield covering torso, merged equipment, smooth shading, "
    "missing limbs, transparent holes inside the body, anti-aliasing, blur, "
    "one-pixel noise, background, ground shadow, text, border, more than one "
    "character"
)


def connected_face(source: Image.Image) -> set[tuple[int, int]]:
    """Find the connected skin cluster belonging to the face, not the hands."""

    remaining = {
        (x, y)
        for y in range(10)
        for x in range(16)
        if source.getpixel((x, y)) == SKIN
    }
    components: list[set[tuple[int, int]]] = []
    while remaining:
        start = remaining.pop()
        component = {start}
        pending = [start]
        while pending:
            x, y = pending.pop()
            for near_y in range(max(0, y - 1), min(10, y + 2)):
                for near_x in range(max(0, x - 1), min(16, x + 2)):
                    point = (near_x, near_y)
                    if point in remaining:
                        remaining.remove(point)
                        component.add(point)
                        pending.append(point)
        components.append(component)
    if not components:
        raise ValueError("source sprite has no detectable Elwin face")
    # Elwin's actual face is the upper skin cluster beside his brown hair.
    # The larger lower cluster is his exposed hand.  Selecting by size caused
    # the old mask to freeze the torso while leaving the real face editable.
    return min(
        components,
        key=lambda component: (
            min(y for _, y in component),
            -len(component),
        ),
    )


def head_lock_box(source: Image.Image) -> tuple[int, int, int, int]:
    """Return a face/hair/context box in native 16x16 coordinates."""

    face = connected_face(source)
    left = max(0, min(x for x, _ in face) - 6)
    top = max(0, min(y for _, y in face) - 1)
    right = min(16, max(x for x, _ in face) + 2)
    bottom = min(16, max(y for _, y in face) + 3)
    return left, top, right, bottom


def inpaint_mask(
    source: Image.Image,
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Build a PixelLab mask: redraw the body but freeze head and background."""

    box = head_lock_box(source)
    # Keeping the transparent source background black prevents the model from
    # shrinking, recentering, or floating the character inside a fully
    # editable canvas.  The original silhouette already has enough room for
    # Lord's sword, cape, and shield; only its occupied body pixels need paint.
    mask = Image.new("L", (16, 16), 0)
    for y in range(16):
        for x in range(16):
            if source.getpixel((x, y))[3]:
                mask.putpixel((x, y), 255)
    left, top, right, bottom = box
    for y in range(top, bottom):
        for x in range(left, right):
            mask.putpixel((x, y), 0)
    return mask, box


def prompt_for(class_id: int, canvas_size: int) -> str:
    class_name, equipment = CLASS_PROMPTS[class_id]
    description = (
        f"Elwin {class_name} commander, full body. Preserve the input's exact "
        "pose, body proportions, size, sword silhouette, and bottom-aligned "
        "stance. The locked original brown-haired head is final. Continue its "
        "neck naturally into the same shoulders. Change only the clothing and "
        f"equipment design to {equipment}. Keep the red cape on screen-left "
        "and the small shield distinct on screen-right. Preserve clear dark "
        "gaps between the head, shoulders, arms, torso, legs, sword, and "
        "shield. Low top-down three-quarter view, facing south-east. "
    )
    description += (
        "Every editable pixel belongs to the existing character silhouette; "
        "keep all of those pixels opaque and fill them with character art. "
        "Do not erase or hollow out the body. "
    )
    if canvas_size == 16:
        description += (
            "Native 16x16 pixel art. Every output pixel is a final sprite "
            "pixel; use large readable color clusters and no sub-pixel "
            "details. "
        )
    else:
        description += (
            "Logical 16x16 pixel art rendered as uniform 2x2 blocks on this "
            "32x32 canvas. "
        )
    return description + "Transparent background."


def png_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def decode_api_image(value: str) -> Image.Image:
    payload = value.split(",", 1)[-1]
    return Image.open(io.BytesIO(base64.b64decode(payload))).convert("RGBA")


def exact_locked_pixels(
    source: Image.Image,
    candidate: Image.Image,
    mask: Image.Image,
) -> bool:
    return all(
        mask.getpixel((x, y)) != 0
        or candidate.getpixel((x, y)) == source.getpixel((x, y))
        for y in range(source.height)
        for x in range(source.width)
    )


def candidate_score(
    source: Image.Image,
    candidate: Image.Image,
    mask: Image.Image,
) -> tuple[int, dict[str, object]]:
    alpha = candidate.getchannel("A")
    bbox = alpha.getbbox()
    colors = candidate.getcolors(maxcolors=257) or []
    changed_editable = sum(
        mask.getpixel((x, y)) != 0
        and candidate.getpixel((x, y)) != source.getpixel((x, y))
        for y in range(source.height)
        for x in range(source.width)
    )
    locked_exact = exact_locked_pixels(source, candidate, mask)
    bottom_aligned = bbox is not None and bbox[3] == 16
    alpha_binary = {
        color for _, color in (alpha.getcolors(maxcolors=257) or [])
    }.issubset({0, 255})
    occupied = sum(1 for value in alpha.getdata() if value)
    score = (
        1000 * int(locked_exact)
        + 100 * int(bottom_aligned)
        + 50 * int(alpha_binary)
        + min(changed_editable, 80)
        - max(0, len(colors) - 24) * 2
        - max(0, occupied - 190)
    )
    return score, {
        "locked_pixels_exact": locked_exact,
        "bottom_aligned": bottom_aligned,
        "alpha_binary": alpha_binary,
        "color_count": len(colors),
        "occupied_pixel_count": occupied,
        "changed_editable_pixel_count": changed_editable,
    }


def prepare(
    class_id: int,
    output_dir: Path,
    canvas_size: int,
) -> dict[str, object]:
    class_hex = f"{class_id:02X}"
    source_path = SOURCE_DIR / f"{class_hex}-p1.png"
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    source = Image.open(source_path).convert("RGBA")
    mask, box = inpaint_mask(source)
    output_dir.mkdir(parents=True, exist_ok=True)
    source.save(output_dir / f"{class_hex}-source-16.png")
    mask.save(output_dir / f"{class_hex}-mask-16.png")
    working_source = source
    working_mask = mask
    if canvas_size != 16:
        working_source = source.resize(
            (canvas_size, canvas_size),
            RESAMPLING.NEAREST,
        )
        working_mask = mask.resize(
            (canvas_size, canvas_size),
            RESAMPLING.NEAREST,
        )
        working_source.save(
            output_dir / f"{class_hex}-source-{canvas_size}.png"
        )
        working_mask.save(
            output_dir / f"{class_hex}-mask-{canvas_size}.png"
        )
    source.resize((256, 256), RESAMPLING.NEAREST).save(
        output_dir / f"{class_hex}-source-preview.png"
    )
    mask.resize((256, 256), RESAMPLING.NEAREST).save(
        output_dir / f"{class_hex}-mask-preview.png"
    )
    request_template = {
        "description": prompt_for(class_id, canvas_size),
        "negative_description": NEGATIVE_PROMPT,
        "image_size": {"width": canvas_size, "height": canvas_size},
        "text_guidance_scale": 6,
        "outline": "single color black outline",
        "shading": "basic shading",
        "detail": "medium detail",
        "view": "low top-down",
        "direction": "south-east",
        # The transparent exterior is already frozen by the mask.  Enabling
        # background removal here made the model erase opaque body pixels.
        "no_background": False,
        "init_image_strength": 300,
        "inpainting_image": {
            "type": "base64",
            "base64": f"<{class_hex}-source-{canvas_size}.png>",
            "format": "png",
        },
        "mask_image": {
            "type": "base64",
            "base64": f"<{class_hex}-mask-{canvas_size}.png>",
            "format": "png",
        },
        "seed": "<candidate seed>",
    }
    metadata = {
        "class_id": class_id,
        "class_hex": class_hex,
        "class_name": CLASS_PROMPTS[class_id][0],
        "canvas": [canvas_size, canvas_size],
        "logical_canvas": [16, 16],
        "integer_scale": canvas_size // 16,
        "head_lock_box": list(box),
        "mask_semantics": "black=preserve exactly, white=generate",
        "api": API_URL,
        "request_template": request_template,
    }
    (output_dir / f"{class_hex}-request.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def call_api(
    token: str,
    source: Image.Image,
    mask: Image.Image,
    class_id: int,
    seed: int,
) -> Image.Image:
    request_body = {
        "description": prompt_for(class_id, source.width),
        "negative_description": NEGATIVE_PROMPT,
        "image_size": {"width": 16, "height": 16},
        "text_guidance_scale": 6,
        "outline": "single color black outline",
        "shading": "basic shading",
        "detail": "medium detail",
        "view": "low top-down",
        "direction": "south-east",
        # The mask already freezes the transparent exterior.
        "no_background": False,
        "init_image": {
            "type": "base64",
            "base64": png_base64(source),
            "format": "png",
        },
        "init_image_strength": 300,
        "inpainting_image": {
            "type": "base64",
            "base64": png_base64(source),
            "format": "png",
        },
        "mask_image": {
            "type": "base64",
            "base64": png_base64(mask.convert("RGB")),
            "format": "png",
        },
        "color_image": {
            "type": "base64",
            "base64": png_base64(source),
            "format": "png",
        },
        "seed": seed,
    }
    request_body["image_size"] = {
        "width": source.width,
        "height": source.height,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"PixelLab HTTP {error.code}: {detail}") from error
    return decode_api_image(result["image"]["base64"])


def make_contact_sheet(
    candidates: list[tuple[int, Image.Image]],
    output_path: Path,
) -> None:
    scale = 16
    cell = 16 * scale
    sheet = Image.new("RGBA", (cell * max(1, len(candidates)), cell))
    for column, (_, candidate) in enumerate(candidates):
        enlarged = candidate.resize((cell, cell), RESAMPLING.NEAREST)
        sheet.alpha_composite(enlarged, (column * cell, 0))
    sheet.save(output_path)


def collapse_integer_blocks(
    image: Image.Image,
    scale: int,
) -> Image.Image:
    """Collapse uniform logical pixel blocks without interpolation or blur."""

    if scale == 1:
        return image.copy()
    if image.width != 16 * scale or image.height != 16 * scale:
        raise ValueError(
            f"cannot collapse {image.size} with logical scale {scale}"
        )
    collapsed = Image.new("RGBA", (16, 16))
    for y in range(16):
        for x in range(16):
            counts: dict[tuple[int, int, int, int], int] = {}
            order: list[tuple[int, int, int, int]] = []
            for source_y in range(y * scale, (y + 1) * scale):
                for source_x in range(x * scale, (x + 1) * scale):
                    color = image.getpixel((source_x, source_y))
                    if color not in counts:
                        counts[color] = 0
                        order.append(color)
                    counts[color] += 1
            selected = max(order, key=lambda color: counts[color])
            collapsed.putpixel((x, y), selected)
    return collapsed


def run_trials(
    class_id: int,
    output_dir: Path,
    seeds: list[int],
    token_file: Path,
    canvas_size: int,
) -> None:
    token = os.environ.get("PIXELLAB_API_TOKEN", "").strip()
    if not token and token_file.is_file():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit(
            f"no token found in PIXELLAB_API_TOKEN or {token_file}; inputs "
            "were prepared but no API request was sent"
        )
    class_hex = f"{class_id:02X}"
    logical_source = Image.open(
        output_dir / f"{class_hex}-source-16.png"
    ).convert("RGBA")
    logical_mask = Image.open(
        output_dir / f"{class_hex}-mask-16.png"
    ).convert("L")
    source = Image.open(
        output_dir / f"{class_hex}-source-{canvas_size}.png"
    ).convert("RGBA")
    mask = Image.open(
        output_dir / f"{class_hex}-mask-{canvas_size}.png"
    ).convert("L")
    scale = canvas_size // 16
    accepted: list[tuple[int, Image.Image]] = []
    report = []
    for index, seed in enumerate(seeds):
        if index:
            time.sleep(1)
        candidate = call_api(token, source, mask, class_id, seed)
        if candidate.size != (canvas_size, canvas_size):
            raise ValueError(
                f"seed {seed} returned {candidate.size}, "
                f"expected {canvas_size}x{canvas_size}"
            )
        raw_locked_exact = exact_locked_pixels(source, candidate, mask)
        collapsed = collapse_integer_blocks(candidate, scale)
        score, checks = candidate_score(
            logical_source,
            collapsed,
            logical_mask,
        )
        checks["raw_locked_pixels_exact"] = raw_locked_exact
        checks.update({"seed": seed, "score": score})
        if raw_locked_exact and checks["locked_pixels_exact"]:
            candidate.save(
                output_dir
                / f"{class_hex}-candidate-{seed}-{canvas_size}.png"
            )
            collapsed.save(
                output_dir / f"{class_hex}-candidate-{seed}.png"
            )
            accepted.append((seed, collapsed))
            checks["accepted"] = True
        else:
            checks["accepted"] = False
            checks["reason"] = "PixelLab changed a black locked pixel"
        report.append(checks)
    accepted.sort(
        key=lambda item: candidate_score(
            logical_source,
            item[1],
            logical_mask,
        )[0],
        reverse=True,
    )
    make_contact_sheet(
        accepted,
        output_dir / f"{class_hex}-candidate-contact.png",
    )
    (output_dir / f"{class_hex}-candidate-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--class-id",
        type=lambda value: int(value, 0),
        default=0x04,
        choices=sorted(CLASS_PROMPTS),
    )
    parser.add_argument(
        "--canvas-size",
        type=int,
        choices=(16, 32),
        default=16,
        help="working canvas; 16 is native and 32 is an experimental 2x grid",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--token-file",
        type=Path,
        default=DEFAULT_TOKEN_FILE,
        help="local secret file used when PIXELLAB_API_TOKEN is unset",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="consume PixelLab generation credits after preparing the inputs",
    )
    parser.add_argument(
        "--seeds",
        default="1337",
        help="comma-separated candidate seeds",
    )
    args = parser.parse_args()
    prepare(args.class_id, args.output, args.canvas_size)
    if args.run:
        seeds = [int(value) for value in args.seeds.split(",") if value]
        run_trials(
            args.class_id,
            args.output,
            seeds,
            args.token_file,
            args.canvas_size,
        )


if __name__ == "__main__":
    main()
