#!/usr/bin/env python3
"""Build full-ratio and identity-only AI references from editor state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "editor/static/ai-class-sprites/manifest.json"
DEFAULT_SPRITE_DIR = ROOT / "editor/static/class-sprites/commanders"
DEFAULT_MOUNT_MASKS = ROOT / "editor/ai_mount_masks.json"
MAGENTA = (255, 0, 255, 255)
RESAMPLING = getattr(Image, "Resampling", Image)


def build_guides(
    commander_id: int,
    class_ids: list[int],
    output_dir: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
    sprite_dir: Path = DEFAULT_SPRITE_DIR,
    mount_mask_path: Path = DEFAULT_MOUNT_MASKS,
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest["commanders"][str(commander_id)]["classes"]
    output_dir.mkdir(parents=True, exist_ok=True)
    point_document: dict[str, list[list[int]]] = {}
    reports: list[dict[str, object]] = []
    full_images: list[Image.Image] = []
    masked_images: list[Image.Image] = []
    mount_images: list[Image.Image] = []
    mount_document = (
        json.loads(mount_mask_path.read_text(encoding="utf-8"))
        if mount_mask_path.is_file()
        else {"version": 1, "masks": {}}
    )
    if mount_document.get("version") != 1:
        raise ValueError("unsupported AI mount-mask file version")
    raw_mount_masks = mount_document.get("masks", {})
    if not isinstance(raw_mount_masks, dict):
        raise ValueError("AI mount-mask masks must be an object")
    mount_point_document: dict[str, list[list[int]]] = {}

    for class_id in class_ids:
        row = rows[str(class_id)]
        points = {
            tuple(point)
            for point in row["identity_lock_points"]
        }
        original = Image.open(
            sprite_dir / str(commander_id) / f"{class_id:02X}-p1.png"
        ).convert("RGBA")
        if original.size != (16, 16):
            raise ValueError(
                f"original {commander_id}:{class_id:02X} must be 16x16"
            )

        full = Image.new("RGBA", (16, 16), MAGENTA)
        full.alpha_composite(original)
        masked = Image.new("RGBA", (16, 16), MAGENTA)
        for point in points:
            color = original.getpixel(point)
            if color[3] != 0:
                masked.putpixel(point, color)
        mount_points = {
            tuple(point)
            for point in raw_mount_masks.get(
                f"{commander_id}:{class_id:02X}",
                [],
            )
        }
        mount = Image.new("RGBA", (16, 16), MAGENTA)
        for point in mount_points:
            color = original.getpixel(point)
            if color[3] != 0:
                mount.putpixel(point, color)

        full.resize((1024, 1024), RESAMPLING.NEAREST).save(
            output_dir / f"{class_id:02X}-original-full-ratio.png",
            optimize=True,
        )
        masked.resize((1024, 1024), RESAMPLING.NEAREST).save(
            output_dir / f"{class_id:02X}-masked-identity.png",
            optimize=True,
        )
        mount.resize((1024, 1024), RESAMPLING.NEAREST).save(
            output_dir / f"{class_id:02X}-masked-mount.png",
            optimize=True,
        )
        full_images.append(full)
        masked_images.append(masked)
        mount_images.append(mount)
        point_document[f"{class_id:02X}"] = [
            list(point) for point in sorted(points)
        ]
        mount_point_document[f"{class_id:02X}"] = [
            list(point) for point in sorted(mount_points)
        ]
        reports.append(
            {
                "class_id": f"{class_id:02X}",
                "class_name": row["class_name"],
                "identity_lock_mode": row["identity_lock_mode"],
                "identity_pixel_count": len(points),
                "mount_pixel_count": len(mount_points),
            }
        )

    board_size = 1024
    board_columns = 4
    board_rows = 4
    cell_size = board_size // board_columns
    for filename, images in (
        ("original-reference-board.png", full_images),
        ("masked-identity-board.png", masked_images),
        ("masked-mount-board.png", mount_images),
    ):
        board = Image.new(
            "RGBA",
            (board_size, board_size),
            MAGENTA,
        )
        for index, image in enumerate(images):
            row, column = divmod(index, board_columns)
            board.alpha_composite(
                image.resize(
                    (cell_size, cell_size),
                    RESAMPLING.NEAREST,
                ),
                (column * cell_size, row * cell_size),
            )
        board.save(output_dir / filename, optimize=True)

    metadata = {
        "version": 1,
        "commander_id": commander_id,
        "commander_name": manifest["commanders"][str(commander_id)]["name"],
        "source_manifest_version": manifest["asset_version"],
        "classes": reports,
        "identity_points": point_document,
        "mount_points": mount_point_document,
        "board_layout": {
            "columns": board_columns,
            "rows": board_rows,
            "class_ids": [f"{class_id:02X}" for class_id in class_ids],
            "original": "original-reference-board.png",
            "masked": "masked-identity-board.png",
            "mount": "masked-mount-board.png",
        },
    }
    (output_dir / "identity-points.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def parse_class_id(value: str) -> int:
    return int(value, 16)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commander-id", required=True, type=int)
    parser.add_argument(
        "--class-id",
        action="append",
        required=True,
        type=parse_class_id,
        dest="class_ids",
        help="hexadecimal class ID; repeat for every desired class",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--mount-masks",
        type=Path,
        default=DEFAULT_MOUNT_MASKS,
    )
    args = parser.parse_args()
    metadata = build_guides(
        args.commander_id,
        args.class_ids,
        args.output_dir.resolve(),
        args.manifest.resolve(),
        DEFAULT_SPRITE_DIR,
        args.mount_masks.resolve(),
    )
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == "__main__":
    main()
