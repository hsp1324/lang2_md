#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA = ROOT / "localization/item_shop_inventory.json"
DEFAULT_CAPTURE_DIR = ROOT / "captures/run"
DEFAULT_OUTPUT = ROOT / "editor/static/item-icons"
CAPTURE_PREFIX = "97e0_item_id"
ROWS_PER_PAGE = 5
ICON_X = 24
ICON_Y = 42
ROW_HEIGHT = 14
ICON_SIZE = 16


def icon_crop(item_id: int) -> tuple[int, int, int, int]:
    if not 1 <= item_id <= 37:
        raise ValueError("item ID must be 1..37")
    row = (item_id - 1) % ROWS_PER_PAGE
    top = ICON_Y + row * ROW_HEIGHT
    return (ICON_X, top, ICON_X + ICON_SIZE, top + ICON_SIZE)


def build_assets(
    metadata_path: Path,
    capture_dir: Path,
    output_dir: Path,
) -> dict[str, object]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    assets: dict[str, object] = {}
    for row in metadata["items"]:
        item_id = int(row["id"])
        source = capture_dir / f"{CAPTURE_PREFIX}{item_id:02d}.png"
        if not source.is_file():
            raise FileNotFoundError(source)
        with Image.open(source) as image:
            if image.size != (320, 240):
                raise ValueError(
                    f"unexpected capture size for {source}: {image.size}"
                )
            crop = icon_crop(item_id)
            target = output_dir / f"{item_id:02d}.png"
            image.convert("RGB").crop(crop).save(target, optimize=True)
        assets[str(item_id)] = {
            "file": target.name,
            "name": row["target_korean"],
            "source": str(source.relative_to(ROOT)),
            "crop": list(crop),
        }

    manifest = {
        "generated_from": str(metadata_path.relative_to(ROOT)),
        "asset_count": len(assets),
        "assets": assets,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop verified item icons for the local editor"
    )
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--captures", type=Path, default=DEFAULT_CAPTURE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_assets(args.metadata, args.captures, args.output)
    print(f"{args.output}: {manifest['asset_count']} item icons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
